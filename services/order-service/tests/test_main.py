import os
from pathlib import Path
import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete
os.environ.setdefault("DATABASE_URL", os.getenv("TEST_DATABASE_URL", ""))
if not os.environ["DATABASE_URL"]:
    pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required", allow_module_level=True)
import app.main as main  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Order  # noqa: E402

REAL_CLIENT = httpx.Client
ORDER_REQUEST = {"restaurant_id": 1, "items": [{"product_id": 1, "quantity": 2}, {"product_id": 3, "quantity": 1}]}
PRICES = {1: "4250.00", 3: "480.00"}

@pytest.fixture(scope="session", autouse=True)
def migrate():
    command.upgrade(Config(Path(__file__).resolve().parents[1] / "alembic.ini"), "head")

@pytest.fixture(autouse=True)
def clean(migrate):
    with SessionLocal.begin() as db:
        db.execute(delete(Order))
    yield
    with SessionLocal.begin() as db:
        db.execute(delete(Order))

@pytest.fixture
def requests(monkeypatch):
    seen = []
    def handle(request):
        seen.append(request)
        if request.method == "GET":
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"price_npr": PRICES[product_id]})
        return httpx.Response(200, json={})
    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handle), **kwargs))
    return seen

@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value

def test_health_ready_and_empty(client):
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/ready").json() == {"status": "ready"}
    assert client.get("/orders").json() == []

def test_create_uses_catalog_price_and_persists(client, requests):
    response = client.post("/orders", json=ORDER_REQUEST)
    assert response.status_code == 201
    order = response.json()
    assert order["total_npr"] == 8980.0
    assert [item["unit_price_npr"] for item in order["items"]] == [4250.0, 480.0]
    with SessionLocal() as db:
        persisted = db.get(Order, order["id"])
        assert persisted.total_npr.as_tuple().exponent == -2
        assert len(persisted.items) == 2
    assert client.get(f"/orders/{order['id']}").json() == order

def test_validation_and_missing(client, requests):
    assert client.post("/orders", json={"restaurant_id": 1, "items": []}).status_code == 422
    assert client.get("/orders/999").status_code == 404
    assert client.post("/orders/999/cancel").status_code == 404

def test_cancel_confirmed_order(client, requests):
    order = client.post("/orders", json=ORDER_REQUEST).json()
    assert client.post(f"/orders/{order['id']}/confirm").status_code == 409
    assert client.post(f"/orders/{order['id']}/cancel").json()["status"] == "CANCELLED"
    compensation_paths = [request.url.path for request in requests if "release" in request.url.path]
    assert compensation_paths == ["/inventory/3/release", "/inventory/1/release", "/accounts/1/release-credit"]
    request_count = len(requests)
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 409
    assert len(requests) == request_count

def test_cancel_is_best_effort_when_compensation_fails(client, monkeypatch):
    def handle(request):
        if request.method == "GET":
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"price_npr": PRICES[product_id]})
        if "release" in request.url.path:
            return httpx.Response(500, json={"detail": "failure"})
        return httpx.Response(200, json={})
    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handle), **kwargs))
    order = client.post("/orders", json=ORDER_REQUEST).json()
    response = client.post(f"/orders/{order['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 409

def test_account_failure_releases_all_inventory(client, monkeypatch):
    seen = []
    def handle(request):
        seen.append((request.method, request.url.path))
        if request.method == "GET":
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"price_npr": PRICES[product_id]})
        if "reserve-credit" in request.url.path:
            return httpx.Response(409, json={"detail": "Insufficient available credit"})
        return httpx.Response(200, json={})
    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handle), **kwargs))
    assert client.post("/orders", json=ORDER_REQUEST).status_code == 409
    assert [path for method, path in seen if path.endswith("/release")] == ["/inventory/3/release", "/inventory/1/release"]

def test_second_inventory_failure_compensates_first(client, monkeypatch):
    seen = []
    def handle(request):
        seen.append(request.url.path)
        if request.method == "GET":
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"price_npr": PRICES[product_id]})
        if request.url.path == "/inventory/3/reserve":
            return httpx.Response(409, json={"detail": "Insufficient inventory"})
        return httpx.Response(200, json={})
    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handle), **kwargs))
    assert client.post("/orders", json=ORDER_REQUEST).status_code == 409
    assert "/inventory/1/release" in seen

def test_catalog_unavailable_prevents_reservations(client, monkeypatch):
    def handle(request):
        raise httpx.ConnectError("refused", request=request)
    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handle), **kwargs))
    assert client.post("/orders", json=ORDER_REQUEST).json() == {"detail": "Catalog service is unavailable"}


def metric_values(client):
    from prometheus_client.parser import text_string_to_metric_families
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    return {
        sample.name: sample.value
        for family in text_string_to_metric_families(response.text)
        for sample in family.samples
        if sample.name.startswith("order_creation_") and not sample.labels
    }


def test_metrics_scrapes_and_other_routes_do_not_count(client):
    before = metric_values(client)
    client.get("/health")
    client.get("/orders")
    client.post("/orders/999/confirm")
    assert metric_values(client) == before
    text = client.get("/metrics").text
    assert "# TYPE order_creation_attempts_total counter" in text
    assert "# TYPE order_creation_successes_total counter" in text
    assert "# TYPE order_creation_failures_total counter" in text
    assert "# TYPE order_creation_duration_seconds histogram" in text


@pytest.mark.parametrize("outcome,expected_status", [
    ("success", 201), ("validation", 422), ("catalog", 502),
    ("inventory", 409), ("account", 409), ("database", 503),
    ("unexpected", 500),
])
def test_order_metrics(client, monkeypatch, outcome, expected_status):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session

    events = []
    def clock():
        events.append("clock")
        return 10.0 if len(events) == 1 else 12.5

    def handle(request):
        events.append(request.url.path)
        if outcome == "unexpected":
            raise RuntimeError("unexpected downstream error")
        if request.method == "GET":
            if outcome == "catalog":
                return httpx.Response(500)
            product_id = int(request.url.path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"price_npr": PRICES[product_id]})
        if outcome == "inventory" and request.url.path.endswith("/reserve"):
            return httpx.Response(409)
        if outcome == "account" and request.url.path.endswith("/reserve-credit"):
            return httpx.Response(409)
        return httpx.Response(200, json={})

    original_commit = Session.commit
    def commit(db):
        events.append("commit")
        if outcome == "database":
            raise SQLAlchemyError("commit failed")
        return original_commit(db)

    monkeypatch.setattr(main, "perf_counter", clock)
    monkeypatch.setattr(Session, "commit", commit)
    monkeypatch.setattr(main.httpx, "Client", lambda **kwargs: REAL_CLIENT(transport=httpx.MockTransport(handle), **kwargs))
    before = metric_values(client)
    payload = {"restaurant_id": 1, "items": []} if outcome == "validation" else ORDER_REQUEST
    with TestClient(app, raise_server_exceptions=False) as error_client:
        response = error_client.post("/orders", json=payload)
    assert response.status_code == expected_status
    after = metric_values(client)
    assert after["order_creation_attempts_total"] - before["order_creation_attempts_total"] == 1
    assert after["order_creation_successes_total"] - before["order_creation_successes_total"] == (outcome == "success")
    assert after["order_creation_failures_total"] - before["order_creation_failures_total"] == (outcome != "success")
    assert after["order_creation_duration_seconds_count"] - before["order_creation_duration_seconds_count"] == 1
    assert after["order_creation_duration_seconds_sum"] - before["order_creation_duration_seconds_sum"] == pytest.approx(2.5)
    assert events[0] == events[-1] == "clock"
    assert events.count("clock") == 2
    if outcome == "success":
        assert "commit" in events
        assert response.json()["status"] == "CONFIRMED"
        with SessionLocal() as db:
            assert db.get(Order, response.json()["id"]).status == "CONFIRMED"
    if outcome == "database":
        assert events[-4:-1] == ["/accounts/1/release-credit", "/inventory/3/release", "/inventory/1/release"]
