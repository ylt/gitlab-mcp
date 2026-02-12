# GitLab MCP Server

AI-optimized MCP server for GitLab. Built with FastMCP.

## Installation

```bash
pip install gitlab-mcp
```

## Usage

```bash
export GITLAB_API_URL=https://gitlab.com
export GITLAB_PERSONAL_ACCESS_TOKEN=your-token
gitlab-mcp
```

## Features

- Merge requests, issues, repository operations
- AI-optimized responses (concise, context-rich)
- Full GitLab API coverage

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```
