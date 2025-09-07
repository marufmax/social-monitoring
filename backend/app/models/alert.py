from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models import Workspace, AppUser, Monitor, BaseModel

class AlertRule(BaseModel):
    __tablename__ = 'alert_rules'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('uuid_generate_v4()')
    )

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    conditions: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("""
            '{
                "sentiment": {"enabled": false, "threshold": -0.5, "operator": "below"},
                "volume_spike": {"enabled": false, "percentage": 200, "timeframe_hours": 1},
                "influencer": {"enabled": false, "min_followers": 10000},
                "priority": {"enabled": false, "min_score": 70},
                "keywords": {"enabled": false, "keywords": [], "operator": "any"}
            }'::jsonb
        """),
        nullable=False
    )

    frequency: Mapped[str] = mapped_column(
        String(20),
        server_default='immediate',
        nullable=False
    )

    channels: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        server_default=text("ARRAY['email']"),
        nullable=False
    )

    recipients: Mapped[List[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        server_default='active',
        nullable=False
    )

    created_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    monitor: Mapped["Monitor"] = relationship(
        "Monitor",
        back_populates="alert_rules"
    )

    creator: Mapped["AppUser"] = relationship(
        "AppUser",
        back_populates="alert_rules_created"
    )

    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="rule",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("frequency IN ('immediate', 'hourly', 'daily', 'weekly')", name="alert_rules_frequency_check"),
        CheckConstraint("status IN ('active', 'paused')", name="alert_rules_status_check"),
    )


class Alert(Base):
    __tablename__ = 'alerts'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('uuid_generate_v4()')
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        server_default='medium',
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    mention_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        server_default=text("ARRAY[]::UUID[]")
    )

    alert_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False
    )

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    resolved_by: Mapped[Optional[str]] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id"),
        nullable=True
    )

    # Relationships
    rule: Mapped["AlertRule"] = relationship(
        "AlertRule",
        back_populates="alerts"
    )

    monitor: Mapped["Monitor"] = relationship(
        "Monitor",
        back_populates="alerts"
    )

    resolver: Mapped[Optional["AppUser"]] = relationship(
        "AppUser",
        foreign_keys=[resolved_by],
        back_populates="alerts_resolved"
    )

    deliveries: Mapped[List["AlertDelivery"]] = relationship(
        "AlertDelivery",
        back_populates="alert",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="alerts_severity_check"),
    )


class AlertDelivery(BaseModel):
    __tablename__ = 'alert_deliveries'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text('uuid_generate_v4()')
    )

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    recipient: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        server_default='pending',
        nullable=False
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        server_default=text('0'),
        nullable=False
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    alert: Mapped["Alert"] = relationship(
        "Alert",
        back_populates="deliveries"
    )

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'bounced')", name="alert_deliveries_status_check"),
    )
