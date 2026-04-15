import pytest
from unittest.mock import patch
from app.security import create_access_token


class TestRegisterEndpoint:
    def test_register_success(self, client, valid_user_data):
        with patch("app.services.auth_service.send_verification_email") as mock_send_email:
            response = client.post("/api/auth/register", json=valid_user_data)


        assert response.status_code == 201
        data = response.json()
        assert data["email"] == valid_user_data["email"]
        assert data["username"] == valid_user_data["username"]
        assert data["first_name"] == valid_user_data["first_name"]
        assert data["last_name"] == valid_user_data["last_name"]
        assert data["is_verified"] is False
        assert "id" in data
        mock_send_email.assert_called_once()

    def test_register_duplicate_email(self, client, test_user, valid_user_data):
        valid_user_data["email"] = test_user.email
        response = client.post("/api/auth/register", json=valid_user_data)
        assert response.status_code == 400
        assert "correo electrónico ya está registrado" in response.json()["detail"]

    def test_register_invalid_email(self, client, valid_user_data):
        valid_user_data["email"] = "not-an-email"
        response = client.post("/api/auth/register", json=valid_user_data)
        assert response.status_code == 400

    def test_register_missing_field(self, client):
        invalid_data = {
            "email": "test@example.com",
            "username": "testuser"
        }
        response = client.post("/api/auth/register", json=invalid_data)
        assert response.status_code == 400

    def test_register_user_created_in_database(self, client, db, valid_user_data):
        with patch("app.services.auth_service.send_verification_email"):
            response = client.post("/api/auth/register", json=valid_user_data)

        assert response.status_code == 201
        
        from app.models import User
        user = db.query(User).filter(User.email == valid_user_data["email"]).first()
        assert user is not None
        assert user.username == valid_user_data["username"]
        assert user.is_verified is False


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
        assert "Usuario o contraseña incorrectos" in response.json()["detail"]

    def test_login_user_not_found(self, client):
        response = client.post(
            "/api/auth/login",
            json={"identifier": "nonexistent@example.com", "password": "password123"}
        )
        assert response.status_code == 404
        assert "Usuario no encontrado" in response.json()["detail"]

    def test_login_user_blocked(self, client, db, test_user):
        test_user.blocked = True
        db.commit()
        
        response = client.post(
            "/api/auth/login",
            json={"identifier": test_user.email, "password": "password123"}
        )
        assert response.status_code == 403
        assert "Tu cuenta ha sido bloqueada" in response.json()["detail"]

    def test_login_user_not_verified(self, client, db):
        from app.models import User
        from app.security import hash_password

        user = User(
            email="pending@example.com",
            username="pendinguser",
            hashed_password=hash_password("password123"),
            first_name="Pending",
            last_name="User",
            role="user",
            blocked=False,
            is_verified=False,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/auth/login",
            json={"identifier": user.email, "password": "password123"}
        )
        assert response.status_code == 403
        assert "Verificá tu email antes de iniciar sesión" in response.json()["detail"]

    def test_login_missing_identifier(self, client):
        response = client.post(
            "/api/auth/login",
            json={"password": "password123"}
        )
        assert response.status_code == 400

    def test_login_missing_password(self, client):
        response = client.post(
            "/api/auth/login",
            json={"identifier": "test@example.com"}
        )
        assert response.status_code == 400


class TestGetCurrentUserDependency:
    def test_get_current_user_valid_token(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/livez", headers=headers)
        assert response.status_code == 200

    def test_get_current_user_missing_token(self, client):
        response = client.get("/livez")
        assert response.status_code == 200

    def test_get_current_user_invalid_token(self, client):
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/livez", headers=headers)
        assert response.status_code == 200

    def test_get_current_user_malformed_header(self, client):
        headers = {"Authorization": "NotBearer token"}
        response = client.get("/livez", headers=headers)
        assert response.status_code == 200


class TestHomeEndpoint:
    def test_home_endpoint(self, client):
        response = client.get("/livez")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestStatusEndpoint:
    def test_status_endpoint(self, client):
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestVerifyEmailEndpoint:
    def test_verify_email_success(self, client, db):
        from app.models import User
        from app.security import hash_password

        user = User(
            email="verify@example.com",
            username="verifyuser",
            hashed_password=hash_password("password123"),
            first_name="Verify",
            last_name="User",
            role="user",
            blocked=False,
            is_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        token = create_access_token({"sub": str(user_id), "scope": "email-verification"})
        response = client.get(f"/api/auth/verify-email?token={token}")

        assert response.status_code == 200
        assert "Email verificado exitosamente" in response.json()["message"]

        updated_user = db.query(User).filter(User.id == user_id).first()
        assert updated_user is not None
        assert updated_user.is_verified is True

    def test_verify_email_invalid_token(self, client):
        response = client.get("/api/auth/verify-email?token=invalid-token")
        assert response.status_code == 401
        assert "Token de verificación inválido o expirado" in response.json()["detail"]

    def test_verify_email_wrong_scope(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id), "scope": "password-reset"})
        response = client.get(f"/api/auth/verify-email?token={token}")
        assert response.status_code == 401
        assert "Token de verificación inválido o expirado" in response.json()["detail"]

    def test_verify_email_already_verified(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id), "scope": "email-verification"})
        response = client.get(f"/api/auth/verify-email?token={token}")
        assert response.status_code == 200
        assert "El correo ya está verificado" in response.json()["message"]


class TestResendVerificationEmailEndpoint:
    def test_resend_verification_email_unverified_user(self, client, db):
        from app.models import User
        from app.security import hash_password

        user = User(
            email="resend@example.com",
            username="resenduser",
            hashed_password=hash_password("password123"),
            first_name="Resend",
            last_name="User",
            role="user",
            blocked=False,
            is_verified=False,
        )
        db.add(user)
        db.commit()

        with patch("app.services.auth_service.send_verification_email") as mock_send_email:
            response = client.post(
                "/api/auth/resend-verification-email",
                json={"email": user.email},
            )

        assert response.status_code == 200
        assert "Si existe una cuenta con ese email y no está verificada, se envió un nuevo código." in response.json()["message"]
        mock_send_email.assert_called_once()

    def test_resend_verification_email_verified_user(self, client, test_user):
        with patch("app.services.auth_service.send_verification_email") as mock_send_email:
            response = client.post(
                "/api/auth/resend-verification-email",
                json={"email": test_user.email},
            )

        assert response.status_code == 200
        assert "Si existe una cuenta con ese email y no está verificada, se envió un nuevo código." in response.json()["message"]
        mock_send_email.assert_not_called()

    def test_resend_verification_email_user_not_found(self, client):
        with patch("app.services.auth_service.send_verification_email") as mock_send_email:
            response = client.post(
                "/api/auth/resend-verification-email",
                json={"email": "missing@example.com"},
            )

        assert response.status_code == 200
        assert "Si existe una cuenta con ese email y no está verificada, se envió un nuevo código." in response.json()["message"]
        mock_send_email.assert_not_called()

    def test_resend_verification_email_invalid_email(self, client):
        response = client.post(
            "/api/auth/resend-verification-email",
            json={"email": "invalid-email"},
        )
        assert response.status_code == 400
