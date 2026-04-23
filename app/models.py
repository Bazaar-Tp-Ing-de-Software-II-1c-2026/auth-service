from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from .database import Base

# Table for users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(String, default="user", server_default="user", nullable=False, index=True)
    blocked = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    reset_token = Column(String, nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)
    verification_code = Column(String, nullable=True, index=True)
    verification_code_expires = Column(DateTime, nullable=True)
    last_password_reset_request = Column(DateTime, nullable=True)
    last_verification_email_request = Column(DateTime, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    description = Column(String(500), nullable=True, default="")


class UserPinDevice(Base):
    __tablename__ = "user_pin_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(128), nullable=False, unique=True, index=True)
    device_name = Column(String(128), nullable=True)
    platform = Column(String(32), nullable=True)
    hashed_pin = Column(String, nullable=False)
    pin_length = Column(Integer, nullable=False, default=6)
    pin_enabled = Column(Boolean, nullable=False, default=True)
    failed_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

