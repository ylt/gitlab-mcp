"""Merge request models."""

from typing import Annotated, Literal, Optional, Any
from pydantic import Field, field_validator, field_serializer, computed_field, model_validator, BeforeValidator
from gitlab_mcp.models.base import BaseGitLabModel, relative_time, safe_str


def ensure_string(v: str | None) -> str:
    """Convert None to empty string."""
    return "" if v is None else v


class MergeRequestSummary(BaseGitLabModel):
    """merge request summary.

    Slim representation focused on what matters for decision-making.
    """

    iid: int = Field(description="MR number within the project")
    title: str
    description: str = ""
    state: Literal["opened", "closed", "merged", "locked"]
    author: str = Field(description="Username of the author")
    source_branch: str
    target_branch: str
    url: str = Field(alias="web_url", description="Web URL to view the MR")
    created: str = Field(alias="created_at", description="When created (relative)")
    updated: str = Field(alias="updated_at", description="When last updated (relative)")
    reviewers: list[str] = Field(default_factory=list)

    # Fields for computed properties (extracted in model_validator)
    approvals_required: int = 0
    approvals_left: int = 0
    head_pipeline: dict | None = None
    merge_status: str | None = None
    detailed_merge_status: str | None = None

    @field_validator('author', mode='before')
    @classmethod
    def extract_author(cls, v):
        """Extract username from author dict."""
        return v["username"] if isinstance(v, dict) else v

    @field_validator('reviewers', mode='before')
    @classmethod
    def extract_reviewers(cls, v):
        """Extract usernames from reviewers list."""
        if not v:
            return []
        return [r["username"] for r in v] if isinstance(v[0], dict) else v

    @model_validator(mode='before')
    @classmethod
    def extract_approval_data(cls, data: Any) -> Any:
        """Extract approval info from nested approvals object."""
        # Only extract if processing an object (not already a dict with extracted data)
        if not isinstance(data, dict) and hasattr(data, "approvals"):
            try:
                approval_obj = data.approvals.get()
                approvals_required = getattr(approval_obj, "approvals_required", 0)
                approvals_left = getattr(approval_obj, "approvals_left", 0)

                # Set as attributes for from_attributes extraction
                data.approvals_required = approvals_required
                data.approvals_left = approvals_left
            except (TypeError, AttributeError):
                pass
        return data

    @computed_field
    @property
    def blockers(self) -> list[str]:
        """Compute reasons blocking merge from pipeline/merge status."""
        blockers = []

        # Check pipeline status
        if self.head_pipeline:
            pipeline_status = self.head_pipeline.get("status") if isinstance(self.head_pipeline, dict) else None
            if pipeline_status in ("failed", "running", "pending"):
                blockers.append(f"Pipeline {pipeline_status}")

        # Check merge status for conflicts
        if self.merge_status == "cannot_be_merged":
            blockers.append("Has conflicts")

        # Check detailed merge status (GitLab 15.6+)
        if self.detailed_merge_status:
            if self.detailed_merge_status == "draft":
                blockers.append("MR is draft")
            elif self.detailed_merge_status == "discussions_not_resolved":
                blockers.append("Unresolved discussions")
            elif self.detailed_merge_status == "blocked_status":
                blockers.append("Blocked by rule")

        # Check approvals
        if self.approvals_left > 0:
            blockers.append(f"{self.approvals_left} approvals needed")

        return blockers

    @computed_field
    @property
    def ready_to_merge(self) -> bool:
        """Whether MR can be merged now."""
        return self.state == "opened" and len(self.blockers) == 0

    @computed_field
    @property
    def summary(self) -> str:
        """One-line summary: '{state} MR by {author} - {ready_to_merge status} - {pipeline status}'."""
        pipeline_status = "unknown"
        if self.head_pipeline:
            pipeline_status = self.head_pipeline.get("status") if isinstance(self.head_pipeline, dict) else "unknown"

        ready_status = "ready" if self.ready_to_merge else "not ready"
        return f"{self.state} MR by {self.author} - {ready_status} - {pipeline_status}"

    @field_serializer('description')
    def serialize_description(self, v: str) -> str:
        """Clean null descriptions."""
        return safe_str(v)

    @field_serializer('created', 'updated')
    def serialize_datetime(self, v: str) -> str:
        """Format as relative time."""
        return relative_time(v)


class MergeRequestDiff(BaseGitLabModel):
    """Single file change in a merge request."""

    path: str = Field(alias="new_path", description="File path (new path if renamed)")
    old_path: str | None = Field(None, description="Original path if renamed")
    diff: Annotated[str, BeforeValidator(ensure_string)] = Field(default="", description="Unified diff content")

    # File flags (not serialized by default)
    new_file: bool = Field(default=False, exclude=True)
    deleted_file: bool = Field(default=False, exclude=True)
    renamed_file: bool = Field(default=False, exclude=True)

    @computed_field
    @property
    def status(self) -> Literal["added", "deleted", "modified", "renamed"]:
        """Compute status from file flags."""
        if self.new_file:
            return "added"
        elif self.deleted_file:
            return "deleted"
        elif self.renamed_file:
            return "renamed"
        return "modified"


class MergeRequestApproval(BaseGitLabModel):
    """Approval status for a merge request."""

    approvals_required: int = Field(description="Total approvals required")
    approvals_left: int = Field(description="Remaining approvals needed")
    approved_by: list[str] = Field(default_factory=list, description="Usernames who approved")

    @field_validator('approved_by', mode='before')
    @classmethod
    def extract_approved_by(cls, v):
        """Extract usernames from approved_by list."""
        if not v:
            return []
        return [u.get("user", {}).get("username", "unknown") for u in v]

    @computed_field
    @property
    def approved(self) -> bool:
        """Whether MR has sufficient approvals (computed from approvals_left)."""
        return self.approvals_left == 0


class MergeRequestPipeline(BaseGitLabModel):
    """Pipeline status for a merge request.

    Includes pipeline metadata, stages, and failed job details.
    """

    id: int = Field(description="Pipeline ID")
    status: str = Field(description="Pipeline status: success, failed, running, pending, etc.")
    url: str = Field(alias="web_url", description="Web URL to view the pipeline")
    ref: str = Field(description="Git ref (branch or tag)")
    sha: str = Field(description="Commit SHA")
    created: str = Field(alias="created_at", description="When created (relative)")
    stages: list[str] = Field(default_factory=list, description="Pipeline stages")
    failed_jobs: list[str] = Field(default_factory=list, description="Names of failed jobs")

    @field_validator('failed_jobs', mode='before')
    @classmethod
    def extract_failed_jobs(cls, v):
        """Extract job names from failed_jobs list."""
        if not v or not isinstance(v, list):
            return []
        return [j.get("name", "unknown") if isinstance(j, dict) else str(j) for j in v]

    @field_serializer('created')
    def serialize_created(self, v: str) -> str:
        """Format as relative time."""
        return relative_time(v)


class ApprovalResult(BaseGitLabModel):
    """Result of approving or unapproving a merge request."""

    approved: bool = Field(description="Whether MR is now approved")
    merge_request_iid: int = Field(description="MR number")


class ApprovalRule(BaseGitLabModel):
    """Single approval rule."""

    rule_type: str | None = Field(None, description="Type of approval rule")
    eligible_approvers: list[dict] = Field(default_factory=list, description="List of eligible approvers")
    approvals_required: int | None = Field(None, description="Approvals required for this rule")
    contains_hidden_groups: bool | None = Field(None, description="Whether rule contains hidden groups")


class ApprovalUser(BaseGitLabModel):
    """User who approved a merge request."""

    id: int = Field(description="User ID")
    username: str = Field(description="Username")

    @model_validator(mode='before')
    @classmethod
    def extract_from_user_dict(cls, data):
        """Extract id and username from nested user dict."""
        if isinstance(data, dict) and "user" in data:
            user = data["user"]
            return {
                "id": user["id"],
                "username": user["username"]
            }
        return data


class ApprovalStateDetailed(BaseGitLabModel):
    """Detailed approval state for a merge request."""

    approved: bool = Field(description="Whether MR is approved")
    approved_by: list[ApprovalUser] = Field(default_factory=list, description="Users who approved")
    approvals_left: int = Field(description="Remaining approvals needed")
    approval_rules_left: list[ApprovalRule] = Field(default_factory=list, description="Approval rules still needed", alias="rules")

    @field_validator('approved_by', mode='before')
    @classmethod
    def extract_approved_by(cls, v):
        """Build ApprovalUser list from approved_by."""
        if not v:
            return []
        return [ApprovalUser.model_validate(user, from_attributes=True) for user in v]

    @field_validator('approval_rules_left', mode='before')
    @classmethod
    def extract_approval_rules(cls, v):
        """Build ApprovalRule list from rules."""
        if not v:
            return []
        return [ApprovalRule.model_validate(rule, from_attributes=True) for rule in v]


class MergeRequestNote(BaseGitLabModel):
    """Comment (note) on a merge request."""

    id: int = Field(description="Note ID")
    author_id: int = Field(description="Author user ID")
    author: str = Field(description="Author username")
    created_at: str = Field(description="When created")
    updated_at: str = Field(description="When last updated")
    body: str = Field(description="Note content")
    system: bool = Field(description="Whether this is a system note")

    @field_validator('author_id', mode='before')
    @classmethod
    def extract_author_id(cls, v, info):
        """Extract author ID from nested author dict."""
        if isinstance(v, int):
            return v
        data = info.data
        if isinstance(data, dict):
            author = data.get("author")
            if author and isinstance(author, dict):
                return author.get("id", 0)
        elif hasattr(data, "author"):
            author = data.author
            if isinstance(author, dict):
                return author.get("id", 0)
        return 0

    @field_validator('author', mode='before')
    @classmethod
    def extract_author_username(cls, v, info):
        """Extract author username from nested author dict."""
        if isinstance(v, str):
            return v
        data = info.data
        if isinstance(data, dict):
            author = data.get("author")
            if author and isinstance(author, dict):
                return author.get("username", "unknown")
        elif hasattr(data, "author"):
            author = data.author
            if isinstance(author, dict):
                return author.get("username", "unknown")
        return "unknown"


class MergeRequestVersion(BaseGitLabModel):
    """Version (iteration) of a merge request."""

    id: int = Field(description="Version ID")
    created_at: str = Field(description="When created")
    updated_at: str = Field(description="When updated")
    head_commit_sha: str = Field(description="HEAD commit SHA")
    base_commit_sha: str = Field(description="Base commit SHA")
    start_commit_sha: str = Field(description="Start commit SHA")


class FileChange(BaseGitLabModel):
    """Single file change with diff stats."""

    path: str = Field(alias="new_path", description="File path")
    old_path: str | None = Field(None, description="Original path if renamed")
    status: str = Field(description="Change status: added, modified, deleted, renamed")
    additions: int = Field(description="Lines added")
    deletions: int = Field(description="Lines deleted")


class ChangesSummary(BaseGitLabModel):
    """Summary of all changes in a merge request."""

    files_changed: int = Field(description="Total files changed")
    additions: int = Field(description="Total lines added")
    deletions: int = Field(description="Total lines deleted")
    files: list[FileChange] = Field(default_factory=list, description="Per-file change details")
