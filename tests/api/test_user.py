from app.security import create_access_token


class TestUserProfileEndpoints:
    def test_get_my_profile_success(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/users/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    def test_get_my_profile_requires_token(self, client):
        response = client.get("/api/users/me")
        assert response.status_code == 401
        assert "Token faltante" in response.json()["detail"]

    def test_update_my_profile_success(self, client, db, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "first_name": "Nuevo",
            "last_name": "Nombre",
            "description": "Vendedor confiable",
            "profile_picture_url": "https://example.com/avatar.png",
        }

        response = client.patch("/api/users/me", headers=headers, json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Nuevo"
        assert data["last_name"] == "Nombre"
        assert data["description"] == "Vendedor confiable"
        assert data["profile_picture_url"] == "https://example.com/avatar.png"

    def test_update_my_profile_invalid_data(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "first_name": "",
            "description": "x" * 281,
            "profile_picture_url": "not-a-url",
        }

        response = client.patch("/api/users/me", headers=headers, json=payload)

        assert response.status_code == 422

    def test_get_public_profile_success_hides_private_fields(self, client, test_user):
        response = client.get(f"/api/users/{test_user.username}")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert "email" not in data
        assert "role" not in data
        assert "blocked" not in data

    def test_get_public_profile_blocked_user_not_available(self, client, db, test_user):
        test_user.blocked = True
        db.add(test_user)
        db.commit()

        response = client.get(f"/api/users/{test_user.username}")

        assert response.status_code == 403
        assert "no está disponible" in response.json()["detail"]

    def test_get_public_profile_not_found(self, client):
        response = client.get("/api/users/unknown-user")

        assert response.status_code == 404
        assert "Usuario no encontrado" in response.json()["detail"]
