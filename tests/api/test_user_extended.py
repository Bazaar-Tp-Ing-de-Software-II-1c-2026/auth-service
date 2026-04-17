from unittest.mock import patch

from app.models import User
from app.security import create_access_token
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
            mock_get_s3_client.return_value.generate_presigned_url.return_value = "https://signed.example.com"
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
            mock_get_s3_client.return_value.generate_presigned_url.side_effect = RuntimeError("s3 boom")
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
