"""Release models."""

from pydantic import Field, field_validator
from gitlab_mcp.models.base import BaseGitLabModel, RelativeTime


class ReleaseSummary(BaseGitLabModel):
    """AI-optimized release summary."""

    tag_name: str = Field(description="Release tag (e.g., v1.0.0)")
    name: str | None = None
    description: str | None = None
    author: str | None = None
    created_at: RelativeTime = Field(description="When created")
    released_at: RelativeTime | None = Field(None, description="When released")

    @field_validator("author", mode="before")
    @classmethod
    def extract_author(cls, v):
        """Extract username from author dict."""
        if isinstance(v, dict):
            return v.get("username")
        return v


class ReleaseDeleteResult(BaseGitLabModel):
    """Result of deleting a release."""

    status: str = Field(description="Operation status (e.g., 'deleted')")
    tag_name: str = Field(description="Release tag name")
    keep_tag: bool = Field(description="Whether git tag was preserved")


class ReleaseEvidence(BaseGitLabModel):
    """Evidence metadata for a release."""

    id: int | None = Field(None, description="Evidence ID")
    tag_name: str = Field(description="Release tag name")
    status: str = Field(description="Operation status (e.g., 'created')")
    evidence_url: str | None = Field(None, description="URL to evidence file")


class ReleaseAssetDownload(BaseGitLabModel):
    """Result of downloading a release asset."""

    status: str = Field(description="Download status (e.g., 'downloaded')")
    tag_name: str = Field(description="Release tag name")
    filename: str = Field(description="Downloaded filename")
    path: str = Field(description="Local file path")
    size_bytes: int = Field(description="File size in bytes")


class ReleaseLink(BaseGitLabModel):
    """Release link/asset information."""

    id: int = Field(description="Link ID")
    name: str = Field(description="Link name/label")
    url: str = Field(description="Link URL")
    link_type: str = Field(description="Link type (runbook, image, package, other)")
    created_at: str = Field(description="When created")


class ReleaseLinkDeleteResult(BaseGitLabModel):
    """Result of deleting a release link."""

    status: str = Field(description="Operation status (e.g., 'deleted')")
    link_id: int = Field(description="Deleted link ID")
    tag_name: str = Field(description="Release tag name")
