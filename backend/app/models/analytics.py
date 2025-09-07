from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    TIMESTAMP, Integer, DECIMAL, ForeignKey, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base

if TYPE_CHECKING:
    from .monitor import Monitor


class MonitorAnalyticsHourly(Base):
    """Hourly analytics aggregation for monitors. Corresponds to monitor_analytics_hourly DDL."""

    __tablename__ = "monitor_analytics_hourly"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    hour_bucket: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    # Volume metrics
    mention_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    unique_authors: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    # Engagement metrics
    total_likes: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_shares: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_comments: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    avg_engagement_rate: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 4), nullable=True)

    # Sentiment metrics
    positive_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    negative_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    neutral_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    avg_sentiment: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2), nullable=True)

    # Platform distribution
    platform_breakdown: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )
    top_authors: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    top_hashtags: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    monitor: Mapped[Monitor] = relationship("Monitor") # No back_populates in DDL

    __table_args__ = (UniqueConstraint("monitor_id", "hour_bucket"),)
