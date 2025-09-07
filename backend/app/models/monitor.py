import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String, TEXT, TIMESTAMP,
    ForeignKey, Boolean, Integer, Text, text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel
from app.models import Workspace, AppUser
from sqlalchemy.sql import func

class Monitor(BaseModel):
    """Keywords you are currently monitoring."""

    __tablename__ = "monitors"

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

    description: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    keywords: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        nullable=False,
    )

    negative_keywords: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    # 'facebook', 'Twitter', 'instagram', 'news'
    platforms: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        nullable=False,
    )

    # Monitoring settings
    status: Mapped[str] = mapped_column(
        String(20),
        server_default='active',
        nullable=False
    )

    real_time: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text('TRUE'),
        nullable=False
    )

    include_retweets: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text('FALSE'),
        nullable=False
    )

    min_followers: Mapped[int] = mapped_column(
        Integer,
        server_default=text('0'),
        nullable=False
    )

    created_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(tz=timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(tz=timezone.utc),
        onupdate=func.now(),
        nullable=False
    )

    last_mention_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="monitors"
    )

    creator: Mapped["AppUser"] = relationship(
        "AppUser",
        back_populates="monitors_created"
    )

    # Add the check constraint
    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'archived')", name="monitors_status_check"),
    )

    def __repr__(self) -> str:
        return f"<Monitor(id={self.id}, name='{self.name}', status='{self.status}')>"