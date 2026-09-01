import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete

url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not url:
    pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required", allow_module_level=True)
os.environ["DATABASE_URL"] = url
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import InventoryItem  # noqa: E402

@pytest.fixture(scope="session", autouse=True)
def migrate():
    command.upgrade(Config(Path(__file__).resolve().parents[1] / "alembic.ini"), "head")

@pytest.fixture(autouse=True)
def data(migrate):
    with SessionLocal.begin() as db:
        db.execute(delete(InventoryItem))
        db.add_all([InventoryItem(product_id=1, sku="RICE", quantity_available=120, quantity_reserved=0), InventoryItem(product_id=2, sku="OIL", quantity_available=75, quantity_reserved=5)])
    yield
    with SessionLocal.begin() as db:
        db.execute(delete(InventoryItem))

@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value

def test_health_and_ready(client):
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/ready").json() == {"status": "ready"}

def test_list_get_and_missing(client):
    assert len(client.get("/inventory").json()) == 2
    assert client.get("/inventory/1").json()["sku"] == "RICE"
    assert client.get("/inventory/999").status_code == 404

def test_reserve_release_and_persistence(client):
    assert client.post("/inventory/1/reserve", json={"quantity": 5}).json()["quantity_available"] == 115
    with SessionLocal() as separate:
        assert separate.get(InventoryItem, 1).quantity_reserved == 5
    result = client.post("/inventory/1/release", json={"quantity": 3}).json()
    assert (result["quantity_available"], result["quantity_reserved"]) == (118, 2)

def test_validation_and_conflicts(client):
    assert client.post("/inventory/1/reserve", json={"quantity": 0}).status_code == 422
    assert client.post("/inventory/1/reserve", json={"quantity": 121}).json() == {"detail": "Insufficient inventory"}
    assert client.post("/inventory/2/release", json={"quantity": 6}).json() == {"detail": "Cannot release more than reserved inventory"}
    assert client.post("/inventory/999/reserve", json={"quantity": 1}).status_code == 404

def test_concurrent_reservations_cannot_oversell():
    def reserve():
        with TestClient(app) as client:
            return client.post("/inventory/1/reserve", json={"quantity": 80}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: reserve(), range(2)))
    assert sorted(statuses) == [200, 409]
