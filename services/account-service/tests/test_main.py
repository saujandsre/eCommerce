import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
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
from app.models import RestaurantAccount  # noqa: E402

@pytest.fixture(scope="session", autouse=True)
def migrate():
    command.upgrade(Config(Path(__file__).resolve().parents[1] / "alembic.ini"), "head")

@pytest.fixture(autouse=True)
def data(migrate):
    with SessionLocal.begin() as db:
        db.execute(delete(RestaurantAccount))
        db.add_all([RestaurantAccount(restaurant_id=1, restaurant_name="Himalayan Kitchen", credit_limit_npr=Decimal("500000.00"), available_credit_npr=Decimal("450000.00"), reserved_credit_npr=Decimal("50000.00")), RestaurantAccount(restaurant_id=2, restaurant_name="Kathmandu Bistro", credit_limit_npr=Decimal("300000.00"), available_credit_npr=Decimal("300000.00"), reserved_credit_npr=Decimal("0"))])
    yield
    with SessionLocal.begin() as db:
        db.execute(delete(RestaurantAccount))

@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value

def test_health_ready_list_get(client):
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/ready").status_code == 200
    assert len(client.get("/accounts").json()) == 2
    assert client.get("/accounts/1").json()["restaurant_name"] == "Himalayan Kitchen"
    assert client.get("/accounts/999").status_code == 404

def test_decimal_reserve_release_and_persistence(client):
    result = client.post("/accounts/2/reserve-credit", json={"amount_npr": 10000.15}).json()
    assert result["available_credit_npr"] == 289999.85
    with SessionLocal() as db:
        assert db.get(RestaurantAccount, 2).reserved_credit_npr == Decimal("10000.15")
    result = client.post("/accounts/2/release-credit", json={"amount_npr": 0.15}).json()
    assert result["reserved_credit_npr"] == 10000.0

def test_validation_conflicts(client):
    assert client.post("/accounts/1/reserve-credit", json={"amount_npr": 0}).status_code == 422
    assert client.post("/accounts/1/reserve-credit", json={"amount_npr": 450001}).json() == {"detail": "Insufficient available credit"}
    assert client.post("/accounts/1/release-credit", json={"amount_npr": 50001}).json() == {"detail": "Cannot release more than reserved credit"}

def test_concurrent_credit_reservations_cannot_overspend():
    def reserve():
        with TestClient(app) as client:
            return client.post("/accounts/2/reserve-credit", json={"amount_npr": 200000}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: reserve(), range(2)))
    assert sorted(statuses) == [200, 409]
