"""Merge request models."""

from typing import Annotated, Literal, Any
from pydantic import (
    Field,
    field_validator,
    computed_field,
    model_validator,
    BeforeValidator,
)
from gitlab_mcp.models.base import (
    BaseGitLabModel,
    HtmlCommentFree,
    RelativeTime,
    SafeString,
)
from gitlab_mcp.models.misc import UserRef


def ensure_string(v: str | None) -> str:
    """Convert None to empty string."""
    return "" if v is None else v


class MergeRequestSummary(BaseGitLabModel):
    """merge request summary.

    Slim representation focused on what matters for decision-making.
    """

    iid: int = Field(description="MR number within the project")
    title: str
    description: SafeString = ""
    state: Literal["opened", "closed", "merged", "locked"]
    author: UserRef = Field(description="Author of the merge request")
    source_branch: str
    target_branch: str
    created: RelativeTime = Field(alias="created_at", description="When created (relative)")
    updated: RelativeTime = Field(alias="updated_at", description="When last updated (relative)")
    reviewers: list[UserRef] = Field(default_factory=list)

    # Fields for computed properties (extracted in model_validator)
    _approvals_required: int = 0
    _approvals_left: int = 0
    head_pipeline: dict | None = None
    _merge_status: str | None = None
    _detailed_merge_status: str | None = None

    @model_validator(mode="before")
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
                data._approvals_required = approvals_required
                data._approvals_left = approvals_left
            except (TypeError, AttributeError):
                pass
        return data

    @computed_field
    @property
    def approvals(self) -> str:
        """Approval status as 'approved/required'."""
        approved = self._approvals_required - self._approvals_left
        return f"{approved}/{self._approvals_required}"

    @computed_field
    @property
    def blockers(self) -> list[str]:
        """Compute reasons blocking merge from pipeline/merge status."""
        blockers = []

        # Check pipeline status
        if self.head_pipeline:
            pipeline_status = (
                self.head_pipeline.get("status") if isinstance(self.head_pipeline, dict) else None
            )
            if pipeline_status in ("failed", "running", "pending"):
                blockers.append(f"Pipeline {pipeline_status}")

        # Check merge status for conflicts
        if self._merge_status == "cannot_be_merged":
            blockers.append("Has conflicts")

        # Check detailed merge status (GitLab 15.6+)
        if self._detailed_merge_status:
            if self._detailed_merge_status == "draft":
                blockers.append("MR is draft")
            elif self._detailed_merge_status == "discussions_not_resolved":
                blockers.append("Unresolved discussions")
            elif self._detailed_merge_status == "blocked_status":
                blockers.append("Blocked by rule")

        # Check approvals
        if self._approvals_left > 0:
            blockers.append(f"{self._approvals_left} approvals needed")

        return blockers

    @computed_field
    @property
    def ready_to_merge(self) -> bool:
        """Whether MR can be merged now."""
        return self.state == "opened" and len(self.blockers) == 0


class MergeRequestDiff(BaseGitLabModel):
    """Single file change in a merge request."""

    path: str = Field(alias="new_path", description="File path (new path if renamed)")
    old_path: str | None = Field(None, description="Original path if renamed")
    diff: Annotated[str, BeforeValidator(ensure_string)] = Field(
        default="", description="Unified diff content"
    )

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
    approved_by: list[UserRef] = Field(default_factory=list, description="Users who approved")

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
    created: RelativeTime = Field(alias="created_at", description="When created (relative)")
    stages: list[str] = Field(default_factory=list, description="Pipeline stages")
    failed_jobs: list[str] = Field(default_factory=list, description="Names of failed jobs")

    @field_validator("failed_jobs", mode="before")
    @classmethod
    def extract_failed_jobs(cls, v):
        """Extract job names from failed_jobs list."""
        if not v or not isinstance(v, list):
            return []
        return [j.get("name", "unknown") if isinstance(j, dict) else str(j) for j in v]


class ApprovalResult(BaseGitLabModel):
    """Result of approving or unapproving a merge request."""

    approved: bool = Field(description="Whether MR is now approved")
    merge_request_iid: int = Field(description="MR number")


class ApprovalRule(BaseGitLabModel):
    """Single approval rule."""

    rule_type: str | None = Field(None, description="Type of approval rule")
    eligible_approvers: list[dict] = Field(
        default_factory=list, description="List of eligible approvers"
    )
    approvals_required: int | None = Field(None, description="Approvals required for this rule")
    contains_hidden_groups: bool | None = Field(
        None, description="Whether rule contains hidden groups"
    )


class ApprovalStateDetailed(BaseGitLabModel):
    """Detailed approval state for a merge request."""

    iid: int = Field(description="MR number within the project")
    approved: bool = Field(description="Whether MR is approved")
    approved_by: list[UserRef] = Field(default_factory=list, description="Users who approved")
    approvals_required: int = Field(0, description="Total approvals required")
    approvals_left: int = Field(0, description="Remaining approvals needed")
    approval_rules_left: list[ApprovalRule] = Field(
        default_factory=list, description="Approval rules still needed", alias="rules"
    )


class MergeRequestNote(BaseGitLabModel):
    """Comment (note) on a merge request."""

    id: int = Field(description="Note ID")
    author_id: int = Field(default=0, description="Author user ID")
    author: str = Field(description="Author username")
    created_at: str = Field(description="When created")
    updated_at: str = Field(description="When last updated")
    body: HtmlCommentFree = Field(description="Note content")
    system: bool = Field(description="Whether this is a system note")

    @model_validator(mode="before")
    @classmethod
    def normalize_author(cls, data):
        """Extract author_id and author username from nested author dict.

        Handles both plain dicts (from API responses) and RESTObjects
        (from python-gitlab, which have no author_id attribute).
        """
        if isinstance(data, dict):
            author = data.get("author")
            if isinstance(author, dict):
                data = dict(data)
                data.setdefault("author_id", author.get("id", 0))
                data["author"] = author.get("username", "unknown")
            return data
        # RESTObject: author is a nested dict attribute, author_id doesn't exist
        author = getattr(data, "author", None)
        if isinstance(author, dict):
            return {
                "id": getattr(data, "id", None),
                "author_id": author.get("id", 0),
                "author": author.get("username", "unknown"),
                "created_at": getattr(data, "created_at", ""),
                "updated_at": getattr(data, "updated_at", ""),
                "body": getattr(data, "body", ""),
                "system": getattr(data, "system", False),
            }
        return data

class MergeRequestVersion(BaseGitLabModel):
    """Version (iteration) of a merge request."""

    id: int = Field(description="Version ID")
    created_at: str = Field(description="When created")
    updated_at: str | None = Field(None, description="When updated")
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
