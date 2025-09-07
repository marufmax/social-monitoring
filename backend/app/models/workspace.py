import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy import (
    String, TEXT, Boolean, TIMESTAMP, DECIMAL, Integer,
    ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel
from app.models import Monitor


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
        default={
            "data_retention_days": 90,
            "auto_assignment": False
        },
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

    __table_args__ = (
        CheckConstraint(
            "slug ~ '^[a-z0-9-]+$'",
            name="check_workspace_slug_format"
        ),
    )


class WorkspaceMember(BaseModel):
    """Workspace membership with roles and permissions."""

    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="member",
        nullable=False,
        index=True,
    )

    permissions: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={
            "monitors": {"create": True, "edit": True, "delete": False},
            "mentions": {"assign": True, "respond": True},
            "analytics": {"view": True},
            "billing": {"view": False}
        },
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="members",
    )

    user: Mapped["AppUser"] = relationship(
        "AppUser",
        back_populates="workspace_memberships",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="check_member_role"
        ),
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
        default={
            "monitors": 5,
            "keywords_per_monitor": 10,
            "mentions_per_month": 1000,
            "team_members": 3,
            "api_calls_per_month": 10000,
            "data_retention_days": 30
        },
        nullable=False,
    )

    features: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=["basic_monitoring", "email_alerts"],
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )


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
        String(20),
        default="active",
        nullable=False,
        index=True,
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
        default={
            "mentions_collected": 0,
            "api_calls": 0,
            "alerts_sent": 0,
            "active_monitors": 0
        },
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "period_start"),
    )