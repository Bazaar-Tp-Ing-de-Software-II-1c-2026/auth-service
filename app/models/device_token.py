from sqlalchemy import (
    String,
    Column,
    Integer,
    DateTime,
    Boolean,
    Index,
    UniqueConstraint,
)

from datetime import datetime, timezone
from ..database import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(500), nullable=False)
    device_id = Column(String(255), nullable=True, index=True)
    platform = Column(String(50), nullable=True)  # android, ios, web
    provider = Column(String(50), nullable=False, default="fcm")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_seen_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_device_tokens_user_active", "user_id", "is_active"),
        UniqueConstraint("token", name="uq_device_token"),
    )
