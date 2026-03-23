"""FastMCP server for GitLab."""

from contextlib import asynccontextmanager

from fastmcp import FastMCP
from gitlab_mcp.config import get_config


@asynccontextmanager
async def lifespan(server):
    """Manage the Action Cable WebSocket connection lifecycle."""
    from gitlab_mcp.realtime import ActionCableManager
    from gitlab_mcp.tools.realtime import set_manager

    config = get_config()
    manager = ActionCableManager(
        gitlab_url=config.gitlab_url,
        token=config.oauth_token or config.token,
    )
    set_manager(manager)

    try:
        yield
    finally:
        await manager.close()
        set_manager(None)


# Create the MCP server
mcp = FastMCP(
    name="gitlab-mcp",
    instructions="""GitLab MCP server providing tools to interact with GitLab repositories,
    merge requests, issues, pipelines, and more. Responses are optimized for AI consumption
    with relevant context and human-readable formatting.""",
    lifespan=lifespan,
)

# Inject Channel capability so Claude Code treats this as a channel-capable server.
# The MCP SDK doesn't have native channel support yet, so we patch get_capabilities
# to merge our experimental capability into the response.
_orig_get_capabilities = mcp._mcp_server.get_capabilities


def _patched_get_capabilities(notification_options, experimental_capabilities=None):
    merged = {**(experimental_capabilities or {}), "claude/channel": {}}
    return _orig_get_capabilities(notification_options, merged)


mcp._mcp_server.get_capabilities = _patched_get_capabilities

# Load configuration for dynamic tool loading
config = get_config()

# Import core tool modules (always loaded)
from gitlab_mcp.tools import merge_requests  # noqa: F401, E402
from gitlab_mcp.tools import issues  # noqa: F401, E402
from gitlab_mcp.tools import repository  # noqa: F401, E402
from gitlab_mcp.tools import discussions  # noqa: F401, E402
from gitlab_mcp.tools import pipelines  # noqa: F401, E402
from gitlab_mcp.tools import projects  # noqa: F401, E402
from gitlab_mcp.tools import labels  # noqa: F401, E402
from gitlab_mcp.tools import namespaces  # noqa: F401, E402
from gitlab_mcp.tools import milestones  # noqa: F401, E402
from gitlab_mcp.tools import users  # noqa: F401, E402
from gitlab_mcp.tools import draft_notes  # noqa: F401, E402
from gitlab_mcp.tools import uploads  # noqa: F401, E402
from gitlab_mcp.tools import iterations  # noqa: F401, E402
from gitlab_mcp.tools import realtime  # noqa: F401, E402

# Conditionally import optional tool modules based on config
if not config.disable_wiki:
    from gitlab_mcp.tools import wiki  # noqa: F401, E402

if not config.disable_releases:
    from gitlab_mcp.tools import releases  # noqa: F401, E402

if not config.disable_graphql:
    from gitlab_mcp.tools import graphql  # noqa: F401, E402


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
