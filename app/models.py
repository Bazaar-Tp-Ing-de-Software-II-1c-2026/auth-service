from sqlalchemy import Boolean, Column, Integer, String
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