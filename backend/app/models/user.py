import uuid
from typing import Optional, Dict, Any
from sqlalchemy import String, TIMESTAMP, Boolean, TEXT
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class SuperTokensUser(Base, TimestampMixin):
    """SuperTokens user integration table."""

    __tablename__ = "supertokens_users"

    user_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        nullable=False,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
        index=True,
    )

    last_login_at: Mapped[Optional[TIMESTAMP]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationship to app user
    app_user: Mapped["AppUser"] = relationship(
        "AppUser",
        back_populates="supertokens_user",
        uselist=False,
    )


class AppUser(Base, TimestampMixin):
    """Application-specific user data."""

    __tablename__ = "app_users"

    user_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        index=True,
    )

    display_name: Mapped[Optional[str]] = mapped_column(
        TEXT,
        nullable=True,
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )

    preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default={
            "notifications": {
                "email": True,
                "push": True,
                "frequency": "immediate"
            }
        },
        nullable=False,
    )

    # GDPR compliance
    data_retention_until: Mapped[Optional[TIMESTAMP]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    consent_marketing: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    supertokens_user: Mapped["SuperTokensUser"] = relationship(
        "SuperTokensUser",
        back_populates="app_user",
    )

    workspace_memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )

