"""Label models."""

from pydantic import Field, field_serializer
from gitlab_mcp.models.base import BaseGitLabModel


class LabelSummary(BaseGitLabModel):
    """Label info."""

    id: int = Field(description="Unique label identifier")
    name: str = Field(description="Label name")
    color: str = Field(description="Label color (hex code)")
    description: str = Field(default="", description="Label description")
    text_color: str = Field(default="#FFFFFF", description="Text color for contrast")

    @field_serializer("description")
    def serialize_description(self, v: str) -> str:
        """Ensure description is never None."""
        return v or ""

    @field_serializer("text_color")
    def serialize_text_color(self, v: str) -> str:
        """Ensure text_color has a default."""
        return v or "#FFFFFF"


class LabelDeleteResult(BaseGitLabModel):
    """Result of deleting a label."""

    id: int = Field(description="Label ID that was deleted")
    deleted: bool = Field(description="Whether deletion was successful")


class LabelSubscriptionResult(BaseGitLabModel):
    """Result of label subscription action."""

    name: str = Field(description="Label name")
    subscribed: bool = Field(description="Current subscription status")
    message: str = Field(description="Subscription action message")
