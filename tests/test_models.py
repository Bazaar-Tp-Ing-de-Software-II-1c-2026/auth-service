import pytest
from app.models import User
from app.security import hash_password


class TestUserModel:
    def test_create_user(self, db):
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("password123"),
            first_name="Test",
            last_name="User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.role == "user"
        assert user.blocked is False
        assert user.is_verified is False

    def test_user_unique_email(self, db):
        user1 = User(
            email="test@example.com",
            username="user1",
            hashed_password=hash_password("pass123")
        )
        db.add(user1)
        db.commit()
        
        user2 = User(
            email="test@example.com",
            username="user2",
            hashed_password=hash_password("pass123")
        )
        db.add(user2)
        
        with pytest.raises(Exception):
            db.commit()

    def test_user_unique_username(self, db):
        user1 = User(
            email="test1@example.com",
            username="testuser",
            hashed_password=hash_password("pass123")
        )
        db.add(user1)
        db.commit()
        
        user2 = User(
            email="test2@example.com",
            username="testuser",
            hashed_password=hash_password("pass123")
        )
        db.add(user2)
        
        with pytest.raises(Exception):
            db.commit()

    def test_user_role_default(self, db):
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("pass123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.role == "user"

    def test_user_blocked_default(self, db):
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("pass123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.blocked is False

    def test_user_custom_role(self, db):
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("pass123"),
            role="admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.role == "admin"

    def test_query_user_by_email(self, db, test_user):
        found_user = db.query(User).filter(User.email == "test@example.com").first()
        assert found_user is not None
        assert found_user.username == "testuser"

    def test_query_user_by_username(self, db, test_user):
        found_user = db.query(User).filter(User.username == "testuser").first()
        assert found_user is not None
        assert found_user.email == "test@example.com"

    def test_update_user(self, db, test_user):
        test_user.blocked = True
        test_user.first_name = "Updated"
        db.commit()
        db.refresh(test_user)
        
        assert test_user.blocked is True
        assert test_user.first_name == "Updated"
