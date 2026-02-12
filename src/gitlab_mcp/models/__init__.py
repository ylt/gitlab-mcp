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
from gitlab_mcp.models.issues import IssueSummary, IssueNote
from gitlab_mcp.models.repository import FileSummary, FileContents, CommitSummary, BranchSummary
from gitlab_mcp.models.pipelines import PipelineSummary, JobSummary
from gitlab_mcp.models.labels import LabelSummary
from gitlab_mcp.models.milestones import MilestoneSummary
from gitlab_mcp.models.discussions import DiscussionSummary, NoteSummary
from gitlab_mcp.models.wiki import WikiPageSummary, WikiPageDetail
from gitlab_mcp.models.releases import ReleaseSummary
from gitlab_mcp.models.draft_notes import DraftNoteSummary
from gitlab_mcp.models.uploads import UploadSummary, DownloadResult
from gitlab_mcp.models.misc import NamespaceSummary, UserSummary, EventSummary, IterationSummary
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
    # Repository
    "FileSummary",
    "FileContents",
    "CommitSummary",
    "BranchSummary",
    # Pipelines
    "PipelineSummary",
    "JobSummary",
    # Labels
    "LabelSummary",
    # Milestones
    "MilestoneSummary",
    # Discussions
    "DiscussionSummary",
    "NoteSummary",
    # Wiki
    "WikiPageSummary",
    "WikiPageDetail",
    # Releases
    "ReleaseSummary",
    # Draft Notes
    "DraftNoteSummary",
    # Uploads
    "UploadSummary",
    "DownloadResult",
    # Misc
    "NamespaceSummary",
    "UserSummary",
    "EventSummary",
    "IterationSummary",
    # GraphQL
    "GraphQLResponse",
    "PaginationResult",
    "GraphQLError",
    "PageInfo",
]
