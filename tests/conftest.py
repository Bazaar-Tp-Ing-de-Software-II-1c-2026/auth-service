import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.database import Base, get_db
from app.models import User
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    yield db_session
    db_session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    from app.security import hash_password
    
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("password123"),
        first_name="Test",
        last_name="User",
        role="user",
        blocked=False,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    from app.security import hash_password
    
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=hash_password("admin123"),
        first_name="Admin",
        last_name="User",
        role="admin",
        blocked=False,
        is_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def valid_user_data():
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "SecurePass123!",
        "first_name": "New",
        "last_name": "User"
    }
