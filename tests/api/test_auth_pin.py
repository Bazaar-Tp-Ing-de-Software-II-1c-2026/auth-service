from app.security import create_access_token


class TestPinAuthEndpoints:
    def test_register_pin_success(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/auth/pin/register",
            headers=headers,
            json={
                "device_id": "device-123",
                "pin": "123456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pin_enabled"] is True
        assert data["device_id"] == "device-123"

    def test_register_pin_requires_auth(self, client):
        response = client.post(
            "/api/auth/pin/register",
            json={"device_id": "device-123", "pin": "123456"},
        )

        assert response.status_code == 401
        assert "Missing token" in response.json()["detail"]

    def test_register_pin_validates_numeric_pin(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/auth/pin/register",
            headers=headers,
            json={"device_id": "device-123", "pin": "12ab56"},
        )

        assert response.status_code == 400
        assert "PIN must contain digits only" in response.json()["detail"]

    def test_login_with_pin_success(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        register_resp = client.post(
            "/api/auth/pin/register",
            headers=headers,
            json={"device_id": "device-abc", "pin": "654321"},
        )
        assert register_resp.status_code == 200

        response = client.post(
            "/api/auth/pin/login",
            json={"device_id": "device-abc", "pin": "654321"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_with_pin_locks_after_retries(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        register_resp = client.post(
            "/api/auth/pin/register",
            headers=headers,
            json={"device_id": "device-lock", "pin": "999999"},
        )
        assert register_resp.status_code == 200

        # 4 intentos inválidos -> 401
        for _ in range(4):
            wrong = client.post(
                "/api/auth/pin/login",
                json={"device_id": "device-lock", "pin": "000000"},
            )
            assert wrong.status_code == 401

        # 5to intento inválido -> 423 lock
        locked = client.post(
            "/api/auth/pin/login",
            json={"device_id": "device-lock", "pin": "000000"},
        )
        assert locked.status_code == 423
        assert "temporarily blocked" in locked.json()["detail"]

    def test_pin_status_success(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        register_resp = client.post(
            "/api/auth/pin/register",
            headers=headers,
            json={"device_id": "device-status", "pin": "123456"},
        )
        assert register_resp.status_code == 200

        response = client.get("/api/auth/pin/status?device_id=device-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "device-status"
        assert data["pin_enabled"] is True
        assert data["locked"] is False

    def test_disable_pin_success(self, client, test_user):
        token = create_access_token({"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        register_resp = client.post(
            "/api/auth/pin/register",
            headers=headers,
            json={"device_id": "device-disable", "pin": "123456"},
        )
        assert register_resp.status_code == 200

        disable_resp = client.post(
            "/api/auth/pin/disable",
            headers=headers,
            json={"device_id": "device-disable"},
        )
        assert disable_resp.status_code == 200
        assert disable_resp.json()["pin_enabled"] is False

        login_resp = client.post(
            "/api/auth/pin/login",
            json={"device_id": "device-disable", "pin": "123456"},
        )
        assert login_resp.status_code == 404
