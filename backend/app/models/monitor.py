from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, TEXT, TIMESTAMP,
    ForeignKey, Boolean, Integer, text, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel

if TYPE_CHECKING:
    from .workspace import Workspace
    from .user import AppUser
    from .alert import Alert, AlertRule
    from .mention import MonitorMention


class Monitor(BaseModel):
    """Keywords you are currently monitoring. Corresponds to monitors DDL."""

    __tablename__ = "monitors"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(TEXT, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    keywords: Mapped[List[str]] = mapped_column(ARRAY(TEXT), nullable=False)
    negative_keywords: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT), server_default=text("ARRAY[]::TEXT[]"), nullable=False
    )
    platforms: Mapped[List[str]] = mapped_column(ARRAY(TEXT), nullable=False)
    languages: Mapped[List[str]] = mapped_column(
        ARRAY(String(10)), server_default=text("ARRAY['en']"), nullable=False
    )

    # Monitoring settings
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"), nullable=False)
    real_time: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    include_retweets: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    min_followers: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    created_by: Mapped[str] = mapped_column(
        String(128), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=False
    )
    last_mention_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="monitors")
    creator: Mapped[AppUser] = relationship("AppUser", back_populates="monitors_created")

    # Placeholders for back-populates from other models
    alert_rules: Mapped[List[AlertRule]] = relationship("AlertRule", back_populates="monitor", cascade="all, delete-orphan")
    monitor_mentions: Mapped[List[MonitorMention]] = relationship("MonitorMention", back_populates="monitor", cascade="all, delete-orphan")
    alerts: Mapped[List[Alert]] = relationship("Alert", back_populates="monitor", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'archived')", name="monitors_status_check"),
    )

    def __repr__(self) -> str:
        return f"<Monitor(id={self.id}, name='{self.name}', status='{self.status}')>"