import httpx
from fastapi.testclient import TestClient

from app.main import app


def upstream(request: httpx.Request) -> httpx.Response:
    data = {
        "/accounts": [{"restaurant_id": 1, "restaurant_name": "Everest Kitchen", "available_credit_npr": 5000, "reserved_credit_npr": 0}],
        "/products": [{"id": 10, "sku": "RICE-01", "name": "Basmati Rice", "price_npr": 250}],
        "/inventory": [{"product_id": 10, "quantity_available": 12, "quantity_reserved": 0}],
        "/orders": [],
    }
    if request.method == "POST" and request.url.path == "/orders":
        return httpx.Response(201, json={"id": 7, "restaurant_id": 1, "items": [{"product_id": 10, "quantity": 2, "unit_price_npr": 250}], "status": "CONFIRMED", "total_npr": 500, "created_at": "2026-01-01T00:00:00"})
    return httpx.Response(200, json=data[request.url.path])


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_page_and_confirmed_order():
    with TestClient(app) as client:
        original = client.app.state.http
        client.app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        response = client.get("/")
        assert response.status_code == 200
        assert "Everest Kitchen" in response.text
        assert "Basmati Rice" in response.text

        response = client.post("/orders", data={"restaurant_id": "1", "quantity_10": "2"})
        assert response.status_code == 200
        assert "Order #7 confirmed" in response.text
        client.app.state.http = original


def test_empty_order_is_rejected_in_ui():
    with TestClient(app) as client:
        original = client.app.state.http
        client.app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        response = client.post("/orders", data={"restaurant_id": "1", "quantity_10": "0"})
        assert response.status_code == 200
        assert "Choose at least one product quantity" in response.text
        client.app.state.http = original
