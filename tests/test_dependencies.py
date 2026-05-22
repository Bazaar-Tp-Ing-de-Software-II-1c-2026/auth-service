from unittest.mock import patch

import pytest

from app.api.dependencies import get_current_user, get_optional_user, require_admin
from app.exceptions.handler import ServiceException
from app.models import User


class TestGetCurrentUser:
    def test_missing_authorization_header_raises_401(self, db):
        with pytest.raises(ServiceException) as exc:
            get_current_user(authorization=None, db=db)

        assert exc.value.status_code == 401
        assert "Missing token" in exc.value.detail

    def test_invalid_scheme_raises_401(self, db):
        with pytest.raises(ServiceException) as exc:
            get_current_user(authorization="Basic abc", db=db)

        assert exc.value.status_code == 401

    def test_invalid_token_raises_401(self, db):
        with patch("app.api.dependencies.security.decode_token", return_value=None):
            with pytest.raises(ServiceException) as exc:
                get_current_user(authorization="Bearer invalid", db=db)

        assert exc.value.status_code == 401
        assert "Invalid token" in exc.value.detail

    def test_missing_sub_raises_401(self, db):
        with patch(
            "app.api.dependencies.security.decode_token", return_value={"sub": None}
        ):
            with pytest.raises(ServiceException) as exc:
                get_current_user(authorization="Bearer token", db=db)

        assert exc.value.status_code == 401
        assert "missing user id" in exc.value.detail

    def test_user_not_found_raises_404(self, db):
        with patch(
            "app.api.dependencies.security.decode_token", return_value={"sub": "999999"}
        ):
            with pytest.raises(ServiceException) as exc:
                get_current_user(authorization="Bearer token", db=db)

        assert exc.value.status_code == 404
        assert "User not found" in exc.value.detail

    def test_valid_token_returns_user(self, db, test_user):
        with patch(
            "app.api.dependencies.security.decode_token",
            return_value={"sub": str(test_user.id)},
        ):
            user = get_current_user(authorization="Bearer token", db=db)

        assert user.id == test_user.id


class TestGetOptionalUser:
    def test_no_header_returns_none(self, db):
        assert get_optional_user(authorization=None, db=db) is None

    def test_invalid_scheme_returns_none(self, db):
        assert get_optional_user(authorization="Token abc", db=db) is None

    def test_decode_returns_none_returns_none(self, db):
        with patch("app.api.dependencies.security.decode_token", return_value=None):
            assert get_optional_user(authorization="Bearer token", db=db) is None

    def test_missing_sub_returns_none(self, db):
        with patch("app.api.dependencies.security.decode_token", return_value={}):
            assert get_optional_user(authorization="Bearer token", db=db) is None

    def test_decode_exception_returns_none(self, db):
        with patch(
            "app.api.dependencies.security.decode_token",
            side_effect=RuntimeError("boom"),
        ):
            assert get_optional_user(authorization="Bearer token", db=db) is None

    def test_valid_token_returns_user(self, db, test_user):
        with patch(
            "app.api.dependencies.security.decode_token",
            return_value={"sub": str(test_user.id)},
        ):
            user = get_optional_user(authorization="Bearer token", db=db)

        assert user is not None
        assert user.id == test_user.id


class TestRequireAdmin:
    def test_non_admin_raises_403(self):
        current_user = User(role="user")

        with pytest.raises(ServiceException) as exc:
            require_admin(current_user=current_user)

        assert exc.value.status_code == 403
        assert "Admin only" in exc.value.detail

    def test_admin_is_returned(self):
        admin = User(role="admin")

        result = require_admin(current_user=admin)

        assert result is admin
