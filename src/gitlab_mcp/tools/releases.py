"""Release tools."""

import httpx

from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.config import get_config
from gitlab_mcp.models import ReleaseSummary
from gitlab_mcp.models.releases import (
    ReleaseDeleteResult,
    ReleaseEvidence,
    ReleaseAssetDownload,
    ReleaseLink,
    ReleaseLinkDeleteResult,
)
from gitlab_mcp.utils.pagination import paginate
from gitlab_mcp.utils.query import build_sort


@mcp.tool(
    annotations={
        "title": "List Releases",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_releases(
    project_id: str,
    per_page: int = 20,
    order_by: str | None = None,
    sort: str = "desc",
) -> list[ReleaseSummary]:
    """List releases in a project.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        per_page: Items per page (max 100)
        order_by: Sort by field (released_at, created_at)
        sort: Sort direction (asc, desc)
    """
    project = get_project(project_id)
    filters = build_sort(order_by=order_by, sort=sort)
    releases = paginate(
        project.releases,
        per_page=per_page,
        **filters,
    )
    return ReleaseSummary.from_gitlab(releases)


@mcp.tool(
    annotations={
        "title": "Get Release",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def get_release(project_id: str, tag_name: str) -> ReleaseSummary:
    """Get details of a release.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name
    """
    project = get_project(project_id)
    release = project.releases.get(tag_name)
    return ReleaseSummary.from_gitlab(release)


@mcp.tool(
    annotations={
        "title": "Create Release",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_release(
    project_id: str,
    tag_name: str,
    name: str = "",
    description: str = "",
    ref: str = "",
) -> ReleaseSummary:
    """Create a new release.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name (must be unique)
        name: Release name
        description: Release description (markdown supported)
        ref: Commit SHA, another tag, or branch name (defaults to tag_name)
    """
    project = get_project(project_id)
    data = {"tag_name": tag_name}
    if name:
        data["name"] = name
    if description:
        data["description"] = description
    if ref:
        data["ref"] = ref
    release = project.releases.create(data)
    return ReleaseSummary.from_gitlab(release)


@mcp.tool(
    annotations={
        "title": "Update Release",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def update_release(
    project_id: str,
    tag_name: str,
    name: str = "",
    description: str = "",
) -> ReleaseSummary:
    """Update a release.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name
        name: New release name (leave empty to keep current)
        description: New description (leave empty to keep current)
    """
    project = get_project(project_id)
    release = project.releases.get(tag_name)
    if name:
        release.name = name
    if description:
        release.description = description
    release.save()
    return ReleaseSummary.from_gitlab(release)


@mcp.tool(
    annotations={
        "title": "Delete Release",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_release(project_id: str, tag_name: str, keep_tag: bool = False) -> ReleaseDeleteResult:
    """Delete a release.

    Note: By default, this deletes both the release and the git tag.
    Set keep_tag=True to preserve the git tag.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name
        keep_tag: If True, delete release but preserve the git tag (default: False)
    """
    project = get_project(project_id)
    project.releases.delete(tag_name, keep_tag=keep_tag)
    return ReleaseDeleteResult.model_validate({"status": "deleted", "tag_name": tag_name, "keep_tag": keep_tag})


@mcp.tool(
    annotations={
        "title": "Create Release Evidence",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_release_evidence(project_id: str, tag_name: str) -> ReleaseEvidence:
    """Create release evidence for a release.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name

    Returns:
        Evidence metadata
    """
    config = get_config()
    project = get_project(project_id)
    # Verify release exists
    project.releases.get(tag_name)

    # Create evidence via API
    with httpx.Client(headers={"PRIVATE-TOKEN": config.token}) as client:
        url = f"{config.gitlab_url}/api/v4/projects/{project.id}/releases/{tag_name}/evidence"
        response = client.post(url, json={})
        response.raise_for_status()
        data = response.json()

    return ReleaseEvidence.model_validate({
        "id": data.get("id"),
        "tag_name": tag_name,
        "status": "created",
        "evidence_file_path": data.get("evidence_file_path"),
    })


@mcp.tool(
    annotations={
        "title": "Download Release Asset",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def download_release_asset(
    project_id: str, tag_name: str, asset_path: str, output_path: str = ""
) -> ReleaseAssetDownload:
    """Download a release asset.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name
        asset_path: Path or URL of asset to download
        output_path: Path to save file (defaults to current directory + filename)

    Returns:
        Download status and file metadata
    """
    config = get_config()

    # Download using httpx
    with httpx.Client(headers={"PRIVATE-TOKEN": config.token}) as client:
        response = client.get(asset_path)
        response.raise_for_status()

    # Determine filename from asset_path
    filename = asset_path.split("/")[-1]
    save_path = output_path or filename

    # Save file
    with open(save_path, "wb") as f:
        f.write(response.content)

    return ReleaseAssetDownload.model_validate({
        "status": "downloaded",
        "tag_name": tag_name,
        "filename": filename,
        "path": save_path,
        "size_bytes": len(response.content),
    })


@mcp.tool(
    annotations={
        "title": "List Release Links",
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
def list_release_links(project_id: str, tag_name: str) -> list[ReleaseLink]:
    """List all links/assets attached to a release.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name
    """
    project = get_project(project_id)
    release = project.releases.get(tag_name)
    links = release.releaselinks.list(get_all=True)
    return ReleaseLink.from_gitlab(links)


@mcp.tool(
    annotations={
        "title": "Create Release Link",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def create_release_link(
    project_id: str,
    tag_name: str,
    name: str,
    url: str,
    link_type: str = "other",
) -> ReleaseLink:
    """Add a link to a release.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name
        name: Link name/label
        url: URL of the link
        link_type: Type of link (runbook, image, package, other)
    """
    project = get_project(project_id)
    release = project.releases.get(tag_name)
    link = release.releaselinks.create({"name": name, "url": url, "link_type": link_type})
    return ReleaseLink.from_gitlab(link)


@mcp.tool(
    annotations={
        "title": "Delete Release Link",
        "readOnlyHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def delete_release_link(project_id: str, tag_name: str, link_id: int) -> ReleaseLinkDeleteResult:
    """Delete a link from a release.

    Args:
        project_id: Project ID or path
        tag_name: Release tag name
        link_id: Release link ID
    """
    project = get_project(project_id)
    release = project.releases.get(tag_name)
    release.releaselinks.delete(link_id)
    return ReleaseLinkDeleteResult.model_validate({"status": "deleted", "link_id": link_id, "tag_name": tag_name})
