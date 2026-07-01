from app.security import create_access_token
from app.models import User
from unittest.mock import patch
from app.services import users as users_service

class TestAdminBlockUnblock:
    def test_admin_can_block_user(self, client, db, test_user, test_admin, monkeypatch):
        monkeypatch.setattr(users_service, "_notify_product_service_block", lambda user_id: None)

        token = create_access_token({"sub": str(test_admin.id)})
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.services.users._notify_product_service_block"):
            response = client.post(
                f"/api/users/{test_user.id}/block",
                headers=headers,
            )

        assert response.status_code == 200
        assert "blocked" in response.json()["message"].lower()

        user = db.get(User, test_user.id)
        assert user.blocked is True

    def test_admin_cannot_block_self(self, client, test_admin):
        token = create_access_token({"sub": str(test_admin.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"/api/users/{test_admin.id}/block", headers=headers)

        assert response.status_code == 400
        assert "cannot" in response.json()["detail"].lower()

    def test_admin_can_unblock_user(self, client, db, test_user, test_admin, monkeypatch):
        # pre-block the user
        test_user.blocked = True
        db.add(test_user)
        db.commit()

        monkeypatch.setattr(users_service, "_notify_product_service_unblock", lambda user_id: None)

        token = create_access_token({"sub": str(test_admin.id)})
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.services.users._notify_product_service_unblock"):
            response = client.post(
                f"/api/users/{test_user.id}/unblock",
                headers=headers,
            )

        assert response.status_code == 200
        assert "unblocked" in response.json()["message"].lower()

        user = db.get(User, test_user.id)
        assert user.blocked is False

    def test_blocked_user_cannot_login(self, client, db, test_user):
        # block the user
        test_user.blocked = True
        db.add(test_user)
        db.commit()

        payload = {"identifier": test_user.email, "password": "password123"}
        response = client.post("/api/auth/login", json=payload)

        assert response.status_code == 403
        assert "blocked" in response.json()["detail"].lower()
