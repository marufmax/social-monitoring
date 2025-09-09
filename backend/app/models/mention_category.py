from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    String, TEXT, TIMESTAMP, CheckConstraint, text, ForeignKey, UniqueConstraint, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .base import Base

if TYPE_CHECKING:
    from .workspace import Workspace
    from .mention import Mention


class MentionCategory(Base):
    """Represents a user-defined category for mentions. Corresponds to mention_categories DDL."""

    __tablename__ = "mention_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    auto_assignment_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship("Workspace") # No back_populates in DDL
    assignments: Mapped[List[MentionCategoryAssignment]] = relationship(
        "MentionCategoryAssignment", back_populates="category", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("workspace_id", "name"),)


class MentionCategoryAssignment(Base):
    """Assigns a category to a mention. Corresponds to mention_category_assignments DDL."""

    __tablename__ = "mention_category_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    mention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mentions.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mention_categories.id", ondelete="CASCADE"), nullable=False
    )
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2), nullable=True)
    assigned_by: Mapped[str] = mapped_column(
        String(20), server_default=text("'auto'"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    mention: Mapped[Mention] = relationship("Mention") # No back_populates in DDL
    category: Mapped[MentionCategory] = relationship("MentionCategory", back_populates="assignments")

    __table_args__ = (
        UniqueConstraint("mention_id", "category_id"),
        CheckConstraint("assigned_by IN ('auto', 'manual')", name="check_mca_assigned_by"),
    )
