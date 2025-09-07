from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    String, TEXT, TIMESTAMP, Integer, DECIMAL, BigInteger,
    ForeignKey, UniqueConstraint, CheckConstraint, CHAR, text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base, BaseModel

if TYPE_CHECKING:
    from .platform import Platform
    from .social import SocialUser
    from .monitor import Monitor
    from .mention_assignment import MentionAssignment, MentionResponse


class Mention(BaseModel):
    """Social media posts/mentions with analysis. Corresponds to mentions DDL."""

    __tablename__ = "mentions"

    platform_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False
    )
    social_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_users.id", ondelete="CASCADE"), nullable=False
    )
    platform_post_id: Mapped[str] = mapped_column(TEXT, nullable=False)

    # Content
    content_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    content_html: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    normalized_content: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Metadata
    post_type: Mapped[str] = mapped_column(String(50), server_default=text("'post'"), nullable=False)
    parent_post_id: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    media_urls: Mapped[List[str]] = mapped_column(ARRAY(TEXT), server_default=text("ARRAY[]::TEXT[]"))
    external_links: Mapped[List[str]] = mapped_column(ARRAY(TEXT), server_default=text("ARRAY[]::TEXT[]"))
    hashtags: Mapped[List[str]] = mapped_column(ARRAY(TEXT), server_default=text("ARRAY[]::TEXT[]"))
    mentioned_users: Mapped[List[str]] = mapped_column(ARRAY(TEXT), server_default=text("ARRAY[]::TEXT[]"))

    # Timestamps
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    # Engagement metrics
    likes_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    shares_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    comments_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    views_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    # Analysis
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2), nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    toxicity_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2), nullable=True)
    spam_probability: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2), nullable=True)

    # Business categorization
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    priority_score: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    # Processing
    processing_status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))

    # Relationships
    social_user: Mapped[SocialUser] = relationship("SocialUser", back_populates="mentions")
    monitor_mentions: Mapped[List[MonitorMention]] = relationship(
        "MonitorMention", back_populates="mention", cascade="all, delete-orphan"
    )
    fingerprint: Mapped[Optional[MentionFingerprint]] = relationship(
        "MentionFingerprint", back_populates="mention", uselist=False, cascade="all, delete-orphan"
    )
    assignment: Mapped[Optional[MentionAssignment]] = relationship(
        "MentionAssignment", back_populates="mention", uselist=False, cascade="all, delete-orphan"
    )
    assignments: Mapped[List[MentionAssignment]] = relationship("MentionAssignment") # For backpop from MentionAssignment
    responses: Mapped[List[MentionResponse]] = relationship(
        "MentionResponse", back_populates="mention", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("platform_id", "platform_post_id"),
        CheckConstraint("processing_status IN ('pending', 'processed', 'error')"),
    )


class MonitorMention(BaseModel):
    """Track which mentions match which monitors. Corresponds to monitor_mentions DDL."""

    __tablename__ = "monitor_mentions"

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mentions.id", ondelete="CASCADE"), nullable=False
    )
    matched_keywords: Mapped[List[str]] = mapped_column(ARRAY(TEXT), server_default=text("ARRAY[]::TEXT[]"))
    match_score: Mapped[Decimal] = mapped_column(DECIMAL(5, 4), server_default=text("1.0"))
    detected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    monitor: Mapped[Monitor] = relationship("Monitor", back_populates="monitor_mentions")
    mention: Mapped[Mention] = relationship("Mention", back_populates="monitor_mentions")

    __table_args__ = (UniqueConstraint("monitor_id", "mention_id"),)


class MentionFingerprint(Base):
    """Fingerprints for deduplication. Corresponds to mention_fingerprints DDL."""

    __tablename__ = "mention_fingerprints"

    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mentions.id", ondelete="CASCADE"), primary_key=True
    )
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    similarity_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    mention: Mapped[Mention] = relationship("Mention", back_populates="fingerprint")
