from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from datetime import datetime
from ..database import Base


# Table for users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    role = Column(
        String, default="user", server_default="user", nullable=False, index=True
    )
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

    # Shipping address fields
    shipping_address = Column(String(200), nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(100), nullable=True)
    shipping_postal_code = Column(String(20), nullable=True)
    shipping_country = Column(String(100), nullable=True)
    shipping_phone = Column(String(20), nullable=True)

    # PIN authentication fields
    pin_hash = Column(String(255), nullable=True)
    pin_device_id = Column(String(255), nullable=True, index=True)
    pin_failed_attempts = Column(Integer, default=0, nullable=False)
    pin_locked_until = Column(DateTime, nullable=True)
    pin_created_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
