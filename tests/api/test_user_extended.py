from unittest.mock import patch

from app.models import User
from app.security import create_access_token, hash_password
from app.services import users as users_service


class TestUserExtraEndpoints:
    def test_get_public_profile_by_username_endpoint(self, client, test_user):
        response = client.get(f"/api/users/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username

    def test_get_public_profile_by_id_success(self, client, test_user):
        response = client.get(f"/api/users/{test_user.id}")
        assert response.status_code in (200, 404)

    def test_get_public_profile_by_id_blocked(self, client, db, test_user):
        test_user.blocked = True
        db.add(test_user)
        db.commit()

        response = client.get(f"/api/users/{test_user.id}")
        assert response.status_code == 403

    def test_generate_upload_url_invalid_content_type(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/users/me/upload-url?content_type=application/pdf",
            headers=headers,
        )
        assert response.status_code == 400

    def test_generate_upload_url_missing_bucket(self, client, test_user, monkeypatch):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        monkeypatch.setattr(users_service.settings, "S3_BUCKET_NAME", "")

        response = client.post(
            "/api/users/me/upload-url?content_type=image/png",
            headers=headers,
        )
        assert response.status_code == 500

    def test_generate_upload_url_success(self, client, test_user, monkeypatch):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        monkeypatch.setattr(users_service.settings, "S3_BUCKET_NAME", "my-bucket")

        with patch("app.services.users.get_s3_client") as mock_get_s3_client:
            mock_get_s3_client.return_value.generate_presigned_url.return_value = (
                "https://signed.example.com"
            )
            response = client.post(
                "/api/users/me/upload-url?content_type=image/jpeg",
                headers=headers,
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["upload_url"] == "https://signed.example.com"
        assert "my-bucket.s3.amazonaws.com" in payload["file_url"]

    def test_generate_upload_url_s3_error(self, client, test_user, monkeypatch):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        monkeypatch.setattr(users_service.settings, "S3_BUCKET_NAME", "my-bucket")

        with patch("app.services.users.get_s3_client") as mock_get_s3_client:
            mock_get_s3_client.return_value.generate_presigned_url.side_effect = (
                RuntimeError("s3 boom")
            )
            response = client.post(
                "/api/users/me/upload-url?content_type=image/jpeg",
                headers=headers,
            )

        assert response.status_code == 500
        assert "Error generating presigned URL" in response.json()["detail"]

    def test_update_profile_ignores_unknown_fields(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.patch(
            "/api/users/me",
            headers=headers,
            json={"username": "otheruser"},
        )

        assert response.status_code == 200
        assert response.json()["username"] == test_user.username

    def test_admin_list_users_paged(self, client, db, test_admin, test_user):
        another_user = User(
            email="another@example.com",
            username="anotheruser",
            hashed_password=hash_password("password123"),
            first_name="Another",
            last_name="Person",
            role="user",
            blocked=False,
            is_verified=True,
        )
        blocked_user = User(
            email="blocked@example.com",
            username="blockeduser",
            hashed_password=hash_password("password123"),
            first_name="Blocked",
            last_name="User",
            role="user",
            blocked=True,
            is_verified=True,
        )
        db.add_all([another_user, blocked_user])
        db.commit()

        token = create_access_token({"sub": str(test_admin.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/users?page=1&limit=2", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["page"] == 1
        assert payload["limit"] == 2
        assert payload["total"] == 4
        assert len(payload["data"]) == 2
        assert {"id", "name", "email", "created_at", "status"}.issubset(
            payload["data"][0].keys()
        )

    def test_admin_list_users_filters_by_name_or_email(
        self, client, db, test_admin, test_user
    ):
        matched_user = User(
            email="maria.garcia@example.com",
            username="mariag",
            hashed_password=hash_password("password123"),
            first_name="Maria",
            last_name="Garcia",
            role="user",
            blocked=False,
            is_verified=True,
        )
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=hash_password("password123"),
            first_name="Otro",
            last_name="Usuario",
            role="user",
            blocked=False,
            is_verified=True,
        )
        db.add_all([matched_user, other_user])
        db.commit()

        token = create_access_token({"sub": str(test_admin.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/users?search=maria", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["data"]) == 1
        assert payload["data"][0]["email"] == "maria.garcia@example.com"

        response = client.get("/api/users?search=other@example.com", headers=headers)

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["data"][0]["email"] == "other@example.com"

    def test_non_admin_cannot_list_users(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/users", headers=headers)

        assert response.status_code == 403
        assert "Admin only" in response.json()["detail"]
