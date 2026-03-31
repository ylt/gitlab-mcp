"""Action Cable WebSocket manager for GitLab real-time events."""

import asyncio
import datetime
import json
import logging
import urllib.parse
import uuid
from dataclasses import dataclass, field
from typing import ClassVar

import websockets
from websockets import ClientConnection

from mcp.types import JSONRPCNotification, JSONRPCMessage
from mcp.shared.session import SessionMessage

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """An active Action Cable subscription."""

    id: str
    channel: str
    params: dict
    description: str = ""

    @property
    def identifier(self) -> str:
        """Action Cable identifier JSON string."""
        return json.dumps({"channel": self.channel, **self.params})


@dataclass
class ActionCableManager:
    """Manages a single WebSocket connection to GitLab Action Cable.

    Multiplexes subscriptions over one connection and pushes events
    to the MCP client as Channel notifications.
    """

    gitlab_url: str
    token: str
    _ws: ClientConnection | None = field(default=None, repr=False)
    _subscriptions: dict[str, Subscription] = field(default_factory=dict)
    _session: object | None = field(default=None, repr=False)  # ServerSession
    _listener_task: asyncio.Task | None = field(default=None, repr=False)
    _connect_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _reconnect_delay: float = 1.0
    delivery_mode: str = "push"
    _event_buffer: dict[str, list[dict]] = field(default_factory=dict)

    MAX_BUFFER_PER_SUB: ClassVar[int] = 500

    @property
    def cable_url(self) -> str:
        parsed = urllib.parse.urlparse(self.gitlab_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        return f"{ws_scheme}://{parsed.netloc}/-/cable"

    @property
    def origin(self) -> str:
        parsed = urllib.parse.urlparse(self.gitlab_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def set_session(self, session) -> None:
        """Store the MCP ServerSession for pushing channel notifications."""
        self._session = session

    async def connect(self) -> None:
        """Establish WebSocket connection to Action Cable."""
        async with self._connect_lock:
            if self._ws is not None:
                return

            headers = {
                "Origin": self.origin,
                "PRIVATE-TOKEN": self.token,
            }

            self._ws = await websockets.connect(
                self.cable_url,
                additional_headers=headers,
                subprotocols=[websockets.Subprotocol("actioncable-v1-json")],
                open_timeout=10,
            )

            # Wait for welcome
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
            msg = json.loads(raw)
            if msg.get("type") != "welcome":
                await self._ws.close()
                self._ws = None
                raise ConnectionError(f"Expected welcome, got: {msg}")

            logger.info("Action Cable connected to %s", self.cable_url)

            # Start listener
            self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        """Background listener that receives Action Cable messages and pushes channel notifications."""
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                # Skip pings and connection management
                if msg_type in ("ping", "welcome", "disconnect"):
                    if msg_type == "disconnect":
                        logger.warning("Action Cable disconnect: %s", msg.get("reason"))
                    continue

                # Subscription confirmations/rejections
                if msg_type in ("confirm_subscription", "reject_subscription"):
                    identifier = msg.get("identifier", "")
                    status = "confirmed" if msg_type == "confirm_subscription" else "rejected"
                    logger.info("Subscription %s: %s", status, identifier)
                    continue

                # Data message — push to Claude as channel notification
                identifier_str = msg.get("identifier")
                message = msg.get("message")
                if message is not None and identifier_str:
                    await self._push_event(identifier_str, message)

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("Action Cable connection closed: %s", e)
        except Exception as e:
            logger.exception("Action Cable listener error: %s", e)
        finally:
            self._ws = None
            # Attempt reconnect if we still have subscriptions
            if self._subscriptions:
                asyncio.create_task(self._reconnect())

    async def _reconnect(self) -> None:
        """Reconnect and re-subscribe."""
        logger.info("Reconnecting in %.1fs...", self._reconnect_delay)
        await asyncio.sleep(self._reconnect_delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, 30)

        try:
            await self.connect()
            # Re-subscribe all active subscriptions
            for sub in self._subscriptions.values():
                await self._send_subscribe(sub)
            self._reconnect_delay = 1.0
            logger.info("Reconnected and re-subscribed %d subscriptions", len(self._subscriptions))
        except Exception as e:
            logger.error("Reconnect failed: %s", e)
            if self._subscriptions:
                asyncio.create_task(self._reconnect())

    async def _push_event(self, identifier_str: str, message: dict | str) -> None:
        """Push an event to the MCP client or buffer it for polling."""
        # Find which subscription this belongs to
        sub = None
        for s in self._subscriptions.values():
            if s.identifier == identifier_str:
                sub = s
                break

        # Build content
        if isinstance(message, dict):
            content = json.dumps(message, indent=2)
        else:
            content = str(message)

        meta = {"source": "gitlab"}
        if sub:
            meta["subscription_id"] = sub.id
            meta["channel"] = sub.channel
            meta.update({k: str(v) for k, v in sub.params.items() if v is not None})

        # Poll mode: buffer the event
        if self.delivery_mode == "poll":
            event = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "subscription_id": sub.id if sub else "unknown",
                "channel": sub.channel if sub else "unknown",
                "content": content,
                "meta": meta,
            }
            sub_id = sub.id if sub else "unknown"
            buf = self._event_buffer.setdefault(sub_id, [])
            buf.append(event)

            # Enforce cap
            if len(buf) > self.MAX_BUFFER_PER_SUB:
                overflow = len(buf) - self.MAX_BUFFER_PER_SUB
                # Check if first entry is already an overflow marker
                if buf and buf[0].get("type") == "buffer_overflow":
                    buf[0]["dropped"] += overflow
                    del buf[1:1 + overflow]
                else:
                    del buf[:overflow]
                    buf.insert(0, {
                        "type": "buffer_overflow",
                        "dropped": overflow,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    })
            return

        # Push mode: send via session stream
        if self._session is None:
            logger.debug("No session, dropping event: %s", identifier_str)
            return

        notif = JSONRPCNotification(
            jsonrpc="2.0",
            method="notifications/claude/channel",
            params={"content": content, "meta": meta},
        )
        session_msg = SessionMessage(message=JSONRPCMessage(notif))

        try:
            await self._session._write_stream.send(session_msg)
        except Exception as e:
            logger.error("Failed to push channel notification: %s", e)

    async def _send_subscribe(self, sub: Subscription) -> None:
        """Send an Action Cable subscribe command."""
        if self._ws is None:
            raise ConnectionError("Not connected")

        msg = json.dumps({
            "command": "subscribe",
            "identifier": sub.identifier,
        })
        await self._ws.send(msg)

    async def _send_unsubscribe(self, sub: Subscription) -> None:
        """Send an Action Cable unsubscribe command."""
        if self._ws is None:
            return

        msg = json.dumps({
            "command": "unsubscribe",
            "identifier": sub.identifier,
        })
        await self._ws.send(msg)

    async def subscribe(
        self,
        channel: str,
        params: dict | None = None,
        description: str = "",
    ) -> Subscription:
        """Subscribe to an Action Cable channel. Connects if needed."""
        await self.connect()

        sub = Subscription(
            id=uuid.uuid4().hex[:8],
            channel=channel,
            params=params or {},
            description=description,
        )
        self._subscriptions[sub.id] = sub
        await self._send_subscribe(sub)

        logger.info("Subscribed %s to %s (%s)", sub.id, channel, params)
        return sub

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a channel."""
        sub = self._subscriptions.pop(subscription_id, None)
        if sub is None:
            return False

        self._event_buffer.pop(subscription_id, None)

        await self._send_unsubscribe(sub)
        logger.info("Unsubscribed %s from %s", sub.id, sub.channel)

        # Disconnect if no more subscriptions
        if not self._subscriptions:
            await self.close()

        return True

    def list_subscriptions(self) -> list[dict]:
        """List all active subscriptions."""
        return [
            {
                "id": sub.id,
                "channel": sub.channel,
                "params": sub.params,
                "description": sub.description,
            }
            for sub in self._subscriptions.values()
        ]

    def drain_events(self, subscription_id: str | None = None) -> list[dict]:
        """Drain buffered events, returning and clearing them.

        Args:
            subscription_id: If given, drain only that subscription's events.
                If None, drain all events across all subscriptions.

        Returns:
            List of event dicts, sorted by timestamp.
        """
        if subscription_id is not None:
            return self._event_buffer.pop(subscription_id, [])

        # Drain all subscriptions
        all_events = []
        for sid in list(self._event_buffer.keys()):
            all_events.extend(self._event_buffer.pop(sid, []))
        all_events.sort(key=lambda e: e.get("timestamp", ""))
        return all_events

    async def close(self) -> None:
        """Close the WebSocket connection and clean up."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._ws is not None:
            await self._ws.close()
            self._ws = None

        self._event_buffer.clear()
        self._subscriptions.clear()
        logger.info("Action Cable manager closed")
