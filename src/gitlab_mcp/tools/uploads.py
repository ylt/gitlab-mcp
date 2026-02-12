"""Upload and attachment tools."""

import httpx
from typing import Any
from gitlab_mcp.server import mcp
from gitlab_mcp.client import get_project
from gitlab_mcp.config import get_config
from gitlab_mcp.models.uploads import UploadSummary, DownloadResult


@mcp.tool(
    annotations={
        "title": "Upload Markdown",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
def upload_markdown(project_id: str, file_path: str) -> UploadSummary:
    """Upload a file to a project and get markdown link.

    Args:
        project_id: Project ID or path (e.g., "mygroup/myproject")
        file_path: Path to file to upload

    Returns:
        UploadSummary with markdown link and upload metadata
    """
    project = get_project(project_id)

    with open(file_path, "rb") as f:
        file_contents = f.read()

    # Use project uploads API
    result: Any = project.uploads.create({"file": (file_path.split("/")[-1], file_contents)})  # type: ignore[union-attr]

    return UploadSummary.from_gitlab(result)  # type: ignore[arg-type]


@mcp.tool(annotations={"title": "Download Attachment", "readOnlyHint": True, "openWorldHint": True})
def download_attachment(
    project_id: str, secret: str, filename: str, output_path: str = ""
) -> DownloadResult:
    """Download an uploaded attachment from a project.

    Args:
        project_id: Project ID or path
        secret: Secret token from upload
        filename: Filename to download
        output_path: Path to save file (defaults to current directory + filename)

    Returns:
        DownloadResult with download status and file path
    """
    config = get_config()

    # Construct download URL
    url = f"{config.gitlab_url}/api/v4/projects/{project_id}/uploads/{secret}/{filename}"

    # Download using httpx
    with httpx.Client(headers={"PRIVATE-TOKEN": config.token}) as http_client:
        response = http_client.get(url)
        response.raise_for_status()

    # Save file
    save_path = output_path or filename
    with open(save_path, "wb") as f:
        f.write(response.content)

    return DownloadResult.model_validate({
        "status": "downloaded",
        "filename": filename,
        "path": save_path,
        "size_bytes": len(response.content),
    })
