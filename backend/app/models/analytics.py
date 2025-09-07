import uuid
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy import TIMESTAMP, Integer, DECIMAL, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


class MonitorAnalyticsHourly(BaseModel):
    """Hourly analytics aggregation for monitors."""

    __tablename__ = "monitor_analytics_hourly"

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    hour_bucket: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
    )

    # Volume metrics
    mention_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    unique_authors: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Engagement metrics
    total_likes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_shares: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_comments: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    avg_engagement_rate: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 4),
        nullable=True,
    )

    # Sentiment metrics
    positive_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    negative_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    neutral_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    avg_sentiment: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(3, 2),
        nullable=True,
    )

    # Platform and content breakdown
    platform_breakdown: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )

    top_authors: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
    )

    top_hashtags: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("monitor_id", "hour_bucket"),
    )
    s: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        nullable=False,
    )

    languages: Mapped[List[str]] = mapped_column(
        ARRAY(String(10)),
        default=["en"],
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )

    real_time: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    include_retweets: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    min_followers: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    last_mention_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="monitors",
    )

    alert_rules: Mapped[List["AlertRule"]] = relationship(
        "AlertRule",
        back_populates="monitor",
        cascade="all, delete-orphan",
    )

    monitor_mentions: Mapped[List["MonitorMention"]] = relationship(
        "MonitorMention",
        back_populates="monitor",
        cascade="all, delete-orphan",
    )

    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="monitor",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'paused', 'archived')",
            name="check_monitor_status"
        ),
    )


class AlertRule(BaseModel):
    """Alert rules for monitors."""

    __tablename__ = "alert_rules"

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    conditions: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={
            "sentiment": {"enabled": False, "threshold": -0.5, "operator": "below"},
            "volume_spike": {"enabled": False, "percentage": 200, "timeframe_hours": 1},
            "influencer": {"enabled": False, "min_followers": 10000},
            "priority": {"enabled": False, "min_score": 70},
            "keywords": {"enabled": False, "keywords": [], "operator": "any"}
        },
        nullable=False,
    )

    frequency: Mapped[str] = mapped_column(
        String(20),
        default="immediate",
        nullable=False,
    )

    channels: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=["email"],
        nullable=False,
    )

    recipients: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=[],
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )

    created_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    monitor: Mapped["Monitor"] = relationship(
        "Monitor",
        back_populates="alert_rules",
    )

    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="rule",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "frequency IN ('immediate', 'hourly', 'daily', 'weekly')",
            name="check_alert_frequency"
        ),
        CheckConstraint(
            "status IN ('active', 'paused')",
            name="check_alert_rule_status"
        ),
    )


class Alert(BaseModel):
    """Generated alerts from alert rules."""

    __tablename__ = "alerts"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    message: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    mention_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        default=[],
        nullable=False,
    )

    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={},
        nullable=False,
    )

    triggered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    resolved_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id"),
        nullable=True,
    )

    # Relationships
    rule: Mapped["AlertRule"] = relationship(
        "AlertRule",
        back_populates="alerts",
    )

    monitor: Mapped["Monitor"] = relationship(
        "Monitor",
        back_populates="alerts",
    )

    deliveries: Mapped[List["AlertDelivery"]] = relationship(
        "AlertDelivery",
        back_populates="alert",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="check_alert_severity"
        ),
    )


class AlertDelivery(BaseModel):
    """Track alert delivery attempts."""

    __tablename__ = "alert_deliveries"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    recipient: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    alert: Mapped["Alert"] = relationship(
        "Alert",
        back_populates="deliveries",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'bounced')",
            name="check_delivery_status"
        ),
    )
