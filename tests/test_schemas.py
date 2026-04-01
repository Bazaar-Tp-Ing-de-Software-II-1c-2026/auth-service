import pytest
from pydantic import ValidationError
from app.schemas import (
    UserCreate,
    UserLogin,
    UserUpdate,
    UserOut,
    Token,
    TokenData,
    ForgotPasswordRequest,
    ResetPassword
)


class TestUserCreate:
    def test_valid_user_create(self, valid_user_data):
        user = UserCreate(**valid_user_data)
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.password == "SecurePass123!"
        assert user.first_name == "New"
        assert user.last_name == "User"

    def test_invalid_email(self, valid_user_data):
        valid_user_data["email"] = "invalid-email"
        with pytest.raises(ValidationError):
            UserCreate(**valid_user_data)

    def test_missing_required_field(self, valid_user_data):
        del valid_user_data["password"]
        with pytest.raises(ValidationError):
            UserCreate(**valid_user_data)

    def test_empty_string_password(self, valid_user_data):
        valid_user_data["password"] = ""
        user = UserCreate(**valid_user_data)
        assert user.password == ""


class TestUserLogin:
    def test_valid_login_with_email(self):
        login = UserLogin(identifier="test@example.com", password="password123")
        assert login.identifier == "test@example.com"
        assert login.password == "password123"

    def test_valid_login_with_username(self):
        login = UserLogin(identifier="testuser", password="password123")
        assert login.identifier == "testuser"
        assert login.password == "password123"

    def test_missing_identifier(self):
        with pytest.raises(ValidationError):
            UserLogin(password="password123")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            UserLogin(identifier="test@example.com")


class TestUserUpdate:
    def test_update_first_name(self):
        update = UserUpdate(first_name="John")
        assert update.first_name == "John"
        assert update.last_name is None

    def test_update_last_name(self):
        update = UserUpdate(last_name="Doe")
        assert update.first_name is None
        assert update.last_name == "Doe"

    def test_update_both_names(self):
        update = UserUpdate(first_name="John", last_name="Doe")
        assert update.first_name == "John"
        assert update.last_name == "Doe"

    def test_empty_update(self):
        update = UserUpdate()
        assert update.first_name is None
        assert update.last_name is None


class TestUserOut:
    def test_user_out_from_dict(self):
        data = {
            "id": 1,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "user",
            "blocked": False,
            "is_verified": True,
            "username": "testuser"
        }
        user_out = UserOut(**data)
        assert user_out.id == 1
        assert user_out.email == "test@example.com"
        assert user_out.role == "user"
        assert user_out.is_verified is True

    def test_user_out_default_blocked(self):
        data = {
            "id": 1,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "user",
            "username": "testuser"
        }
        user_out = UserOut(**data)
        assert user_out.blocked is False
        assert user_out.is_verified is False


class TestToken:
    def test_token_creation(self):
        token = Token(access_token="fake-jwt-token", token_type="bearer")
        assert token.access_token == "fake-jwt-token"
        assert token.token_type == "bearer"

    def test_missing_access_token(self):
        with pytest.raises(ValidationError):
            Token(token_type="bearer")

    def test_missing_token_type(self):
        with pytest.raises(ValidationError):
            Token(access_token="fake-jwt-token")


class TestTokenData:
    def test_token_data_with_username(self):
        data = TokenData(username="testuser")
        assert data.username == "testuser"

    def test_token_data_empty(self):
        data = TokenData()
        assert data.username is None


class TestForgotPasswordRequest:
    def test_valid_forgot_password(self):
        req = ForgotPasswordRequest(email="test@example.com")
        assert req.email == "test@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="invalid-email")

    def test_missing_email(self):
        with pytest.raises(ValidationError):
            ForgotPasswordRequest()


class TestResetPassword:
    def test_valid_reset_password(self):
        reset = ResetPassword(token="fake-token", new_password="NewPassword123!")
        assert reset.token == "fake-token"
        assert reset.new_password == "NewPassword123!"

    def test_missing_token(self):
        with pytest.raises(ValidationError):
            ResetPassword(new_password="NewPassword123!")

    def test_missing_new_password(self):
        with pytest.raises(ValidationError):
            ResetPassword(token="fake-token")
