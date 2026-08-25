import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.main import app, orders


client = TestClient(app)
REAL_HTTPX_CLIENT = httpx.Client
ORDER_REQUEST = {"restaurant_id": 1, "items": [{"product_id": 1, "quantity": 2}, {"product_id": 3, "quantity": 1}]}
PRODUCT_PRICES = {1: 4250, 3: 480}


@pytest.fixture(autouse=True)
def reset_orders() -> None:
    orders.clear()
    main.next_order_id = 1


@pytest.fixture(autouse=True)
def mock_downstream_services(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"id": product_id, "price_npr": PRODUCT_PRICES[product_id]})
        return httpx.Response(200, json={})

    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handle), **kwargs))
    return requests


def create_order() -> dict:
    response = client.post("/orders", json=ORDER_REQUEST)
    assert response.status_code == 201
    return response.json()


def test_health() -> None:
    assert client.get("/health").json() == {"status": "healthy"}


def test_orders_start_empty() -> None:
    assert client.get("/orders").json() == []


def test_create_order_orchestrates_services_and_confirms(mock_downstream_services: list[httpx.Request]) -> None:
    order = create_order()
    assert order["id"] == 1
    assert order["status"] == "CONFIRMED"
    assert order["total_npr"] == 8980
    assert [item["unit_price_npr"] for item in order["items"]] == [4250, 480]
    assert order["created_at"]
    assert [(request.method, request.url.path) for request in mock_downstream_services] == [
        ("GET", "/products/1"), ("GET", "/products/3"),
        ("POST", "/inventory/1/reserve"), ("POST", "/inventory/3/reserve"),
        ("POST", "/accounts/1/reserve-credit"),
    ]
    assert [request.read() for request in mock_downstream_services[2:]] == [
        b'{"quantity":2}', b'{"quantity":1}', b'{"amount_npr":8980.0}'
    ]


def test_order_ids_increment() -> None:
    assert (create_order()["id"], create_order()["id"]) == (1, 2)


def test_get_order() -> None:
    created = create_order()
    assert client.get(f"/orders/{created['id']}").json() == created


def test_missing_order_returns_404() -> None:
    assert client.get("/orders/999").status_code == 404


@pytest.mark.parametrize("item", [{"product_id": 1, "quantity": 0}, {"product_id": 0, "quantity": 1}])
def test_order_rejects_non_positive_item_values(item: dict) -> None:
    assert client.post("/orders", json={"restaurant_id": 1, "items": [item]}).status_code == 422


def test_order_requires_at_least_one_item() -> None:
    assert client.post("/orders", json={"restaurant_id": 1, "items": []}).status_code == 422


def test_confirming_confirmed_order_returns_conflict() -> None:
    order = create_order()
    assert client.post(f"/orders/{order['id']}/confirm").status_code == 409


def test_cancel_confirmed_order() -> None:
    order = create_order()
    response = client.post(f"/orders/{order['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_cancelling_cancelled_order_returns_conflict() -> None:
    order = create_order()
    client.post(f"/orders/{order['id']}/cancel")
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 409


def test_mutating_missing_order_returns_404() -> None:
    assert client.post("/orders/999/confirm").status_code == 404
    assert client.post("/orders/999/cancel").status_code == 404


def install_handler(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs))


def test_catalog_not_found_prevents_reservations(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(404, json={"detail": "Product not found"})
    install_handler(monkeypatch, handle)
    response = client.post("/orders", json=ORDER_REQUEST)
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}
    assert len(requests) == 1
    assert orders == {}


def test_inventory_rejection_prevents_credit_and_order(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = []
    def handle(request):
        requests.append(request)
        if request.method == "GET":
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"price_npr": PRODUCT_PRICES[product_id]})
        return httpx.Response(409, json={"detail": "Insufficient inventory"})
    install_handler(monkeypatch, handle)
    response = client.post("/orders", json=ORDER_REQUEST)
    assert response.status_code == 409
    assert response.json() == {"detail": "Insufficient inventory"}
    assert not any("reserve-credit" in request.url.path for request in requests)
    assert orders == {}


def test_account_rejection_leaves_inventory_reserved_but_creates_no_order(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = []
    def handle(request):
        requests.append(request)
        if request.method == "GET":
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"price_npr": PRODUCT_PRICES[product_id]})
        if "reserve-credit" in request.url.path:
            return httpx.Response(409, json={"detail": "Insufficient available credit"})
        return httpx.Response(200, json={})
    install_handler(monkeypatch, handle)
    response = client.post("/orders", json=ORDER_REQUEST)
    assert response.status_code == 409
    assert response.json() == {"detail": "Insufficient available credit"}
    assert sum("/inventory/" in request.url.path for request in requests) == 2
    assert orders == {}


def test_unavailable_catalog_returns_bad_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    def handle(request):
        raise httpx.ConnectError("connection refused", request=request)
    install_handler(monkeypatch, handle)
    response = client.post("/orders", json=ORDER_REQUEST)
    assert response.status_code == 502
    assert response.json() == {"detail": "Catalog service is unavailable"}
    assert orders == {}
