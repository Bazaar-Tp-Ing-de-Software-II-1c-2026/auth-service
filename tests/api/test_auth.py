import pytest
from app.security import create_access_token


class TestRegisterEndpoint:
    def test_register_success(self, client, valid_user_data):
        response = client.post("/api/auth/register", json=valid_user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == valid_user_data["email"]
        assert data["username"] == valid_user_data["username"]
        assert data["first_name"] == valid_user_data["first_name"]
        assert data["last_name"] == valid_user_data["last_name"]
        assert "id" in data

    def test_register_duplicate_email(self, client, test_user, valid_user_data):
        valid_user_data["email"] = test_user.email
        response = client.post("/api/auth/register", json=valid_user_data)
        assert response.status_code == 400
        assert "correo electrónico ya está registrado" in response.json()["detail"]

    def test_register_duplicate_username(self, client, test_user, valid_user_data):
        valid_user_data["username"] = test_user.username
        response = client.post("/api/auth/register", json=valid_user_data)
        assert response.status_code == 400
        assert "nombre de usuario ya existe" in response.json()["detail"]

    def test_register_invalid_email(self, client, valid_user_data):
        valid_user_data["email"] = "not-an-email"
        response = client.post("/api/auth/register", json=valid_user_data)
        assert response.status_code == 422

    def test_register_missing_field(self, client):
        invalid_data = {
            "email": "test@example.com",
            "username": "testuser"
        }
        response = client.post("/api/auth/register", json=invalid_data)
        assert response.status_code == 422

    def test_register_user_created_in_database(self, client, db, valid_user_data):
        response = client.post("/api/auth/register", json=valid_user_data)
        assert response.status_code == 200
        
        from app.models import User
        user = db.query(User).filter(User.email == valid_user_data["email"]).first()
        assert user is not None
        assert user.username == valid_user_data["username"]


class TestLoginEndpoint:
    def test_login_with_email_success(self, client, test_user):
        response = client.post(
            "/api/auth/login",
            json={"identifier": test_user.email, "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_username_success(self, client, test_user):
        response = client.post(
            "/api/auth/login",
            json={"identifier": test_user.username, "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        response = client.post(
            "/api/auth/login",
            json={"identifier": test_user.email, "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "User or password incorrect" in response.json()["detail"]

    def test_login_user_not_found(self, client):
        response = client.post(
            "/api/auth/login",
            json={"identifier": "nonexistent@example.com", "password": "password123"}
        )
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_login_user_blocked(self, client, db, test_user):
        test_user.blocked = True
        db.commit()
        
        response = client.post(
            "/api/auth/login",
            json={"identifier": test_user.email, "password": "password123"}
        )
        assert response.status_code == 403
        assert "account has been blocked" in response.json()["detail"]

    def test_login_missing_identifier(self, client):
        response = client.post(
            "/api/auth/login",
            json={"password": "password123"}
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client):
        response = client.post(
            "/api/auth/login",
            json={"identifier": "test@example.com"}
        )
        assert response.status_code == 422


class TestGetCurrentUserDependency:
    def test_get_current_user_valid_token(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/", headers=headers)
        assert response.status_code == 200

    def test_get_current_user_missing_token(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_get_current_user_invalid_token(self, client):
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/", headers=headers)
        assert response.status_code == 200

    def test_get_current_user_malformed_header(self, client):
        headers = {"Authorization": "NotBearer token"}
        response = client.get("/", headers=headers)
        assert response.status_code == 200


class TestHomeEndpoint:
    def test_home_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Bazaar Auth Service" in data["message"]


class TestStatusEndpoint:
    def test_status_endpoint(self, client):
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
