from sqlalchemy import String, Column, Integer, DateTime, Boolean, Index
from datetime import datetime, timezone
from ..database import Base


class PushToken(Base):
    """Model for storing Expo push tokens per user/device."""
    __tablename__ = "push_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(500), nullable=False)
    device_id = Column(String(255), nullable=True, index=True)
    platform = Column(String(50), nullable=True)  # ios, android, web
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Index for efficient queries by user
    __table_args__ = (
        Index("ix_push_tokens_user_active", "user_id", "is_active"),
    )
