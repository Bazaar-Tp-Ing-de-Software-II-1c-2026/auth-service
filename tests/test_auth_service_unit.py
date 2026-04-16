from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions.handler import ServiceException
from app.schemas.schemas import ResetPassword
from app.services import auth_service


def test_check_rate_limit_raises_when_called_too_soon():
    last_request = datetime.now(timezone.utc) - timedelta(seconds=10)

    with pytest.raises(ServiceException) as exc:
        auth_service._check_rate_limit(last_request, "solicitar otro reset")

    assert exc.value.status_code == 429
    assert "Debes esperar" in exc.value.detail


def test_check_rate_limit_allows_when_window_elapsed():
    last_request = datetime.now(timezone.utc) - timedelta(seconds=120)
    auth_service._check_rate_limit(last_request, "solicitar otro reset")


def test_send_welcome_email_safe_swallows_exceptions():
    user = SimpleNamespace(email="user@example.com", first_name="User", username="user")

    with patch("app.services.auth_service.send_welcome_email", side_effect=RuntimeError("mail error")):
        auth_service._send_welcome_email_safe(user)


def test_google_login_without_client_ids_raises_500(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_WEB", "")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_ANDROID", "")

    with pytest.raises(ServiceException) as exc:
        auth_service.google_login(SimpleNamespace(id_token="bad"), MagicMock())

    assert exc.value.status_code == 500


def test_google_login_invalid_token_raises_401(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_WEB", "web")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_ANDROID", "android")

    with patch("app.services.auth_service.id_token.verify_oauth2_token", side_effect=[Exception("web fail"), Exception("android fail")]):
        with pytest.raises(ServiceException) as exc:
            auth_service.google_login(SimpleNamespace(id_token="bad"), MagicMock())

    assert exc.value.status_code == 401


def test_google_login_missing_email_raises_400(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_WEB", "web")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_ANDROID", "")

    with patch("app.services.auth_service.id_token.verify_oauth2_token", return_value={"given_name": "No"}):
        with pytest.raises(ServiceException) as exc:
            auth_service.google_login(SimpleNamespace(id_token="token"), MagicMock())

    assert exc.value.status_code == 400


def test_google_login_creates_new_user_and_returns_token(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_WEB", "web")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_ANDROID", "")

    db = MagicMock()
    idinfo = {"email": "john@example.com", "given_name": "John", "family_name": "New"}

    with patch("app.services.auth_service.id_token.verify_oauth2_token", return_value=idinfo), patch(
        "app.services.auth_service.auth_repository.get_user_by_email", return_value=None
    ), patch("app.services.auth_service.auth_repository.generate_unique_username", return_value="john1"), patch(
        "app.services.auth_service.auth_repository.create_user"
    ) as mock_create_user, patch("app.services.auth_service.security.hash_password", return_value="hashed"), patch(
        "app.services.auth_service.security.create_access_token", return_value="token123"
    ), patch("app.services.auth_service.send_welcome_email") as mock_welcome:
        result = auth_service.google_login(SimpleNamespace(id_token="token"), db)

    assert result == {"access_token": "token123", "token_type": "bearer"}
    mock_create_user.assert_called_once()
    mock_welcome.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_google_login_access_token_fallback_works(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_WEB", "web")
    monkeypatch.setattr(auth_service.settings, "GOOGLE_CLIENT_ID_ANDROID", "")

    db = MagicMock()
    access_token = "ya29.fake-token"
    userinfo = {"email": "web@example.com", "given_name": "Web", "family_name": "User"}

    with patch("app.services.auth_service.id_token.verify_oauth2_token", side_effect=Exception("not-jwt")), patch(
        "app.services.auth_service._get_google_userinfo_from_access_token", return_value=userinfo
    ), patch("app.services.auth_service.auth_repository.get_user_by_email", return_value=None), patch(
        "app.services.auth_service.auth_repository.generate_unique_username", return_value="webuser"
    ), patch("app.services.auth_service.auth_repository.create_user") as mock_create_user, patch(
        "app.services.auth_service.security.hash_password", return_value="hashed"
    ), patch("app.services.auth_service.security.create_access_token", return_value="token123"), patch(
        "app.services.auth_service.send_welcome_email"
    ):
        result = auth_service.google_login(SimpleNamespace(id_token=access_token), db)

    assert result == {"access_token": "token123", "token_type": "bearer"}
    mock_create_user.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_reset_password_token_mismatch_raises_401():
    payload = ResetPassword(token="token-1", new_password="StrongPass123")
    user = SimpleNamespace(reset_token="other", reset_token_expires=datetime.now(timezone.utc) + timedelta(hours=1))

    with patch("app.services.auth_service.security.decode_token", return_value={"sub": "1", "scope": "password-reset"}), patch(
        "app.services.auth_service.auth_repository.get_user_by_id", return_value=user
    ):
        with pytest.raises(ServiceException) as exc:
            auth_service.reset_password(payload, MagicMock())

    assert exc.value.status_code == 401


def test_reset_password_success_updates_user_and_clears_token():
    payload = ResetPassword(token="token-1", new_password="StrongPass123")
    user = SimpleNamespace(
        id=1,
        reset_token="token-1",
        reset_token_expires=datetime.now(timezone.utc) + timedelta(hours=1),
        hashed_password="oldhash",
    )

    with patch("app.services.auth_service.security.decode_token", return_value={"sub": "1", "scope": "password-reset"}), patch(
        "app.services.auth_service.auth_repository.get_user_by_id", return_value=user
    ), patch("app.services.auth_service.security.hash_password", return_value="newhash"), patch(
        "app.services.auth_service.auth_repository.save"
    ) as mock_save:
        result = auth_service.reset_password(payload, MagicMock())

    assert result["message"].startswith("Contraseña reseteada exitosamente")
    assert user.hashed_password == "newhash"
    assert user.reset_token is None
    assert user.reset_token_expires is None
    mock_save.assert_called_once()
