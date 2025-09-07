import uuid
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    String, TEXT, TIMESTAMP, Integer, DECIMAL, BigInteger,
    ForeignKey, UniqueConstraint, CheckConstraint, CHAR
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import MentionResponse, MentionAssignment, SocialUser, Monitor
from .base import BaseModel


class Mention(BaseModel):
    """Social media posts/mentions with analysis."""

    __tablename__ = "mentions"

    platform_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platforms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    social_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform_post_id: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        index=True,
    )

    # Content
    content_text: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
    )

    content_html: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    normalized_content: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )

    # Metadata
    post_type: Mapped[str] = mapped_column(
        String(50),
        default="post",
        nullable=False,
        index=True,
    )

    parent_post_id: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    media_urls: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    external_links: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    hashtags: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    mentioned_users: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    # Timestamps
    published_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(tz=timezone.utc),
        nullable=False,
    )

    # Engagement metrics
    likes_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    shares_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    comments_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    views_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Analysis results
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(3, 2),
        nullable=True,
        index=True,
    )

    sentiment_label: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    toxicity_score: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(3, 2),
        nullable=True,
    )

    spam_probability: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(3, 2),
        nullable=True,
    )

    # Business categorization
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    priority_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    social_user: Mapped["SocialUser"] = relationship(
        "SocialUser",
        back_populates="mentions",
    )

    monitor_mentions: Mapped[List["MonitorMention"]] = relationship(
        "MonitorMention",
        back_populates="mention",
        cascade="all, delete-orphan",
    )

    fingerprint: Mapped[Optional["MentionFingerprint"]] = relationship(
        "MentionFingerprint",
        back_populates="mention",
        uselist=False,
        cascade="all, delete-orphan",
    )

    assignment: Mapped[Optional["MentionAssignment"]] = relationship(
        "MentionAssignment",
        back_populates="mention",
        uselist=False,
        cascade="all, delete-orphan",
    )

    responses: Mapped[List["MentionResponse"]] = relationship(
        "MentionResponse",
        back_populates="mention",
        cascade="all, delete-orphan",
    )

    content_hash: Mapped[str] = mapped_column(
        CHAR(64),
        nullable=False,
        index=True,
    )

    similarity_hash: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("platform_id", "platform_post_id"),
        CheckConstraint(
            "processing_status IN ('pending', 'processed', 'error')",
            name="check_processing_status"
        ),
    )


class MonitorMention(BaseModel):
    """Track which mentions match which monitors."""

    __tablename__ = "monitor_mentions"

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    matched_keywords: Mapped[List[str]] = mapped_column(
        ARRAY(TEXT),
        default=[],
        nullable=False,
    )

    match_score: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=1.0,
        nullable=False,
    )

    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    monitor: Mapped["Monitor"] = relationship(
        "Monitor",
        back_populates="monitor_mentions",
    )

    mention: Mapped["Mention"] = relationship(
        "Mention",
        back_populates="monitor_mentions",
    )

    __table_args__ = (
        UniqueConstraint("monitor_id", "mention_id"),
    )


class MentionFingerprint(BaseModel):
    """Fingerprints for deduplication."""

    __tablename__ = "mention_fingerprints"
    __table_args__ = {"extend_existing": True}

    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mentions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Override the default id and timestamps from BaseModel
    id = None
    created_at = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(tz=timezone.utc),
        nullable=False,
    )
    updated_at = None

    # Relationships
    mention: Mapped["Mention"] = relationship(
        "Mention",
        back_populates="fingerprint",
    )

    assignments: Mapped[List["MentionAssignment"]] = relationship(
        "MentionAssignment",
        back_populates="mention",
        cascade="all, delete-orphan"
    )

    responses: Mapped[List["MentionResponse"]] = relationship(
        "MentionResponse",
        back_populates="mention",
        cascade="all, delete-orphan"
    )



