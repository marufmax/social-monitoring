import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    String, TEXT, TIMESTAMP, Integer, BigInteger,
    ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class DataExport(BaseModel):
    """Track data export requests and status."""

    __tablename__ = "data_exports"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    requested_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    export_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    export_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    filters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_records: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    processed_records: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    file_path: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    download_url: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "export_type IN ('mentions', 'analytics', 'users', 'monitors', 'alerts')",
            name="check_export_type"
        ),
        CheckConstraint(
            "export_format IN ('csv', 'xlsx', 'json', 'pdf')",
            name="check_export_format"
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'expired')",
            name="check_export_status"
        ),
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="check_progress_range"
        ),
    )
