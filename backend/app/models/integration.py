import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    String, TEXT, Boolean, TIMESTAMP, Integer,
    ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class IntegrationProvider(BaseModel):
    """Available third-party integration providers."""

    __tablename__ = "integration_providers"

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    provider_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    icon_url: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    configuration_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )

    capabilities: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={
            "notifications": False,
            "ticket_creation": False,
            "data_export": False,
            "oauth": False
        },
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "provider_type IN ('notification', 'ticketing', 'crm', 'analytics', 'storage')",
            name="check_provider_type"
        ),
    )


class WorkspaceIntegration(BaseModel):
    """Configured integrations for workspaces."""

    __tablename__ = "workspace_integrations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    configuration: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )

    encrypted_credentials: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,  # Encrypted JSON string
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    sync_error: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    created_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relationships
    provider: Mapped["IntegrationProvider"] = relationship(
        "IntegrationProvider",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "provider_id", "name"),
        CheckConstraint(
            "status IN ('active', 'error', 'disabled', 'pending')",
            name="check_integration_status"
        ),
    )

