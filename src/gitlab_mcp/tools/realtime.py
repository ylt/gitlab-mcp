"""Real-time event subscription tools."""

import logging

from fastmcp.server.context import Context
from mcp.types import ClientCapabilities

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.config import get_config
from gitlab_mcp.realtime import ActionCableManager

logger = logging.getLogger(__name__)

# Per-session managers, keyed by session_id
_managers: dict[str, ActionCableManager] = {}


def _get_or_create_manager(ctx: Context) -> tuple[ActionCableManager, str]:
    """Get or create a per-session ActionCableManager.

    Creates a new manager on first call for a session, detecting the client's
    channel capability to set the delivery mode.

    Returns:
        Tuple of (manager, delivery_mode).
    """
    sid = ctx.session_id
    if sid in _managers:
        mgr = _managers[sid]
        return mgr, mgr.delivery_mode

    config = get_config()

    # Detect delivery mode for this client
    supported = ctx.session.check_client_capability(
        ClientCapabilities(experimental={"claude/channel": {}})
    )
    delivery_mode = "push" if supported else "poll"

    mgr = ActionCableManager(
        gitlab_url=config.gitlab_url,
        token=config.oauth_token or config.token,
        delivery_mode=delivery_mode,
    )

    if supported:
        mgr.set_session(ctx.session)

    _managers[sid] = mgr

    # Register cleanup when session ends
    if hasattr(ctx.session, "on_cleanup"):
        ctx.session.on_cleanup(lambda: _cleanup_manager(sid))

    return mgr, delivery_mode


def _get_manager(ctx: Context) -> ActionCableManager | None:
    """Get existing manager for this session, or None."""
    return _managers.get(ctx.session_id)


async def _cleanup_manager(sid: str) -> None:
    """Clean up a session's manager."""
    mgr = _managers.pop(sid, None)
    if mgr:
        logger.info("Cleaning up ActionCableManager for session %s", sid)
        await mgr.close()


async def cleanup_all_managers() -> None:
    """Clean up all remaining managers (called on server shutdown)."""
    for sid in list(_managers.keys()):
        await _cleanup_manager(sid)


@mcp.tool
async def subscribe_mr_notes(
    project_id: str,
    mr_iid: int,
    ctx: Context = None,
) -> dict:
    """Subscribe to real-time note/comment events on a merge request.

    Pushes new comments and discussion updates as they happen.
    In poll mode, call check_updates to retrieve buffered events.

    Args:
        project_id: Project ID or URL-encoded path
        mr_iid: Merge request IID
    """
    manager, delivery_mode = _get_or_create_manager(ctx)
    project = get_project(project_id)
    mr = project.mergerequests.get(mr_iid)

    sub = await manager.subscribe(
        channel="Noteable::NotesChannel",
        params={
            "project_id": project.id,
            "group_id": None,
            "noteable_type": "merge_request",
            "noteable_id": mr.id,
        },
        description=f"MR !{mr_iid} notes in {project.path_with_namespace}",
    )
    result = {
        "subscription_id": sub.id,
        "channel": sub.channel,
        "description": sub.description,
        "status": "subscribed",
        "delivery_mode": delivery_mode,
    }
    if delivery_mode == "poll":
        result["instructions"] = "Call check_updates to retrieve new events. Events are buffered until you poll."
    return result


@mcp.tool
async def subscribe_issue_notes(
    project_id: str,
    issue_iid: int,
    ctx: Context = None,
) -> dict:
    """Subscribe to real-time note/comment events on an issue.

    Pushes new comments as they happen.
    In poll mode, call check_updates to retrieve buffered events.

    Args:
        project_id: Project ID or URL-encoded path
        issue_iid: Issue IID
    """
    manager, delivery_mode = _get_or_create_manager(ctx)
    project = get_project(project_id)
    issue = project.issues.get(issue_iid)

    sub = await manager.subscribe(
        channel="Noteable::NotesChannel",
        params={
            "project_id": project.id,
            "group_id": None,
            "noteable_type": "issue",
            "noteable_id": issue.id,
        },
        description=f"Issue #{issue_iid} notes in {project.path_with_namespace}",
    )
    result = {
        "subscription_id": sub.id,
        "channel": sub.channel,
        "description": sub.description,
        "status": "subscribed",
        "delivery_mode": delivery_mode,
    }
    if delivery_mode == "poll":
        result["instructions"] = "Call check_updates to retrieve new events. Events are buffered until you poll."
    return result


@mcp.tool
async def subscribe_pipeline_status(
    project_id: str,
    pipeline_id: int,
    ctx: Context = None,
) -> dict:
    """Subscribe to real-time pipeline status updates via GraphQL subscription.

    Pushes status changes as the pipeline progresses.
    In poll mode, call check_updates to retrieve buffered events.

    Args:
        project_id: Project ID or URL-encoded path
        pipeline_id: Pipeline ID
    """
    manager, delivery_mode = _get_or_create_manager(ctx)
    project = get_project(project_id)

    # GraphQL subscription for pipeline status
    sub = await manager.subscribe(
        channel="GraphqlChannel",
        description=f"Pipeline #{pipeline_id} status in {project.path_with_namespace}",
    )

    # Send the GraphQL subscription query as an Action Cable message
    import json
    query = """
        subscription($pipelineId: CiPipelineID!) {
            ciPipelineStatusUpdated(pipelineId: $pipelineId) {
                status
                detailedStatus { text label icon }
                stages { nodes { name status detailedStatus { text } } }
            }
        }
    """
    data_msg = json.dumps({
        "command": "message",
        "identifier": sub.identifier,
        "data": json.dumps({
            "query": query,
            "variables": {"pipelineId": f"gid://gitlab/Ci::Pipeline/{pipeline_id}"},
            "action": "execute",
        }),
    })
    await manager._ws.send(data_msg)

    result = {
        "subscription_id": sub.id,
        "channel": sub.channel,
        "description": sub.description,
        "status": "subscribed",
        "delivery_mode": delivery_mode,
    }
    if delivery_mode == "poll":
        result["instructions"] = "Call check_updates to retrieve new events. Events are buffered until you poll."
    return result


@mcp.tool
async def unsubscribe(subscription_id: str, ctx: Context = None) -> dict:
    """Unsubscribe from a real-time event subscription.

    Args:
        subscription_id: The subscription ID returned by a subscribe tool
    """
    manager = _get_manager(ctx)
    if manager is None:
        return {"subscription_id": subscription_id, "status": "not_found"}

    removed = await manager.unsubscribe(subscription_id)
    return {
        "subscription_id": subscription_id,
        "status": "unsubscribed" if removed else "not_found",
    }


@mcp.tool
async def list_subscriptions(ctx: Context = None) -> dict:
    """List all active real-time event subscriptions."""
    manager = _get_manager(ctx)
    if manager is None:
        return {"count": 0, "subscriptions": [], "connected": False}

    subs = manager.list_subscriptions()
    return {
        "count": len(subs),
        "subscriptions": subs,
        "connected": manager._ws is not None,
        "delivery_mode": manager.delivery_mode,
    }


@mcp.tool(
    annotations={
        "title": "Check Updates",
        "readOnlyHint": True,
    }
)
async def check_updates(
    subscription_id: str | None = None,
    ctx: Context = None,
) -> dict:
    """Check for new real-time events from your subscriptions.

    Returns and clears all buffered events. Call this periodically when
    subscriptions are in poll mode (delivery_mode="poll").

    Args:
        subscription_id: Optional. Filter to a specific subscription.
            If omitted, returns events from all subscriptions.
    """
    manager = _get_manager(ctx)
    if manager is None:
        return {
            "events": [],
            "count": 0,
            "note": "No active subscriptions.",
        }

    if manager.delivery_mode == "push":
        return {
            "events": [],
            "count": 0,
            "delivery_mode": "push",
            "note": "Subscriptions are in push mode. Events are delivered automatically via channel notifications.",
        }

    events = manager.drain_events(subscription_id)
    result = {
        "events": events,
        "count": len(events),
        "delivery_mode": "poll",
    }
    if subscription_id and not events and subscription_id not in {s.id for s in manager._subscriptions.values()}:
        result["note"] = "Subscription not found."
    return result
