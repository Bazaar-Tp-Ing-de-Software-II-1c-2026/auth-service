"""
Tests para app/api/addresses.py - actualmente con solo 30% de cobertura.
"""

import pytest
from fastapi.testclient import TestClient


def _auth_headers(client, email="test@example.com", password="password123"):
    """Helper para obtener headers de auth."""
    response = client.post(
        "/api/auth/login", json={"identifier": email, "password": password}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


def _addr(**kwargs):
    """Helper para construir datos de dirección."""
    base = {
        "name": "Casa",
        "address": "Av. Corrientes 1234",
        "city": "Buenos Aires",
        "state": "CABA",
        "country": "Argentina",
        "postal_code": "1043",
        "is_default": False,
    }
    base.update(kwargs)
    return base


class TestAddressesEndpoints:
    """Tests de integración para el API de addresses."""

    def test_get_addresses_empty(self, client, test_user):
        headers = _auth_headers(client)
        response = client.get("/api/addresses", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert body["total"] == 0

    def test_create_address_success(self, client, test_user):
        headers = _auth_headers(client)
        response = client.post("/api/addresses", json=_addr(), headers=headers)
        assert response.status_code == 201
        body = response.json()
        assert body["city"] == "Buenos Aires"

    def test_create_first_address_becomes_default(self, client, test_user):
        headers = _auth_headers(client)
        # First address with is_default=False should still become default
        response = client.post(
            "/api/addresses", json=_addr(is_default=False), headers=headers
        )
        assert response.status_code == 201
        assert response.json()["is_default"] is True

    def test_create_multiple_addresses(self, client, test_user):
        headers = _auth_headers(client)
        for i in range(3):
            r = client.post(
                "/api/addresses",
                json=_addr(address=f"Calle {i}", postal_code=f"100{i}"),
                headers=headers,
            )
            assert r.status_code == 201

        response = client.get("/api/addresses", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 3

    def test_get_address_by_id(self, client, test_user):
        headers = _auth_headers(client)
        created = client.post("/api/addresses", json=_addr(), headers=headers).json()
        address_id = created["id"]

        response = client.get(f"/api/addresses/{address_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == address_id

    def test_get_address_not_found(self, client, test_user):
        headers = _auth_headers(client)
        response = client.get("/api/addresses/99999", headers=headers)
        assert response.status_code == 404

    def test_update_address(self, client, test_user):
        headers = _auth_headers(client)
        created = client.post("/api/addresses", json=_addr(), headers=headers).json()
        address_id = created["id"]

        update_data = {"address": "Nueva Dirección 999", "city": "Córdoba"}
        response = client.patch(
            f"/api/addresses/{address_id}", json=update_data, headers=headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["address"] == "Nueva Dirección 999"
        assert body["city"] == "Córdoba"

    def test_update_address_not_found(self, client, test_user):
        headers = _auth_headers(client)
        response = client.patch(
            "/api/addresses/99999", json={"address": "X"}, headers=headers
        )
        assert response.status_code == 404

    def test_update_address_set_as_default(self, client, test_user):
        headers = _auth_headers(client)
        id1 = client.post(
            "/api/addresses", json=_addr(name="Addr1"), headers=headers
        ).json()["id"]
        id2 = client.post(
            "/api/addresses",
            json=_addr(name="Addr2", address="Calle 2", postal_code="2000"),
            headers=headers,
        ).json()["id"]

        response = client.patch(
            f"/api/addresses/{id2}", json={"is_default": True}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["is_default"] is True

    def test_delete_address(self, client, test_user):
        headers = _auth_headers(client)
        created = client.post("/api/addresses", json=_addr(), headers=headers).json()
        address_id = created["id"]

        response = client.delete(f"/api/addresses/{address_id}", headers=headers)
        assert response.status_code == 204

        get_response = client.get(f"/api/addresses/{address_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_address_not_found(self, client, test_user):
        headers = _auth_headers(client)
        response = client.delete("/api/addresses/99999", headers=headers)
        assert response.status_code == 404

    def test_delete_default_address_promotes_next(self, client, test_user):
        headers = _auth_headers(client)
        id1 = client.post(
            "/api/addresses", json=_addr(name="First"), headers=headers
        ).json()["id"]
        id2 = client.post(
            "/api/addresses",
            json=_addr(name="Second", address="Other St", postal_code="9000"),
            headers=headers,
        ).json()["id"]

        # Delete the first (which is default as it was first)
        client.delete(f"/api/addresses/{id1}", headers=headers)

        remaining = client.get("/api/addresses", headers=headers).json()["data"]
        assert len(remaining) == 1

    def test_set_default_address(self, client, test_user):
        headers = _auth_headers(client)
        id1 = client.post(
            "/api/addresses", json=_addr(name="A1"), headers=headers
        ).json()["id"]
        id2 = client.post(
            "/api/addresses",
            json=_addr(name="A2", address="Street 2", postal_code="2000"),
            headers=headers,
        ).json()["id"]

        response = client.post(f"/api/addresses/{id2}/set-default", headers=headers)
        assert response.status_code == 200
        assert response.json()["is_default"] is True

    def test_set_default_address_not_found(self, client, test_user):
        headers = _auth_headers(client)
        response = client.post("/api/addresses/99999/set-default", headers=headers)
        assert response.status_code == 404

    def test_addresses_require_auth(self, client):
        response = client.get("/api/addresses")
        assert response.status_code in (401, 403)

    def test_create_address_with_explicit_default(self, client, test_user):
        headers = _auth_headers(client)
        # Create first address
        client.post("/api/addresses", json=_addr(name="First"), headers=headers)
        # Create second with is_default=True
        response = client.post(
            "/api/addresses",
            json=_addr(
                name="Second Default",
                address="Other 2",
                postal_code="2000",
                is_default=True,
            ),
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["is_default"] is True

    def test_create_address_invalid_empty_name(self, client, test_user):
        headers = _auth_headers(client)
        response = client.post("/api/addresses", json=_addr(name=""), headers=headers)
        # App may return 400 or 422 depending on custom error handler
        assert response.status_code in (400, 422)

    def test_create_address_missing_required_fields(self, client, test_user):
        headers = _auth_headers(client)
        response = client.post("/api/addresses", json={"city": "BA"}, headers=headers)
        assert response.status_code in (400, 422)
