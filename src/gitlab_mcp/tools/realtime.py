"""Real-time event subscription tools."""

from fastmcp.server.context import Context

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.realtime import ActionCableManager

# Module-level manager reference, set during server lifespan
_manager: ActionCableManager | None = None


def set_manager(manager: ActionCableManager) -> None:
    global _manager
    _manager = manager


def _get_manager(ctx: Context) -> ActionCableManager:
    if _manager is None:
        raise RuntimeError("Real-time manager not initialized")
    # Ensure the manager has the session for pushing notifications
    if _manager._session is None:
        _manager.set_session(ctx.session)
    return _manager


@mcp.tool
async def subscribe_mr_notes(
    project_id: str,
    mr_iid: int,
    ctx: Context = None,
) -> dict:
    """Subscribe to real-time note/comment events on a merge request.

    Pushes new comments and discussion updates as they happen.

    Args:
        project_id: Project ID or URL-encoded path
        mr_iid: Merge request IID
    """
    manager = _get_manager(ctx)
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
    return {
        "subscription_id": sub.id,
        "channel": sub.channel,
        "description": sub.description,
        "status": "subscribed",
    }


@mcp.tool
async def subscribe_issue_notes(
    project_id: str,
    issue_iid: int,
    ctx: Context = None,
) -> dict:
    """Subscribe to real-time note/comment events on an issue.

    Pushes new comments as they happen.

    Args:
        project_id: Project ID or URL-encoded path
        issue_iid: Issue IID
    """
    manager = _get_manager(ctx)
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
    return {
        "subscription_id": sub.id,
        "channel": sub.channel,
        "description": sub.description,
        "status": "subscribed",
    }


@mcp.tool
async def subscribe_pipeline_status(
    project_id: str,
    pipeline_id: int,
    ctx: Context = None,
) -> dict:
    """Subscribe to real-time pipeline status updates via GraphQL subscription.

    Pushes status changes as the pipeline progresses.

    Args:
        project_id: Project ID or URL-encoded path
        pipeline_id: Pipeline ID
    """
    manager = _get_manager(ctx)
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

    return {
        "subscription_id": sub.id,
        "channel": sub.channel,
        "description": sub.description,
        "status": "subscribed",
    }


@mcp.tool
async def unsubscribe(subscription_id: str, ctx: Context = None) -> dict:
    """Unsubscribe from a real-time event subscription.

    Args:
        subscription_id: The subscription ID returned by a subscribe tool
    """
    manager = _get_manager(ctx)
    removed = await manager.unsubscribe(subscription_id)
    return {
        "subscription_id": subscription_id,
        "status": "unsubscribed" if removed else "not_found",
    }


@mcp.tool
async def list_subscriptions(ctx: Context = None) -> dict:
    """List all active real-time event subscriptions."""
    manager = _get_manager(ctx)
    subs = manager.list_subscriptions()
    return {
        "count": len(subs),
        "subscriptions": subs,
        "connected": manager._ws is not None,
    }
