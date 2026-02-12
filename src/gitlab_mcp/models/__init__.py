"""Pydantic models for responses.

Organized by domain. Import from submodules or use convenience re-exports here.
"""

from gitlab_mcp.models.base import BaseGitLabModel, relative_time
from gitlab_mcp.models.merge_requests import (
    MergeRequestSummary,
    MergeRequestDiff,
    ApprovalResult,
    ApprovalStateDetailed,
    MergeRequestNote,
    MergeRequestVersion,
    FileChange,
    ChangesSummary,
)
from gitlab_mcp.models.issues import (
    IssueSummary,
    IssueNote,
    IssueLink,
    IssueDeleteResult,
    IssueLinkDeleteResult,
    RelatedMergeRequest,
    IssueTimeStats,
    IssueTimeAddResult,
)
from gitlab_mcp.models.repository import (
    FileSummary,
    FileContents,
    CommitSummary,
    BranchSummary,
    FileOperationResult,
    BranchDeleteResult,
    CommitPushResult,
    CommitDetails,
    CommitDiffResult,
    BranchDiffResult,
    BranchComparison,
    FileDeleteResult,
    FileChange as RepositoryFileChange,
    ComparisonCommit,
)
from gitlab_mcp.models.pipelines import PipelineSummary, JobSummary
from gitlab_mcp.models.labels import (
    LabelSummary,
    LabelDeleteResult,
    LabelSubscriptionResult,
)
from gitlab_mcp.models.milestones import (
    MilestoneSummary,
    MilestoneDeleteResult,
    MilestoneBurndownEvent,
    MilestonePromoteResult,
)
from gitlab_mcp.models.discussions import DiscussionSummary, NoteSummary, NoteDeleteResult, DiscussionNoteDeleteResult
from gitlab_mcp.models.wiki import (
    WikiPageSummary,
    WikiPageDetail,
    WikiPageDeleteResult,
    WikiAttachmentResult,
)
from gitlab_mcp.models.releases import (
    ReleaseSummary,
    ReleaseDeleteResult,
    ReleaseEvidence,
    ReleaseAssetDownload,
    ReleaseLink,
    ReleaseLinkDeleteResult,
)
from gitlab_mcp.models.draft_notes import DraftNoteSummary, DraftNoteDeleteResult, DraftNotePublishResult, BulkPublishDraftNotesResult
from gitlab_mcp.models.uploads import UploadSummary, DownloadResult
from gitlab_mcp.models.misc import NamespaceSummary, UserSummary, EventSummary, IterationSummary, NamespaceVerification
from gitlab_mcp.models.graphql import GraphQLResponse, PaginationResult, GraphQLError, PageInfo

__all__ = [
    # Base
    "BaseGitLabModel",
    "relative_time",
    # MRs
    "MergeRequestSummary",
    "MergeRequestDiff",
    "ApprovalResult",
    "ApprovalStateDetailed",
    "MergeRequestNote",
    "MergeRequestVersion",
    "FileChange",
    "ChangesSummary",
    # Issues
    "IssueSummary",
    "IssueNote",
    "IssueLink",
    "IssueDeleteResult",
    "IssueLinkDeleteResult",
    "RelatedMergeRequest",
    "IssueTimeStats",
    "IssueTimeAddResult",
    # Repository
    "FileSummary",
    "FileContents",
    "CommitSummary",
    "BranchSummary",
    "FileOperationResult",
    "BranchDeleteResult",
    "CommitPushResult",
    "CommitDetails",
    "CommitDiffResult",
    "BranchDiffResult",
    "BranchComparison",
    "FileDeleteResult",
    "RepositoryFileChange",
    "ComparisonCommit",
    # Pipelines
    "PipelineSummary",
    "JobSummary",
    # Labels
    "LabelSummary",
    "LabelDeleteResult",
    "LabelSubscriptionResult",
    # Milestones
    "MilestoneSummary",
    "MilestoneDeleteResult",
    "MilestoneBurndownEvent",
    "MilestonePromoteResult",
    # Discussions
    "DiscussionSummary",
    "NoteSummary",
    "NoteDeleteResult",
    "DiscussionNoteDeleteResult",
    # Wiki
    "WikiPageSummary",
    "WikiPageDetail",
    "WikiPageDeleteResult",
    "WikiAttachmentResult",
    # Releases
    "ReleaseSummary",
    "ReleaseDeleteResult",
    "ReleaseEvidence",
    "ReleaseAssetDownload",
    "ReleaseLink",
    "ReleaseLinkDeleteResult",
    # Draft Notes
    "DraftNoteSummary",
    "DraftNoteDeleteResult",
    "DraftNotePublishResult",
    "BulkPublishDraftNotesResult",
    # Uploads
    "UploadSummary",
    "DownloadResult",
    # Misc
    "NamespaceSummary",
    "NamespaceVerification",
    "UserSummary",
    "EventSummary",
    "IterationSummary",
    # GraphQL
    "GraphQLResponse",
    "PaginationResult",
    "GraphQLError",
    "PageInfo",
]
