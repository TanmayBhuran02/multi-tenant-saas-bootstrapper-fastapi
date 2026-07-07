import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class TimestampMixin:
    """Mixin that adds created_at and updated_at columns."""
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class SerializerMixin:
    """Mixin providing a generic to_dict() for JSON serialization."""

    _serialize_exclude = set()

    def to_dict(self, exclude=None):
        """Convert model instance to dictionary."""
        exclude = exclude or set()
        exclude = exclude | self._serialize_exclude
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
            value = getattr(self, column.name)
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, 'value'):
                value = value.value
            result[column.name] = value
        return result
