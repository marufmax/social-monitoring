import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy import (
    String, TEXT, Boolean, TIMESTAMP, DECIMAL, Integer,
    ForeignKey, UniqueConstraint, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base, BaseModel
from app.models.monitor import Monitor
from app.models.collaboration import MentionAssignment


class Workspace(BaseModel):
    """Workspace for team collaboration."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        index=True,
    )

    slug: Mapped[str] = mapped_column(
        TEXT,
        unique=True,
        nullable=False,
        index=True,
    )

    owner_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("""'{"data_retention_days": 90, "auto_assignment": false}'::jsonb"""),
        nullable=False,
    )

    # Relationships
    members: Mapped[List["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    monitors: Mapped[List["Monitor"]] = relationship(
        "Monitor",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    subscription: Mapped[Optional["WorkspaceSubscription"]] = relationship(
        "WorkspaceSubscription",
        back_populates="workspace",
        uselist=False,
    )

    mention_assignments: Mapped[List[MentionAssignment]] = relationship(
        "MentionAssignment", back_populates="workspace"
    )

    __table_args__ = (
        CheckConstraint(
            "slug ~ '^[a-z0-9-]+$'",
            name="check_workspace_slug_format"
        ),
    )


class WorkspaceMember(Base):
    """Workspace membership with roles and permissions. Corresponds to workspace_members DDL."""

    __tablename__ = "workspace_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), server_default=text("'member'"), nullable=False
    )
    permissions: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("""
            '{"monitors": {"create": true, "edit": true, "delete": false},
              "mentions": {"assign": true, "respond": true},
              "analytics": {"view": true},
              "billing": {"view": false}}'::jsonb
        """),
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["AppUser"] = relationship("AppUser", back_populates="workspace_memberships")

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id"),
        CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="check_member_role"),
    )


class SubscriptionPlan(BaseModel):
    """Available subscription plans."""

    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    price_monthly: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2),
        nullable=True,
    )

    price_annual: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 2),
        nullable=True,
    )

    limits: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("""
            '{"monitors": 5, "keywords_per_monitor": 10, "mentions_per_month": 1000,
              "team_members": 3, "api_calls_per_month": 10000, "data_retention_days": 30}'::jsonb
        """),
        nullable=False,
    )

    features: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        server_default=text("ARRAY['basic_monitoring', 'email_alerts']"),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)


class WorkspaceSubscription(BaseModel):
    """Workspace subscription details."""

    __tablename__ = "workspace_subscriptions"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20), server_default=text("'active'"), nullable=False
    )

    current_period_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    current_period_end: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
    )

    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="subscription",
    )

    plan: Mapped["SubscriptionPlan"] = relationship(
        "SubscriptionPlan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'cancelled', 'expired', 'past_due')",
            name="check_subscription_status"
        ),
    )


class UsageTracking(BaseModel):
    """Track workspace usage for billing."""

    __tablename__ = "usage_tracking"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
    )

    period_end: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    usage_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("""
            '{"mentions_collected": 0, "api_calls": 0, "alerts_sent": 0, "active_monitors": 0}'::jsonb
        """),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "period_start"),
    )