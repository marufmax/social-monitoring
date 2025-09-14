from __future__ import annotations
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, TIMESTAMP, Boolean, TEXT, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base, TimestampMixin

from .monitor import Monitor
from .alert import AlertRule, Alert
from .collaboration import MentionAssignment, MentionResponse

if TYPE_CHECKING:
    from .workspace import Workspace, WorkspaceMember

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
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    # --- Relationships to other models ---
    monitors_created: Mapped[List[Monitor]] = relationship(
        "Monitor", foreign_keys=[Monitor.created_by], back_populates="creator", lazy="selectin"
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

    @property
    def default_workspace(self) -> Optional[Workspace]:
        """Get the user's default workspace membership."""
        if self.workspace_memberships:
            return self.workspace_memberships[0].workspace
        return None

    def get_workspace_role(self, workspace_id: str) -> Optional[str]:
        """Get the user's role in a specific workspace."""
        for membership in self.workspace_memberships:
            if str(membership.workspace_id) == workspace_id:
                return membership.role
        return None

    def get_workspace_permissions(self, workspace_id: str) -> Dict[str, Any]:
        """
        Get the user's permissions in a specific workspace based on their role.

        Args:
            workspace_id (str): The ID of the workspace to check permissions for.

        Returns:
            list[str]: A list of permissions for the user in the specified workspace.
            Returns an empty list if no permissions are found.
        """
        for membership in self.workspace_memberships:
            if str(membership.workspace_id) == workspace_id:
                return membership.permissions
        return {}
