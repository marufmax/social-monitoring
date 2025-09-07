import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base model for all models"""

    type_annotation_map = {
        dict[str, Any]: "JSONB",
        Dict[str, Any]: "JSONB",
    }

class TimestampMixin:
    """Mixin for models that need created_at and updated_at timestamps"""

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )


class UUIDMixin:
    """Mixin for models that use UUID as primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
        nullable=False,
    )

class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model class with UUID primary key and timestamps."""

    __abstract__ = True

    def __repr__(self) -> str:
        """String representation of model instance."""
        class_name = self.__class__.__name__
        attrs = []

        # Include primary key
        if hasattr(self, 'id'):
            attrs.append(f"id={self.id}")

        # Include name or title if available
        for attr in ['name', 'title', 'display_name']:
            if hasattr(self, attr):
                value = getattr(self, attr)
                if value:
                    attrs.append(f"{attr}='{value}'")
                break

        attrs_str = ', '.join(attrs)
        return f"<{class_name}({attrs_str})>"

    def to_dict(self, exclude_fields: Optional[set] = None) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        exclude_fields = exclude_fields or set()

        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)

                # Handle datetime serialization
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                # Handle UUID serialization
                elif isinstance(value, uuid.UUID):
                    result[column.name] = str(value)
                else:
                    result[column.name] = value

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """Create model instance from dictionary."""
        # Filter out any keys that don't correspond to model columns
        valid_columns = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_columns}

        return cls(**filtered_data)


class SoftDeleteMixin:
    """Mixin for models that support soft deletion."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if model instance is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark instance as deleted."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore soft deleted instance."""
        self.deleted_at = None


class AuditMixin:
    """Mixin for models that need audit tracking."""

    created_by: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        index=True,
    )

    updated_by: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        index=True,
    )

# Common enums and constants
class StatusEnum:
    """Common status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ARCHIVED = "archived"
    DELETED = "deleted"


class PriorityEnum:
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class SeverityEnum:
    """Severity levels for alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"