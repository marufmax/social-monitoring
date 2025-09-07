from datetime import datetime
from typing import List, Optional
import uuid
from sqlalchemy import String, Text, DateTime, ForeignKey, CheckConstraint, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models import Workspace, AppUser, Mention

class Base(DeclarativeBase):
    pass


class MentionAssignment(Base):
    __tablename__ = 'mention_assignments'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('uuid_generate_v4()')
    )

    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    assigned_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        server_default='pending',
        nullable=False
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        server_default='medium',
        nullable=False
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    mention: Mapped["Mention"] = relationship(
        "Mention",
        back_populates="assignments"
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="mention_assignments"
    )

    assignee: Mapped[Optional["AppUser"]] = relationship(
        "AppUser",
        foreign_keys=[assigned_to],
        back_populates="mention_assignments_assigned"
    )

    assigner: Mapped["AppUser"] = relationship(
        "AppUser",
        foreign_keys=[assigned_by],
        back_populates="mention_assignments_created"
    )

    responses: Mapped[List["MentionResponse"]] = relationship(
        "MentionResponse",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'skipped')",
                        name="mention_assignments_status_check"),
        CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name="mention_assignments_priority_check"),
        UniqueConstraint('mention_id', 'workspace_id', name='uq_mention_workspace_assignment'),
    )


class MentionResponse(Base):
    __tablename__ = 'mention_responses'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('uuid_generate_v4()')
    )

    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    assignment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mention_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    response_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    platform_response_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    response_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    responded_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    external_ticket_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    external_urls: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        server_default=text("ARRAY[]::TEXT[]"),
        nullable=False
    )

    # Relationships
    mention: Mapped["Mention"] = relationship(
        "Mention",
        back_populates="responses"
    )

    assignment: Mapped[Optional["MentionAssignment"]] = relationship(
        "MentionAssignment",
        back_populates="responses"
    )

    responder: Mapped["AppUser"] = relationship(
        "AppUser",
        back_populates="mention_responses"
    )
