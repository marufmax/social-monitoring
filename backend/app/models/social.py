import uuid
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    String, TEXT, Boolean, TIMESTAMP, Integer, DECIMAL,
    ForeignKey, UniqueConstraint, text
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel, Base


class SocialUser(BaseModel):
    """Social media user profiles with influence metrics."""

    __tablename__ = "social_users"

    platform_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platforms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform_user_id: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        index=True,
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    display_name: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    profile_url: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    # Influence metrics
    follower_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    account_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Influence scoring
    influence_score: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), server_default=text("0"), nullable=False)

    engagement_rate: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 4),
        nullable=True,
    )

    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Profile data
    bio: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    location: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    website_url: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    created_on_platform_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # DDL has last_updated_at, not updated_at, so we define it manually instead of using TimestampMixin
    last_updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    platform: Mapped["Platform"] = relationship(
        "Platform",
        back_populates="social_users",
    )

    mentions: Mapped[List["Mention"]] = relationship(
        "Mention",
        back_populates="social_user",
        cascade="all, delete-orphan",
    )

    influencer_categories: Mapped[List["InfluencerCategory"]] = relationship(
        "InfluencerCategory",
        back_populates="social_user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("platform_id", "platform_user_id"),
    )


class InfluencerCategory(Base):
    """Categorize influencers for business purposes. Corresponds to influencer_categories DDL."""

    __tablename__ = "influencer_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    social_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    added_by: Mapped[str] = mapped_column(
        String(128), ForeignKey("app_users.user_id", ondelete="RESTRICT"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    social_user: Mapped["SocialUser"] = relationship(
        "SocialUser", back_populates="influencer_categories"
    )

    __table_args__ = (UniqueConstraint("workspace_id", "social_user_id", "category"),)