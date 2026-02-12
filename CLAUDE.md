# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                    # Install dependencies
uv run gitlab-mcp          # Run server
ruff check src/            # Lint code
ruff format src/           # Format code
uv run python -c "from gitlab_mcp.server import mcp; print(len(mcp._tool_manager._tools))"  # Count tools
```

## Environment Variables

### Authentication (pick one)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITLAB_OAUTH_TOKEN` | Yes* | - | OAuth token (highest priority) |
| `GITLAB_PERSONAL_ACCESS_TOKEN` | Yes* | - | Personal access token |
| `GITLAB_TOKEN` | Yes* | - | Generic token (fallback) |
| `GITLAB_SESSION_COOKIE` | Yes* | - | Session cookie for self-hosted |

### Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITLAB_API_URL` | No | `https://gitlab.com` | GitLab instance URL |
| `GITLAB_PROJECT_ID` | No | - | Default project for tools |
| `GITLAB_READ_ONLY_MODE` | No | `false` | Set `true` for read-only |
| `GITLAB_RETRY_COUNT` | No | `3` | Number of retry attempts |
| `GITLAB_RETRY_BACKOFF` | No | `0.5` | Retry backoff factor |
| `GITLAB_TIMEOUT` | No | `30` | Request timeout in seconds |

## Architecture

**Core pattern**: `server.py` creates a FastMCP instance. Tool modules use `@mcp.tool` decorator and auto-register via import.

```
src/gitlab_mcp/
├── server.py       # FastMCP server, imports all tool modules
├── config.py       # get_config() - singleton from env vars
├── client.py       # get_client(), get_project() - singleton GitLab client
├── models/         # Pydantic models with from_gitlab() transformers
└── tools/          # 112 MCP tools across 16 domain files
```

## Adding New Tools

1. Find the appropriate domain file in `tools/`
2. Add function with `@mcp.tool` decorator:

```python
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project

@mcp.tool
def my_new_tool(project_id: str, param: str) -> dict:
    """Tool description for AI.

    Args:
        project_id: Project ID or path
        param: What this param does
    """
    project = get_project(project_id)
    # ... implementation
    return {"result": "value"}
```

3. For new domains, create file and import in `server.py`

## Response Philosophy

Responses are **AI-optimized**, not raw API passthrough:

- **Slim**: Drop internal IDs, nulls, deprecated fields
- **Enhance**: Add computed fields (ready_to_merge, blockers)
- **Humanize**: "2 days ago" not ISO timestamps
- **Flatten**: `author: "jane"` not nested objects

Use Pydantic models in `models/` for consistent transformation.

## Key Helpers

- `get_project(project_id)` - Get project, handles default from config
- `get_client()` - Get GitLab API client
- `get_config()` - Get environment configuration
- `relative_time(dt)` - Format datetime as "2 days ago"
- Models have `from_gitlab(obj)` classmethod for transformation
