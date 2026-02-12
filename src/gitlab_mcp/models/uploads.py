"""Upload and attachment response models."""

from pydantic import Field, computed_field
from gitlab_mcp.models.base import BaseGitLabModel


class UploadSummary(BaseGitLabModel):
    """AI-optimized upload summary."""

    markdown: str = Field(description="Markdown format for embedding in issues/MRs")
    url: str = Field(description="Direct URL to uploaded file")
    alt: str = Field(description="Alt text for markdown link")

    @computed_field
    @property
    def filename(self) -> str:
        """Extract filename from markdown link."""
        return self.markdown.split("(")[-1].rstrip(")")


class DownloadResult(BaseGitLabModel):
    """Result of downloading an attachment."""

    status: str = Field(description="Download status (e.g., 'downloaded')")
    filename: str = Field(description="Name of downloaded file")
    path: str = Field(description="Local path where file was saved")
    size_bytes: int = Field(description="Size of downloaded file in bytes")
