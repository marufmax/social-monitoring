import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String, TEXT, Boolean, TIMESTAMP, Integer,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class NotificationTemplate(BaseModel):
    """Templates for different types of notifications."""

    __tablename__ = "notification_templates"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        index=True,
    )

    template_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    subject_template: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    body_template: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    variables: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    created_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "template_type IN ('alert', 'digest', 'welcome', 'report', 'reminder')",
            name="check_template_type"
        ),
        CheckConstraint(
            "channel IN ('email', 'sms', 'slack', 'teams', 'webhook', 'push')",
            name="check_notification_channel"
        ),
        Index("idx_notification_template_workspace_type", "workspace_id", "template_type"),
    )


class NotificationQueue(BaseModel):
    """Queue for outgoing notifications."""

    __tablename__ = "notification_queue"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipient_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    recipient_address: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    subject: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    body: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    scheduled_for: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )

    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    notification_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )

    # External provider tracking
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'sms', 'slack', 'teams', 'webhook', 'push')",
            name="check_queue_channel"
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="check_queue_priority"
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed', 'cancelled')",
            name="check_queue_status"
        ),
        Index("idx_notification_queue_processing", "status", "scheduled_for", "priority"),
    )


class NotificationPreference(BaseModel):
    """User notification preferences."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    channels: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=["email"],
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    frequency: Mapped[str] = mapped_column(
        String(20),
        default="immediate",
        nullable=False,
    )

    quiet_hours_start: Mapped[Optional[str]] = mapped_column(
        String(5),  # HH:MM format
        nullable=True,
    )

    quiet_hours_end: Mapped[Optional[str]] = mapped_column(
        String(5),  # HH:MM format
        nullable=True,
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "frequency IN ('immediate', 'hourly', 'daily', 'weekly', 'never')",
            name="check_preference_frequency"
        ),
        Index("idx_notification_pref_user_workspace", "user_id", "workspace_id"),
    )
