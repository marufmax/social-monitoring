import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, TEXT, TIMESTAMP, ForeignKey,
    UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel
from app.models import Workspace, AppUser, Mention


class MentionAssignment(BaseModel):
    """Assign mentions to team members for response."""

    __tablename__ = "mention_assignments"

    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assigned_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        index=True,
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    mention: Mapped["Mention"] = relationship(
        "Mention",
        back_populates="assignment",
    )

    responses: Mapped[List["MentionResponse"]] = relationship(
        "MentionResponse",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("mention_id", "workspace_id"),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'skipped')",
            name="check_assignment_status"
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="check_assignment_priority"
        ),
    )


class MentionResponse(BaseModel):
    """Track responses to mentions."""

    __tablename__ = "mention_responses"

    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assignment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mention_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    response_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    platform_response_id: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
        index=True,
    )

    response_content: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    response_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    responded_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    responded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # External integrations
    external_ticket_id: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    external_urls: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    # Internal notes
    internal_notes: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    # Relationships
    mention: Mapped["Mention"] = relationship(
        "Mention",
        back_populates="responses",
    )

    assignment: Mapped[Optional["MentionAssignment"]] = relationship(
        "MentionAssignment",
        back_populates="responses",
    )

    __table_args__ = (
        CheckConstraint(
            "response_type IN ('reply', 'direct_message', 'email', 'ticket', 'internal_note')",
            name="check_response_type"
        ),
        CheckConstraint(
            "response_status IN ('pending', 'sent', 'failed', 'cancelled')",
            name="check_response_status"
        ),
    )

