import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.main import app, orders


client = TestClient(app)
ORDER_REQUEST = {
    "restaurant_id": 1,
    "items": [
        {"product_id": 1, "quantity": 2, "unit_price_npr": 3500},
        {"product_id": 3, "quantity": 1, "unit_price_npr": 5500},
    ],
}


@pytest.fixture(autouse=True)
def reset_orders() -> None:
    orders.clear()
    main.next_order_id = 1


def create_order() -> dict:
    response = client.post("/orders", json=ORDER_REQUEST)
    assert response.status_code == 201
    return response.json()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_orders_start_empty() -> None:
    response = client.get("/orders")
    assert response.status_code == 200
    assert response.json() == []


def test_create_order_calculates_total_and_sets_pending() -> None:
    order = create_order()
    assert order["id"] == 1
    assert order["status"] == "PENDING"
    assert order["total_npr"] == 12500
    assert order["created_at"]


def test_order_ids_increment() -> None:
    first = create_order()
    second = create_order()
    assert (first["id"], second["id"]) == (1, 2)


def test_get_order() -> None:
    created = create_order()
    response = client.get(f"/orders/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_missing_order_returns_404() -> None:
    response = client.get("/orders/999")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "item",
    [
        {"product_id": 1, "quantity": 0, "unit_price_npr": 100},
        {"product_id": 1, "quantity": 1, "unit_price_npr": 0},
    ],
)
def test_order_rejects_non_positive_quantity_or_price(item: dict) -> None:
    response = client.post("/orders", json={"restaurant_id": 1, "items": [item]})
    assert response.status_code == 422


def test_order_requires_at_least_one_item() -> None:
    response = client.post("/orders", json={"restaurant_id": 1, "items": []})
    assert response.status_code == 422


def test_confirm_pending_order() -> None:
    order = create_order()
    response = client.post(f"/orders/{order['id']}/confirm")
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_confirming_confirmed_order_returns_conflict() -> None:
    order = create_order()
    client.post(f"/orders/{order['id']}/confirm")
    response = client.post(f"/orders/{order['id']}/confirm")
    assert response.status_code == 409


def test_cancel_pending_order() -> None:
    order = create_order()
    response = client.post(f"/orders/{order['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_cancelling_cancelled_order_returns_conflict() -> None:
    order = create_order()
    client.post(f"/orders/{order['id']}/cancel")
    response = client.post(f"/orders/{order['id']}/cancel")
    assert response.status_code == 409


def test_mutating_missing_order_returns_404() -> None:
    assert client.post("/orders/999/confirm").status_code == 404
    assert client.post("/orders/999/cancel").status_code == 404
