"""Pipeline and job models."""

from typing import Literal
from pydantic import Field, field_validator, field_serializer
from gitlab_mcp.models.base import BaseGitLabModel, RelativeTime


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
    url: str = Field(alias="web_url", description="Web URL to view pipeline")
    created: RelativeTime = Field(alias="created_at", description="When created (relative)")
    updated: RelativeTime = Field(alias="updated_at", description="When last updated (relative)")
    duration: int | None = Field(None, description="Pipeline duration in seconds")
    stages: list[str] | list[dict] | None = Field(
        None, description="Stage names or stages breakdown with status and job count"
    )
    failure_reason: str | None = Field(None, description="Reason if pipeline failed")

    @field_validator("sha", mode="before")
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
    url: str = Field(alias="web_url", description="Web URL to view job")
    duration: float | None = Field(None, description="Job duration in seconds")
    created: RelativeTime = Field(alias="created_at", description="When created (relative)")
    failure_reason: str | None = Field(None, description="Reason if job failed")
    retry_count: int = Field(0, description="Number of retries")
    artifacts: list[str] | None = Field(None, description="List of artifact filenames")

    @field_validator("artifacts", mode="before")
    @classmethod
    def extract_artifacts(cls, v):
        """Extract artifact filenames from artifact objects."""
        if callable(v):
            # from_attributes=True reads the .artifacts manager method, not a list
            return None
        if not v:
            return None
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            return [artifact.get("file_format", artifact.get("filename", "")) for artifact in v]
        if isinstance(v, list):
            return [a for a in v if a is not None]
        return v

    @field_serializer("artifacts")
    def serialize_artifacts(self, v: list[str] | None) -> list[str] | None:
        """Remove empty artifact names."""
        if not v:
            return None
        filtered = [a for a in v if a]
        return filtered if filtered else None


class JobLogResult(BaseGitLabModel):
    """Result of retrieving job logs."""

    job_id: int = Field(description="ID of the job")
    log: str = Field(description="Job log output")
    truncated: bool = Field(description="Whether the log was truncated")
    total_lines: int = Field(description="Total number of lines in the log")
    shown_lines: int = Field(description="Number of lines shown")
