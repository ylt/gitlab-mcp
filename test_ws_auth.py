"""Test whether GitLab Action Cable WebSocket accepts PAT auth.

Tries multiple auth strategies for the Action Cable handshake:
1. Authorization: Bearer header
2. PRIVATE-TOKEN header
3. private_token query param
4. _gitlab_session cookie (if GITLAB_SESSION_COOKIE is set)

For each working strategy, tests both:
- GraphqlChannel (for GraphQL subscriptions like pipeline status)
- Noteable::NotesChannel (native Action Cable channel for MR/issue notes)

Usage:
    # Uses env vars from your existing config
    uv run python test_ws_auth.py

    # With a specific MR to subscribe to notes on:
    GITLAB_PROJECT_ID=77932505 GITLAB_MR_IID=123 uv run python test_ws_auth.py
"""

import asyncio
import json
import os
import sys
import urllib.parse

import websockets


def get_config():
    url = os.environ.get("GITLAB_API_URL", "https://gitlab.com").removesuffix("/api/v4")
    token = (
        os.environ.get("GITLAB_OAUTH_TOKEN")
        or os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN")
        or os.environ.get("GITLAB_TOKEN")
        or ""
    )
    session_cookie = os.environ.get("GITLAB_SESSION_COOKIE")
    project_id = os.environ.get("GITLAB_PROJECT_ID")
    mr_iid = os.environ.get("GITLAB_MR_IID")
    return url, token, session_cookie, project_id, mr_iid


def cable_url(base_url: str) -> str:
    """Convert HTTP(S) URL to Action Cable WebSocket URL."""
    parsed = urllib.parse.urlparse(base_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{ws_scheme}://{parsed.netloc}/-/cable"


def origin_url(base_url: str) -> str:
    """Extract origin (scheme + host) for the Origin header."""
    parsed = urllib.parse.urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def subscribe_msg(channel: str, params: dict | None = None) -> str:
    """Build an Action Cable subscribe command."""
    identifier = {"channel": channel, **(params or {})}
    return json.dumps({"command": "subscribe", "identifier": json.dumps(identifier)})


async def recv_until(ws, type_names: str | list[str], timeout: float = 10) -> dict | None:
    """Receive messages until we get one with a matching type, or timeout.

    Skips pings and messages without a type field (e.g. data messages).
    """
    if isinstance(type_names, str):
        type_names = [type_names]
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return None
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            data = json.loads(raw)
            msg_type = data.get("type")
            # Skip pings
            if msg_type == "ping":
                continue
            # Skip messages without a type (data messages, errors before confirm)
            if msg_type is None:
                print(f"     (skipping data message: {json.dumps(data)[:120]})")
                continue
            if msg_type in type_names:
                return data
            # Got a typed message but not one we're looking for — return it anyway
            return data
        except asyncio.TimeoutError:
            return None


async def test_channel_subscription(ws, channel: str, params: dict | None, label: str) -> bool:
    """Subscribe to a channel and check for confirm/reject."""
    msg = subscribe_msg(channel, params)
    print(f"  -> subscribe to {label}")
    await ws.send(msg)

    response = await recv_until(ws, ["confirm_subscription", "reject_subscription"], timeout=10)
    if response is None:
        print(f"     TIMEOUT: no response for {label}")
        return False

    print(f"  <- {response}")

    if response.get("type") == "confirm_subscription":
        print(f"     OK: {label} confirmed!")
        return True
    elif response.get("type") == "reject_subscription":
        print(f"     REJECTED: {label}")
        return False
    else:
        print(f"     UNEXPECTED: {response.get('type')}")
        return False


async def test_strategy(
    name: str,
    ws_url: str,
    headers: dict,
    origin: str,
    project_id: str | None,
    mr_iid: str | None,
    noteable_id: str | None,
) -> dict:
    """Test a single auth strategy. Returns dict of channel -> bool."""
    print(f"\n{'='*60}")
    print(f"Strategy: {name}")
    print(f"URL: {ws_url}")
    print(f"Headers: { {k: v[:12] + '...' for k, v in headers.items()} if headers else '(none)' }")
    print(f"{'='*60}")

    # Action Cable requires Origin header and the actioncable subprotocol
    connect_headers = {"Origin": origin, **headers}

    results = {}

    try:
        async with websockets.connect(
            ws_url,
            additional_headers=connect_headers,
            subprotocols=[websockets.Subprotocol("actioncable-v1-json")],
            open_timeout=10,
            close_timeout=5,
        ) as ws:
            # Action Cable sends a "welcome" message on successful connection
            welcome = await recv_until(ws, "welcome", timeout=10)
            if welcome is None or welcome.get("type") != "welcome":
                print(f"  FAILED: no welcome (got {welcome})")
                return {"connect": False}

            print(f"  <- {welcome}")
            print(f"  OK: WebSocket connected")
            results["connect"] = True

            # Test 1: GraphqlChannel
            results["GraphqlChannel"] = await test_channel_subscription(
                ws, "GraphqlChannel", None, "GraphqlChannel"
            )

            # Test 2: Noteable::NotesChannel (needs project_id + noteable info)
            if project_id and noteable_id:
                results["NotesChannel"] = await test_channel_subscription(
                    ws,
                    "Noteable::NotesChannel",
                    {
                        "project_id": int(project_id),
                        "group_id": None,
                        "noteable_type": "merge_request",
                        "noteable_id": int(noteable_id),
                    },
                    f"Noteable::NotesChannel (MR noteable_id={noteable_id})",
                )
            elif project_id:
                print(f"\n  Skipping NotesChannel: need noteable_id (set GITLAB_MR_IID to look it up)")
            else:
                print(f"\n  Skipping NotesChannel: need GITLAB_PROJECT_ID")

            # Listen briefly for any messages (notes, pings, etc.)
            print(f"\n  Listening for 5s...")
            deadline = asyncio.get_event_loop().time() + 5
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    data = json.loads(raw)
                    if data.get("type") != "ping":
                        print(f"  <- {json.dumps(data, indent=2)[:300]}")
                except asyncio.TimeoutError:
                    break

            print(f"  Done listening.")

    except (websockets.exceptions.InvalidStatusCode, websockets.exceptions.InvalidStatus) as e:
        code = getattr(e, "status_code", None) or getattr(e, "response", None)
        print(f"  FAILED: HTTP {code}")
        return {"connect": False}
    except ConnectionRefusedError:
        print(f"  FAILED: Connection refused")
        return {"connect": False}
    except asyncio.TimeoutError:
        print(f"  FAILED: Timeout")
        return {"connect": False}
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        return {"connect": False}

    return results


def resolve_noteable_id(base_url: str, token: str, project_id: str, mr_iid: str) -> str | None:
    """Resolve MR IID to its internal noteable_id via REST API."""
    import urllib.request

    api_url = f"{base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
    req = urllib.request.Request(api_url, headers={"PRIVATE-TOKEN": token})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            noteable_id = data.get("id")
            print(f"Resolved MR !{mr_iid} -> noteable_id={noteable_id}")
            return str(noteable_id)
    except Exception as e:
        print(f"Failed to resolve MR !{mr_iid}: {e}")
        return None


AUTH_STRATEGIES = {
    "bearer_header": lambda token, url: (
        url,
        {"Authorization": f"Bearer {token}"},
    ),
    "private_token_header": lambda token, url: (
        url,
        {"PRIVATE-TOKEN": token},
    ),
    "query_param": lambda token, url: (
        f"{url}?private_token={token}",
        {},
    ),
}


async def main():
    base_url, token, session_cookie, project_id, mr_iid = get_config()
    ws_base = cable_url(base_url)

    print(f"GitLab instance: {base_url}")
    print(f"Cable URL:       {ws_base}")
    print(f"Token:           {'set (' + token[:8] + '...)' if token else 'NOT SET'}")
    print(f"Session cookie:  {'set' if session_cookie else 'NOT SET'}")
    print(f"Project ID:      {project_id or '(not set)'}")
    print(f"MR IID:          {mr_iid or '(not set)'}")

    if not token and not session_cookie:
        print("\nERROR: No auth configured. Set GITLAB_PERSONAL_ACCESS_TOKEN or similar.")
        sys.exit(1)

    # Resolve MR IID -> noteable_id if both are provided
    noteable_id = None
    if project_id and mr_iid and token:
        noteable_id = resolve_noteable_id(base_url, token, project_id, mr_iid)

    all_results = {}

    origin = origin_url(base_url)

    # Test token-based strategies
    if token:
        for name, make_args in AUTH_STRATEGIES.items():
            url, headers = make_args(token, ws_base)
            all_results[name] = await test_strategy(name, url, headers, origin, project_id, mr_iid, noteable_id)

    # Test session cookie
    if session_cookie:
        headers = {"Cookie": f"_gitlab_session={session_cookie}"}
        all_results["session_cookie"] = await test_strategy(
            "session_cookie", ws_base, headers, origin, project_id, mr_iid, noteable_id
        )

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for strategy, channels in all_results.items():
        print(f"\n  {strategy}:")
        for channel, ok in channels.items():
            print(f"    {'PASS' if ok else 'FAIL'}: {channel}")

    # Overall verdict
    any_notes = any(r.get("NotesChannel") for r in all_results.values())
    any_graphql = any(r.get("GraphqlChannel") for r in all_results.values())
    any_connect = any(r.get("connect") for r in all_results.values())

    print(f"\n{'='*60}")
    if any_notes:
        strategies = [s for s, r in all_results.items() if r.get("NotesChannel")]
        print(f"NotesChannel works with: {', '.join(strategies)}")
    if any_graphql:
        strategies = [s for s, r in all_results.items() if r.get("GraphqlChannel")]
        print(f"GraphqlChannel works with: {', '.join(strategies)}")
    if not any_connect:
        print("No auth strategy could connect to Action Cable.")
    elif not any_notes and not any_graphql:
        print("Connected but no channel subscriptions were accepted.")

    return any_connect


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
