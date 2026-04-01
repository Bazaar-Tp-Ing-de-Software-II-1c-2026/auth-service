import pytest
from datetime import timedelta
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    generate_numeric_code
)


class TestPasswordHashing:
    def test_hash_password_creates_different_hash(self):
        password = "mypassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_hash_password_is_not_plain(self):
        password = "mypassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > len(password)


class TestPasswordVerification:
    def test_verify_password_correct(self):
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "mypassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self):
        password = "MyPassword123"
        hashed = hash_password(password)
        assert verify_password("mypassword123", hashed) is False


class TestAccessToken:
    def test_create_access_token_returns_string(self):
        data = {"sub": "1"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        data = {"sub": "1"}
        expires_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded.get("sub") == "1"

    def test_create_access_token_contains_data(self):
        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded.get("sub") == "123"
        assert decoded.get("username") == "testuser"


class TestTokenDecoding:
    def test_decode_valid_token(self):
        data = {"sub": "1", "username": "test"}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded.get("sub") == "1"
        assert decoded.get("username") == "test"

    def test_decode_invalid_token(self):
        invalid_token = "invalid.token.here"
        decoded = decode_token(invalid_token)
        assert decoded is None

    def test_decode_empty_token(self):
        decoded = decode_token("")
        assert decoded is None

    def test_decode_tampered_token(self):
        data = {"sub": "1"}
        token = create_access_token(data)
        tampered = token[:-5] + "xxxxx"
        decoded = decode_token(tampered)
        assert decoded is None


class TestNumericCodeGeneration:
    def test_generate_code_default_length(self):
        code = generate_numeric_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_custom_length(self):
        code = generate_numeric_code(length=4)
        assert len(code) == 4
        assert code.isdigit()

    def test_generate_code_larger_length(self):
        code = generate_numeric_code(length=10)
        assert len(code) == 10
        assert code.isdigit()

    def test_generate_code_randomness(self):
        codes = [generate_numeric_code() for _ in range(100)]
        unique_codes = set(codes)
        assert len(unique_codes) > 90
