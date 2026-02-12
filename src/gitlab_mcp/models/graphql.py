"""GraphQL response models."""

from typing import Any

from pydantic import BaseModel, Field

from gitlab_mcp.models.base import BaseGitLabModel


class GraphQLError(BaseModel):
    """Single GraphQL error."""

    message: str = Field(description="Error message")
    locations: list[dict[str, Any]] | None = Field(
        default=None, description="Error locations in query"
    )
    extensions: dict[str, Any] | None = Field(
        default=None, description="Error extensions"
    )


class GraphQLResponse(BaseGitLabModel):
    """GraphQL query response wrapper."""

    data: dict[str, Any] | None = Field(
        default=None, description="Query result data"
    )
    errors: list[GraphQLError] | None = Field(
        default=None, description="Query errors if any"
    )


class PageInfo(BaseGitLabModel):
    """GraphQL pagination info."""

    has_next_page: bool = Field(
        default=False, description="Whether there are more pages"
    )
    has_previous_page: bool = Field(
        default=False, description="Whether there are previous pages"
    )
    start_cursor: str | None = Field(default=None, description="Cursor for first item")
    end_cursor: str | None = Field(default=None, description="Cursor for last item")


class PaginationResult(BaseGitLabModel):
    """Result of paginated GraphQL query."""

    all_pages: list[dict[str, Any]] = Field(
        default_factory=list, description="All fetched pages"
    )
    page_count: int = Field(default=0, description="Total pages fetched")
    complete: bool = Field(
        default=False, description="Whether pagination completed or hit max_pages"
    )
    errors: list[GraphQLError] | None = Field(
        default=None, description="Any errors encountered"
    )
    pages_fetched: int | None = Field(
        default=None, description="Pages fetched before error"
    )
    partial_results: list[dict[str, Any]] | None = Field(
        default=None, description="Partial results before error"
    )
