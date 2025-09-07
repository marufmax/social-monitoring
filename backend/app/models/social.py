import uuid
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    String, TEXT, Boolean, TIMESTAMP, Integer, DECIMAL,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel


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
    follower_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )

    following_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    post_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    account_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    influence_score: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        default=0,
        nullable=False,
        index=True,
    )

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

    last_updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False,
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


class InfluencerCategory(BaseModel):
    """Categorize influencers for business purposes."""

    __tablename__ = "influencer_categories"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    social_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("social_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    added_by: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    social_user: Mapped["SocialUser"] = relationship(
        "SocialUser",
        back_populates="influencer_categories",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "social_user_id", "category"),
    )