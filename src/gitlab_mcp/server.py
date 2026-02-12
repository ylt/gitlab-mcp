"""FastMCP server for GitLab."""

from fastmcp import FastMCP
from gitlab_mcp.config import get_config

# Create the MCP server
mcp = FastMCP(
    name="gitlab-mcp",
    instructions="""GitLab MCP server providing tools to interact with GitLab repositories,
    merge requests, issues, pipelines, and more. Responses are optimized for AI consumption
    with relevant context and human-readable formatting.""",
)

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
