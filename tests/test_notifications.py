from datetime import datetime, timezone

from app.models import Notification


def test_create_notification_endpoint_persists_notification(client, db, test_user):
    payload = {
        "user_id": test_user.id,
        "notification_type": "low_stock",
        "title": "Alerta de stock bajo",
        "body": "Producto con pocas unidades.",
        "data": {
            "product_id": "abc123",
            "current_stock": "3",
        },
        "source": "product-service",
    }

    response = client.post("/api/notifications", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == test_user.id
    assert body["notification_type"] == "low_stock"
    assert body["is_read"] is False
    assert body["source"] == "product-service"

    saved = db.query(Notification).filter(Notification.user_id == test_user.id).first()
    assert saved is not None
    assert saved.title == payload["title"]


def test_get_my_notifications_returns_user_notifications(client, db, test_user):
    db.add(
        Notification(
            user_id=test_user.id,
            notification_type="out_of_stock",
            title="Producto sin stock",
            body="Se agotó un producto.",
            data={"product_id": "abc123"},
            source="product-service",
            is_read=True,
            read_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    from app.api.dependencies import get_current_user
    from main import app

    def override_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_current_user
    response = client.get("/api/notifications/me")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["data"][0]["notification_type"] == "out_of_stock"
