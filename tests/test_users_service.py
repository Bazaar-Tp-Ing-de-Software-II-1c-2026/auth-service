"""
Tests unitarios para app/services/users.py.
Cubre funciones como get_user_public_profile_by_id/username,
block_user, unblock_user, update_my_profile, list_users_admin, get_user_metrics.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.users import (
    get_my_profile,
    get_user_public_profile_by_id,
    get_user_public_profile_by_username,
    update_my_profile,
    block_user,
    unblock_user,
    list_users_admin,
    get_user_metrics,
)
from app.exceptions.handler import ServiceException
from app.models.user import User


def _make_user(**kwargs):
    user = MagicMock(spec=User)
    user.id = kwargs.get("id", 1)
    user.email = kwargs.get("email", "user@test.com")
    user.username = kwargs.get("username", "testuser")
    user.first_name = kwargs.get("first_name", "Test")
    user.last_name = kwargs.get("last_name", "User")
    user.role = kwargs.get("role", "user")
    user.blocked = kwargs.get("blocked", False)
    user.is_verified = kwargs.get("is_verified", True)
    return user


# ---------------------------------------------------------------------------
# get_my_profile
# ---------------------------------------------------------------------------
class TestGetMyProfile:
    def test_returns_current_user(self):
        user = _make_user(id=5)
        result = get_my_profile(user)
        assert result is user


# ---------------------------------------------------------------------------
# get_user_public_profile_by_id
# ---------------------------------------------------------------------------
class TestGetUserPublicProfileById:
    def test_returns_user_when_found_and_not_blocked(self):
        user = _make_user(id=1, blocked=False)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ):
            result = get_user_public_profile_by_id(1, db)
        assert result is user

    def test_raises_404_when_user_not_found(self):
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=None
        ):
            with pytest.raises(ServiceException) as exc_info:
                get_user_public_profile_by_id(999, db)
        assert exc_info.value.status_code == 404

    def test_raises_403_when_user_blocked(self):
        user = _make_user(id=1, blocked=True)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ):
            with pytest.raises(ServiceException) as exc_info:
                get_user_public_profile_by_id(1, db)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# get_user_public_profile_by_username
# ---------------------------------------------------------------------------
class TestGetUserPublicProfileByUsername:
    def test_returns_user_when_found_and_not_blocked(self):
        user = _make_user(username="alice", blocked=False)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_username",
            return_value=user,
        ):
            result = get_user_public_profile_by_username("alice", db)
        assert result is user

    def test_raises_404_when_not_found(self):
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_username",
            return_value=None,
        ):
            with pytest.raises(ServiceException) as exc_info:
                get_user_public_profile_by_username("ghost", db)
        assert exc_info.value.status_code == 404

    def test_raises_403_when_blocked(self):
        user = _make_user(username="blockeduser", blocked=True)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_username",
            return_value=user,
        ):
            with pytest.raises(ServiceException) as exc_info:
                get_user_public_profile_by_username("blockeduser", db)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# update_my_profile
# ---------------------------------------------------------------------------
class TestUpdateMyProfile:
    def test_updates_profile_successfully(self):
        user = _make_user()
        db = MagicMock()

        with patch("app.services.users.users_repository.save_user") as mock_save:
            from app.schemas.schemas import UserUpdate

            payload = UserUpdate(first_name="NewName")
            result = update_my_profile(payload, db, user)
            mock_save.assert_called_once()
        assert result.first_name == "NewName"

    def test_raises_500_on_db_error(self):
        user = _make_user()
        db = MagicMock()

        with patch(
            "app.services.users.users_repository.save_user",
            side_effect=Exception("DB error"),
        ):
            from app.schemas.schemas import UserUpdate

            payload = UserUpdate(first_name="NewName")
            with pytest.raises(ServiceException) as exc_info:
                update_my_profile(payload, db, user)
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# block_user
# ---------------------------------------------------------------------------
class TestBlockUser:
    def test_raises_400_when_blocking_own_account(self):
        admin = _make_user(id=1, role="admin")
        db = MagicMock()
        with pytest.raises(ServiceException) as exc_info:
            block_user(db, user_id=1, admin_user=admin)
        assert exc_info.value.status_code == 400

    def test_raises_404_when_user_not_found(self):
        admin = _make_user(id=99, role="admin")
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=None
        ):
            with pytest.raises(ServiceException) as exc_info:
                block_user(db, user_id=1, admin_user=admin)
        assert exc_info.value.status_code == 404

    def test_returns_already_blocked_message(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=True)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ):
            result = block_user(db, user_id=1, admin_user=admin)
        assert "already blocked" in result["message"].lower()

    def test_blocks_user_successfully(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=False)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ), patch("app.services.users.users_repository.save_user"), patch(
            "app.services.users._notify_product_service_block"
        ):
            result = block_user(db, user_id=1, admin_user=admin)
        assert "blocked successfully" in result["message"].lower()
        assert user.blocked is True

    def test_reverts_block_when_product_service_fails(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=False)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ), patch("app.services.users.users_repository.save_user"), patch(
            "app.services.users._notify_product_service_block",
            side_effect=Exception("connection error"),
        ):
            with pytest.raises(ServiceException) as exc_info:
                block_user(db, user_id=1, admin_user=admin)
        assert exc_info.value.status_code == 502
        # User should be unblocked after failure
        assert user.blocked is False

    def test_raises_500_when_save_fails(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=False)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ), patch(
            "app.services.users.users_repository.save_user",
            side_effect=Exception("DB error"),
        ):
            with pytest.raises(ServiceException) as exc_info:
                block_user(db, user_id=1, admin_user=admin)
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# unblock_user
# ---------------------------------------------------------------------------
class TestUnblockUser:
    def test_raises_404_when_user_not_found(self):
        admin = _make_user(id=99, role="admin")
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=None
        ):
            with pytest.raises(ServiceException) as exc_info:
                unblock_user(db, user_id=1, admin_user=admin)
        assert exc_info.value.status_code == 404

    def test_returns_not_blocked_message(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=False)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ):
            result = unblock_user(db, user_id=1, admin_user=admin)
        assert "not blocked" in result["message"].lower()

    def test_unblocks_user_successfully(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=True)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ), patch("app.services.users.users_repository.save_user"), patch(
            "app.services.users._notify_product_service_unblock"
        ):
            result = unblock_user(db, user_id=1, admin_user=admin)
        assert "unblocked successfully" in result["message"].lower()
        assert user.blocked is False

    def test_reverts_unblock_when_product_service_fails(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=True)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ), patch("app.services.users.users_repository.save_user"), patch(
            "app.services.users._notify_product_service_unblock",
            side_effect=Exception("error"),
        ):
            with pytest.raises(ServiceException) as exc_info:
                unblock_user(db, user_id=1, admin_user=admin)
        assert exc_info.value.status_code == 502
        assert user.blocked is True

    def test_raises_500_when_save_fails(self):
        admin = _make_user(id=99, role="admin")
        user = _make_user(id=1, blocked=True)
        db = MagicMock()
        with patch(
            "app.services.users.users_repository.get_user_by_id", return_value=user
        ), patch(
            "app.services.users.users_repository.save_user",
            side_effect=Exception("DB error"),
        ):
            with pytest.raises(ServiceException) as exc_info:
                unblock_user(db, user_id=1, admin_user=admin)
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# list_users_admin
# ---------------------------------------------------------------------------
class TestListUsersAdmin:
    def test_returns_paginated_user_list(self):
        user1 = _make_user(id=1, first_name="Alice", last_name="Smith", blocked=False)
        user2 = _make_user(id=2, first_name="Bob", last_name="Jones", blocked=True)
        db = MagicMock()
        with patch(
            "app.services.users.get_users_paginated", return_value=([user1, user2], 2)
        ):
            result = list_users_admin(db, page=1, limit=10)
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["data"]) == 2

    def test_blocked_user_has_status_bloqueado(self):
        user = _make_user(
            id=1, first_name="", last_name="", username="blocky", blocked=True
        )
        db = MagicMock()
        with patch("app.services.users.get_users_paginated", return_value=([user], 1)):
            result = list_users_admin(db, page=1, limit=10)
        assert result["data"][0]["status"] == "blocked"

    def test_active_user_has_status_activo(self):
        user = _make_user(id=1, first_name="Ana", last_name="Garcia", blocked=False)
        db = MagicMock()
        with patch("app.services.users.get_users_paginated", return_value=([user], 1)):
            result = list_users_admin(db, page=1, limit=10)
        assert result["data"][0]["status"] == "active"

    def test_empty_name_fallback_to_username(self):
        user = _make_user(
            id=1, first_name=None, last_name=None, username="johndoe", blocked=False
        )
        user.first_name = None
        user.last_name = None
        db = MagicMock()
        with patch("app.services.users.get_users_paginated", return_value=([user], 1)):
            result = list_users_admin(db, page=1, limit=10)
        assert result["data"][0]["name"] == "johndoe"


# ---------------------------------------------------------------------------
# get_user_metrics
# ---------------------------------------------------------------------------
class TestGetUserMetrics:
    def test_returns_metrics(self):
        from datetime import date

        db = MagicMock()
        timeline_data = [(date(2024, 1, 1), 5), (date(2024, 1, 2), 3)]
        with patch("app.services.users.count_total_users", return_value=100), patch(
            "app.services.users.get_users_timeline", return_value=timeline_data
        ):
            result = get_user_metrics(db, date(2024, 1, 1), date(2024, 1, 31))

        assert result["totalUsers"] == 100
        assert result["usersInPeriod"] == 8
        assert len(result["timeline"]) == 2

    def test_raises_500_on_exception(self):
        from datetime import date

        db = MagicMock()
        with patch(
            "app.services.users.count_total_users", side_effect=Exception("DB error")
        ):
            with pytest.raises(ServiceException) as exc_info:
                get_user_metrics(db, date(2024, 1, 1), date(2024, 1, 31))
        assert exc_info.value.status_code == 500
