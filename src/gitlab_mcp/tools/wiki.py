"""Wiki tools."""

from typing import Any, cast
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.models import WikiPageSummary, WikiPageDetail, WikiPageDeleteResult, WikiAttachmentResult
from gitlab_mcp.utils.pagination import paginate
import os


@mcp.tool(annotations={"title": "List Wiki Pages", "readOnlyHint": True, "openWorldHint": True})
def list_wiki_pages(
    project_id: str,
    per_page: int = 20,
) -> list[WikiPageSummary]:
    """List all wiki pages in a project.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        per_page: Items per page (max 100)
    """
    project = get_project(project_id)
    pages = paginate(
        project.wikis,
        per_page=per_page,
    )
    return WikiPageSummary.from_gitlab(pages)


@mcp.tool(annotations={"title": "Get Wiki Page", "readOnlyHint": True, "openWorldHint": True})
def get_wiki_page(project_id: str, slug: str) -> WikiPageDetail:
    """Get the content of a wiki page.

    Args:
        project_id: Project ID or path
        slug: Wiki page slug (e.g., "home", "my-page")
    """
    project = get_project(project_id)
    page = project.wikis.get(slug)
    return WikiPageDetail.from_gitlab(page)


@mcp.tool(
    annotations={
        "title": "Create Wiki Page",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_wiki_page(
    project_id: str,
    title: str,
    content: str,
    format: str = "markdown",
) -> WikiPageDetail:
    """Create a new wiki page.

    Args:
        project_id: Project ID or path
        title: Page title
        content: Page content
        format: Page format (markdown, rdoc, asciidoc)

    Returns:
        Created wiki page
    """
    project = get_project(project_id)
    data = {
        "title": title,
        "content": content,
        "format": format,
    }
    page = project.wikis.create(data)
    return WikiPageDetail.from_gitlab(page)


@mcp.tool(
    annotations={
        "title": "Update Wiki Page",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_wiki_page(
    project_id: str,
    slug: str,
    title: str = "",
    content: str = "",
) -> WikiPageDetail:
    """Update an existing wiki page.

    Args:
        project_id: Project ID or path
        slug: Wiki page slug
        title: New page title (leave empty to keep current)
        content: New page content (leave empty to keep current)

    Returns:
        Updated wiki page
    """
    project = get_project(project_id)
    page = project.wikis.get(slug)
    if title:
        page.title = title
    if content:
        page.content = content
    page.save()
    return WikiPageDetail.from_gitlab(page)


@mcp.tool(
    annotations={
        "title": "Delete Wiki Page",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_wiki_page(project_id: str, slug: str) -> WikiPageDeleteResult:
    """Delete a wiki page.

    Note: This action is permanent and cannot be undone.

    Args:
        project_id: Project ID or path
        slug: Wiki page slug

    Returns:
        Confirmation of deletion
    """
    project = get_project(project_id)
    project.wikis.delete(slug)
    return WikiPageDeleteResult.model_validate({"deleted": True, "slug": slug})


@mcp.tool(annotations={"title": "Search Wiki Pages", "readOnlyHint": True, "openWorldHint": True})
def search_wiki_pages(project_id: str, query: str) -> list[WikiPageSummary]:
    """Search wiki pages by title or content.

    Searches across all wiki pages in the project, filtering by query match
    in title or content. Returns matching pages with summaries.

    Args:
        project_id: Project ID or path
        query: Search query string (case-insensitive)

    Returns:
        List of matching wiki pages with summaries
    """
    project = get_project(project_id)
    query_lower = query.lower()
    results: list[WikiPageSummary] = []

    # List all pages and filter by query
    try:
        pages = paginate(project.wikis, per_page=100)
        for page in pages:
            # Check title match
            if query_lower in page.title.lower():
                results.append(WikiPageSummary.from_gitlab(page))
            # Check content match (requires fetching full page)
            else:
                full_page = project.wikis.get(page.slug)
                if query_lower in full_page.content.lower():
                    results.append(WikiPageSummary.from_gitlab(page))
    except Exception:
        # If pagination fails, try direct list
        for page in project.wikis.list(all=True):
            if query_lower in page.title.lower():
                results.append(WikiPageSummary.from_gitlab(page))

    return results


@mcp.tool(
    annotations={
        "title": "Upload Wiki Attachment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def upload_wiki_attachment(
    project_id: str,
    file_path: str,
    file_name: str | None = None,
) -> WikiAttachmentResult:
    """Upload a file as a wiki attachment.

    Uploads a file to the project and returns the markdown link
    formatted for use in wiki pages.

    Args:
        project_id: Project ID or path
        file_path: Local file path to upload
        file_name: Optional custom filename (defaults to basename of file_path)

    Returns:
        Dictionary with markdown link and upload metadata
    """
    project = get_project(project_id)

    # Validate file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get filename
    filename = file_name or os.path.basename(file_path)

    # Read and upload file
    with open(file_path, "rb") as f:
        file_contents = f.read()

    # Use project uploads API
    result: Any = project.uploads.create({"file": (filename, file_contents)})  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]

    return WikiAttachmentResult.model_validate({
        "markdown": cast(str, result.markdown),
        "url": cast(str, result.url),
        "alt": cast(str, result.alt),
        "filename": filename,
        "size_bytes": len(file_contents),
    })


# Note: Wiki page revision history and revert functionality are not supported via
# the GitLab REST API. These operations require either:
# 1. GitLab GraphQL API (for metadata about revisions)
# 2. Direct access to the wiki git repository (for actual history/revert operations)
# Consider implementing these via GraphQL queries in the graphql.py module if needed.
