from __future__ import annotations
import uuid
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, TIMESTAMP, Boolean, TEXT, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base, TimestampMixin

from .workspace import WorkspaceMember
from .monitor import Monitor
from .alert import AlertRule, Alert
from .collaboration import MentionAssignment, MentionResponse


class SuperTokensUser(Base):
    """SuperTokens user integration table. Corresponds to supertokens_users DDL."""

    __tablename__ = "supertokens_users"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    # Relationship to app user
    app_user: Mapped[AppUser] = relationship(
        "AppUser",
        back_populates="supertokens_user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AppUser(Base, TimestampMixin):
    """Application-specific user data. Corresponds to app_users DDL."""

    __tablename__ = "app_users"

    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("supertokens_users.user_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(50), server_default=text("'UTC'"), nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(10), server_default=text("'en'"), nullable=False
    )
    preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text(
            """'{"notifications": {"email": true, "push": true, "frequency": "immediate"}}'::jsonb"""
        ),
        nullable=False,
    )

    # GDPR compliance
    data_retention_until: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    consent_marketing: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    # Relationships
    supertokens_user: Mapped[SuperTokensUser] = relationship(
        "SuperTokensUser", back_populates="app_user"
    )
    workspace_memberships: Mapped[List[WorkspaceMember]] = relationship(
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan"
    )

    # --- Relationships to other models ---
    monitors_created: Mapped[List[Monitor]] = relationship(
        "Monitor", foreign_keys=[Monitor.created_by], back_populates="creator"
    )
    alert_rules_created: Mapped[List[AlertRule]] = relationship(
        "AlertRule", foreign_keys=[AlertRule.created_by], back_populates="creator"
    )
    alerts_resolved: Mapped[List[Alert]] = relationship(
        "Alert", foreign_keys=[Alert.resolved_by], back_populates="resolver"
    )
    mention_assignments_assigned: Mapped[List[MentionAssignment]] = relationship(
        "MentionAssignment", foreign_keys=[MentionAssignment.assigned_to], back_populates="assignee"
    )
    mention_assignments_created: Mapped[List[MentionAssignment]] = relationship(
        "MentionAssignment", foreign_keys=[MentionAssignment.assigned_by], back_populates="assigner"
    )
    mention_responses: Mapped[List[MentionResponse]] = relationship(
        "MentionResponse", foreign_keys=[MentionResponse.responded_by], back_populates="responder"
    )
