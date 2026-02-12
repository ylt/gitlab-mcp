"""Pipeline and job models."""

from typing import Literal
from pydantic import Field, field_validator, field_serializer, computed_field
from gitlab_mcp.models.base import BaseGitLabModel, relative_time


class PipelineSummary(BaseGitLabModel):
    """pipeline summary."""

    id: int
    status: Literal[
        "created",
        "waiting_for_resource",
        "preparing",
        "pending",
        "running",
        "success",
        "failed",
        "canceled",
        "skipped",
        "manual",
        "scheduled",
    ]
    ref: str = Field(description="Branch or tag name")
    sha: str = Field(description="Commit SHA")
    web_url: str = Field(exclude=True)  # Helper field for auto-extraction
    created_at: str = Field(exclude=True)  # Helper field for auto-extraction
    updated_at: str = Field(exclude=True)  # Helper field for auto-extraction
    duration: int | None = Field(None, description="Pipeline duration in seconds")
    stages: list[str] | list[dict] | None = Field(
        None, description="Stage names or stages breakdown with status and job count"
    )
    failure_reason: str | None = Field(None, description="Reason if pipeline failed")

    @computed_field
    @property
    def url(self) -> str:
        """Web URL to view pipeline."""
        return self.web_url

    @computed_field
    @property
    def created(self) -> str:
        """When created (relative)."""
        return relative_time(self.created_at)

    @computed_field
    @property
    def updated(self) -> str:
        """When last updated (relative)."""
        return relative_time(self.updated_at)

    @field_validator('sha', mode='before')
    @classmethod
    def truncate_sha(cls, v):
        """Shorten commit SHA to 8 characters for readability."""
        if isinstance(v, str) and len(v) > 8:
            return v[:8]
        return v


class JobSummary(BaseGitLabModel):
    """job summary."""

    id: int
    name: str
    stage: str
    status: str
    web_url: str = Field(exclude=True)  # Helper field for auto-extraction
    duration: float | None = Field(None, description="Job duration in seconds")
    created_at: str = Field(exclude=True)  # Helper field for auto-extraction
    failure_reason: str | None = Field(None, description="Reason if job failed")
    retry_count: int = Field(0, description="Number of retries")
    artifacts: list[str] | None = Field(None, description="List of artifact filenames")

    @computed_field
    @property
    def url(self) -> str:
        """Web URL to view job."""
        return self.web_url

    @computed_field
    @property
    def created(self) -> str:
        """When created (relative)."""
        return relative_time(self.created_at)

    @field_validator('artifacts', mode='before')
    @classmethod
    def extract_artifacts(cls, v):
        """Extract artifact filenames from artifact objects."""
        if not v:
            return None
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            return [
                artifact.get("file_format", artifact.get("filename", ""))
                for artifact in v
            ]
        return v

    @field_serializer('artifacts')
    def serialize_artifacts(self, v: list[str] | None) -> list[str] | None:
        """Remove empty artifact names."""
        if not v:
            return None
        filtered = [a for a in v if a]
        return filtered if filtered else None
