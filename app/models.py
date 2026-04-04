from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text
from datetime import datetime
from .database import Base

# Table for users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
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
    description = Column(Text, nullable=True) 
    profile_picture_url = Column(String, nullable=True)