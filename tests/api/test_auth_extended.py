from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from app.api import dependencies as auth_dependencies
from app.exceptions.handler import ServiceException
from app.services import auth_service as auth_service_module
from app.models import User
from app.security import create_access_token, hash_password, verify_password


def _create_user(db, **overrides):
    data = {
        "email": "user@example.com",
        "username": "user1",
        "hashed_password": hash_password("Password123"),
        "first_name": "User",
        "last_name": "One",
        "role": "user",
        "blocked": False,
        "is_verified": False,
    }
    data.update(overrides)
    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestVerifyCodeEndpoint:
    def test_verify_code_user_not_found(self, client):
        response = client.post(
            "/api/auth/verify-code",
            json={"email": "missing@example.com", "code": "ABC12345"},
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_verify_code_already_verified(self, client, test_user):
        response = client.post(
            "/api/auth/verify-code",
            json={"email": test_user.email, "code": "ABC12345"},
        )
        assert response.status_code == 200
        assert "ya está verificado" in response.json()["message"]

    def test_verify_code_requires_existing_code(self, client, db):
        user = _create_user(db, email="nocode@example.com", username="nocode", is_verified=False)

        response = client.post(
            "/api/auth/verify-code",
            json={"email": user.email, "code": "ABC12345"},
        )
        assert response.status_code == 400
        assert "No verification code has been sent" in response.json()["detail"]

    def test_verify_code_expired(self, client, db):
        user = _create_user(
            db,
            email="expired@example.com",
            username="expired",
            verification_code="ABCD1234",
            verification_code_expires=datetime.utcnow() - timedelta(minutes=1),
        )

        response = client.post(
            "/api/auth/verify-code",
            json={"email": user.email, "code": "ABCD1234"},
        )
        assert response.status_code == 400
        assert "Code has expired" in response.json()["detail"]

    def test_verify_code_wrong_code(self, client, db):
        user = _create_user(
            db,
            email="wrong@example.com",
            username="wrong",
            verification_code="ABCD1234",
            verification_code_expires=datetime.utcnow() + timedelta(hours=1),
        )

        response = client.post(
            "/api/auth/verify-code",
            json={"email": user.email, "code": "ZZZZ9999"},
        )
        assert response.status_code == 400
        assert "Incorrect code" in response.json()["detail"]

    def test_verify_code_success_case_insensitive(self, client, db):
        user = _create_user(
            db,
            email="ok@example.com",
            username="okuser",
            verification_code="ABCD1234",
            verification_code_expires=datetime.utcnow() + timedelta(hours=1),
        )

        with patch("app.services.auth_service.send_welcome_email") as mock_welcome:
            response = client.post(
                "/api/auth/verify-code",
                json={"email": user.email, "code": "abcd1234"},
            )

        assert response.status_code == 200
        assert "verificado exitosamente" in response.json()["message"]
        mock_welcome.assert_called_once()

        updated = db.query(User).filter(User.id == user.id).first()
        assert updated is not None
        assert updated.is_verified is True
        assert updated.verification_code is None
        assert updated.verification_code_expires is None


class TestResetPasswordWithCodeEndpoint:
    def test_reset_with_code_user_not_found(self, client):
        response = client.post(
            "/api/auth/reset-password-with-code",
            json={
                "email": "missing@example.com",
                "code": "ABCDEFGH",
                "new_password": "NewPass123",
            },
        )
        assert response.status_code == 404

    def test_reset_with_code_requires_code(self, client, db):
        user = _create_user(db, email="nocode2@example.com", username="nocode2")
        response = client.post(
            "/api/auth/reset-password-with-code",
            json={
                "email": user.email,
                "code": "ABCDEFGH",
                "new_password": "NewPass123",
            },
        )
        assert response.status_code == 400
        assert "No password reset code has been sent" in response.json()["detail"]

    def test_reset_with_code_expired(self, client, db):
        user = _create_user(
            db,
            email="expired2@example.com",
            username="expired2",
            verification_code="ABCDEFGH",
            verification_code_expires=datetime.utcnow() - timedelta(minutes=1),
        )

        response = client.post(
            "/api/auth/reset-password-with-code",
            json={
                "email": user.email,
                "code": "ABCDEFGH",
                "new_password": "NewPass123",
            },
        )
        assert response.status_code == 400
        assert "Code has expired" in response.json()["detail"]

    def test_reset_with_code_wrong_code(self, client, db):
        user = _create_user(
            db,
            email="wrong2@example.com",
            username="wrong2",
            verification_code="ABCDEFGH",
            verification_code_expires=datetime.utcnow() + timedelta(hours=1),
        )

        response = client.post(
            "/api/auth/reset-password-with-code",
            json={
                "email": user.email,
                "code": "ZZZZZZZZ",
                "new_password": "NewPass123",
            },
        )
        assert response.status_code == 400
        assert "Incorrect code" in response.json()["detail"]

    def test_reset_with_code_success(self, client, db):
        user = _create_user(
            db,
            email="ok2@example.com",
            username="ok2",
            verification_code="ABCDEFGH",
            verification_code_expires=datetime.utcnow() + timedelta(hours=1),
        )
        user_id = user.id
        old_hash = user.hashed_password

        response = client.post(
            "/api/auth/reset-password-with-code",
            json={
                "email": user.email,
                "code": "abcdefgh",
                "new_password": "BrandNew123",
            },
        )

        assert response.status_code == 200
        updated = db.query(User).filter(User.id == user_id).first()
        assert updated is not None
        assert updated.hashed_password != old_hash
        assert verify_password("BrandNew123", updated.hashed_password)
        assert updated.verification_code is None
        assert updated.verification_code_expires is None


class TestResetAndForgotPasswordEndpoints:
    def test_request_reset_password_success(self, client, db):
        user = _create_user(db, email="reset@example.com", username="resetuser")

        with patch("app.services.auth_service.send_reset_password_email") as mock_send:
            response = client.post(
                "/api/auth/request-reset-password",
                json={"email": user.email},
            )

        assert response.status_code == 200
        assert "email de reset de contraseña" in response.json()["message"]
        mock_send.assert_called_once()

        updated = db.query(User).filter(User.id == user.id).first()
        assert updated is not None
        assert updated.verification_code is not None
        assert updated.verification_code_expires is not None
        assert updated.last_password_reset_request is not None

    def test_request_reset_password_rate_limited(self, client, db):
        user = _create_user(
            db,
            email="rate@example.com",
            username="rateuser",
            last_password_reset_request=datetime.utcnow() - timedelta(seconds=30),
        )

        response = client.post(
            "/api/auth/request-reset-password",
            json={"email": user.email},
        )
        assert response.status_code == 429
        assert "Please wait before" in response.json()["detail"]

    def test_request_reset_password_missing_user_is_generic(self, client):
        with patch("app.services.auth_service.send_reset_password_email") as mock_send:
            response = client.post(
                "/api/auth/request-reset-password",
                json={"email": "nobody@example.com"},
            )

        assert response.status_code == 200
        assert "email de reset de contraseña" in response.json()["message"]
        mock_send.assert_not_called()

    def test_reset_password_invalid_scope(self, client):
        token = create_access_token({"sub": "1", "scope": "email-verification"})
        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPass123"},
        )
        assert response.status_code == 401

    def test_reset_password_missing_sub(self, client):
        token = create_access_token({"scope": "password-reset"})
        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPass123"},
        )
        assert response.status_code == 401

    def test_reset_password_user_not_found(self, client):
        token = create_access_token({"sub": "9999", "scope": "password-reset"})
        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPass123"},
        )
        assert response.status_code == 404

    def test_reset_password_token_mismatch(self, client, db):
        user = _create_user(db, email="mismatch@example.com", username="mismatch")
        token = create_access_token({"sub": str(user.id), "scope": "password-reset"})
        user.reset_token = "other-token"
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPass123"},
        )
        assert response.status_code == 401

    def test_reset_password_success(self, client, db):
        user = _create_user(db, email="okreset@example.com", username="okreset")
        user_id = user.id
        token = create_access_token({"sub": str(user.id), "scope": "password-reset"})
        user.reset_token = token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "StrongPass123"},
        )

        assert response.status_code == 200
        updated = db.query(User).filter(User.id == user_id).first()
        assert updated is not None
        assert verify_password("StrongPass123", updated.hashed_password)
        assert updated.reset_token is None
        assert updated.reset_token_expires is None


class TestGoogleLoginEndpoint:
    def test_google_login_without_client_ids(self, client, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID_WEB", raising=False)
        monkeypatch.delenv("GOOGLE_CLIENT_ID_ANDROID", raising=False)

        response = client.post("/api/auth/google-login", json={"id_token": "token"})
        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]

    def test_google_login_invalid_token(self, client, monkeypatch):
        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_WEB", "web-id")
        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_ANDROID", "android-id")

        with patch("app.services.auth_service.id_token.verify_oauth2_token", side_effect=[Exception("web fail"), Exception("android fail")]):
            response = client.post("/api/auth/google-login", json={"id_token": "bad-token"})

        assert response.status_code == 401
        assert "Invalid or expired Google token" in response.json()["detail"]

    def test_google_login_missing_email(self, client, monkeypatch):
        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_WEB", "web-id")
        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_ANDROID", "")

        with patch("app.services.auth_service.id_token.verify_oauth2_token", return_value={"given_name": "No", "family_name": "Email"}):
            response = client.post("/api/auth/google-login", json={"id_token": "token"})

        assert response.status_code == 400
        assert "Email not found in Google token" in response.json()["detail"]

    def test_google_login_existing_blocked_user(self, client, db, monkeypatch):
        blocked = _create_user(
            db,
            email="blocked@example.com",
            username="blockeduser",
            blocked=True,
            is_verified=True,
        )
        assert blocked.blocked is True

        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_WEB", "web-id")
        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_ANDROID", "")
        with patch("app.services.auth_service.id_token.verify_oauth2_token", return_value={"email": blocked.email, "given_name": "Block", "family_name": "Ed"}):
            response = client.post("/api/auth/google-login", json={"id_token": "token"})

        assert response.status_code == 403

    def test_google_login_existing_unverified_user_gets_verified(self, client, db, monkeypatch):
        user = _create_user(
            db,
            email="google-existing@example.com",
            username="googleexisting",
            first_name=None,
            last_name=None,
            is_verified=False,
        )

        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_WEB", "web-id")
        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_ANDROID", "")
        idinfo = {
            "email": user.email,
            "given_name": "Google",
            "family_name": "User",
        }

        with patch("app.services.auth_service.id_token.verify_oauth2_token", return_value=idinfo), patch("app.services.auth_service.send_welcome_email") as mock_welcome:
            response = client.post("/api/auth/google-login", json={"id_token": "token"})

        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        mock_welcome.assert_called_once()

        updated = db.query(User).filter(User.id == user.id).first()
        assert updated is not None
        assert updated.is_verified is True
        assert updated.first_name == "Google"
        assert updated.last_name == "User"

    def test_google_login_creates_new_user_and_resolves_username_collision(self, client, db, monkeypatch):
        _create_user(
            db,
            email="john-existing@example.com",
            username="john",
            is_verified=True,
        )

        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_WEB", "web-id")
        monkeypatch.setattr(auth_service_module.settings, "GOOGLE_CLIENT_ID_ANDROID", "")
        idinfo = {
            "email": "john@example.com",
            "given_name": "John",
            "family_name": "New",
        }

        with patch("app.services.auth_service.id_token.verify_oauth2_token", return_value=idinfo), patch("app.services.auth_service.send_welcome_email") as mock_welcome:
            response = client.post("/api/auth/google-login", json={"id_token": "token"})

        assert response.status_code == 200
        mock_welcome.assert_called_once()

        created = db.query(User).filter(User.email == "john@example.com").first()
        assert created is not None
        assert created.username == "john1"
        assert created.is_verified is True


class TestAuthHelpers:
    def test_get_optional_user_without_header_returns_none(self, db):
        assert auth_dependencies.get_optional_user(None, db) is None

    def test_get_optional_user_with_bad_header_returns_none(self, db):
        assert auth_dependencies.get_optional_user("Token abc", db) is None

    def test_get_optional_user_with_invalid_token_returns_none(self, db):
        assert auth_dependencies.get_optional_user("Bearer invalid-token", db) is None

    def test_get_optional_user_with_valid_token_returns_user(self, db):
        user = _create_user(db, email="opt@example.com", username="optuser", is_verified=True)
        token = create_access_token({"sub": str(user.id)})

        resolved = auth_dependencies.get_optional_user(f"Bearer {token}", db)
        assert resolved is not None
        assert resolved.id == user.id

    def test_require_admin_rejects_non_admin(self, test_user):
        with pytest.raises(ServiceException) as exc:
            auth_dependencies.require_admin(test_user)
        assert exc.value.status_code == 403

    def test_require_admin_accepts_admin(self, test_admin):
        result = auth_dependencies.require_admin(test_admin)
        assert result.id == test_admin.id
