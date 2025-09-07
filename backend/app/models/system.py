import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    String, TEXT, Boolean, TIMESTAMP, Integer,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column
from .base import BaseModel


class SystemConfiguration(BaseModel):
    """System-wide configuration settings."""

    __tablename__ = "system_configuration"

    key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    value: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    updated_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )


class AuditLog(BaseModel):
    """System audit log for tracking important actions."""

    __tablename__ = "audit_logs"

    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    resource_id: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
        index=True,
    )

    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    __table_args__ = (
        Index("idx_audit_log_timestamp", "created_at"),
        Index("idx_audit_log_user_action", "user_id", "action"),
        Index("idx_audit_log_resource", "resource_type", "resource_id"),
    )


class SystemHealth(BaseModel):
    """Track system health metrics."""

    __tablename__ = "system_health"

    component: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )

    last_check_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    last_error_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    last_error_message: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('healthy', 'degraded', 'unhealthy', 'unknown')",
            name="check_health_status"
        ),
        Index("idx_system_health_component_time", "component", "last_check_at"),
    )