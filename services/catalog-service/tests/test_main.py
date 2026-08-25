import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

test_database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not test_database_url:
    pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required", allow_module_level=True)
os.environ["DATABASE_URL"] = test_database_url

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Product  # noqa: E402


SAMPLE_PRODUCTS = [
    {"id": 1, "sku": "RICE-BASMATI-25KG", "name": "Basmati Rice", "category": "Grains", "price_npr": 4250, "unit": "25 kg bag"},
    {"id": 2, "sku": "OIL-SUNFLOWER-15L", "name": "Sunflower Cooking Oil", "category": "Cooking Oils", "price_npr": 3450, "unit": "15 litre tin"},
    {"id": 3, "sku": "CHICKEN-WHOLE-1KG", "name": "Fresh Whole Chicken", "category": "Meat & Poultry", "price_npr": 480, "unit": "kg"},
    {"id": 4, "sku": "TOMATO-LOCAL-1KG", "name": "Fresh Local Tomatoes", "category": "Fresh Produce", "price_npr": 110, "unit": "kg"},
    {"id": 5, "sku": "CLEAN-DISHWASH-5L", "name": "Commercial Dishwashing Liquid", "category": "Cleaning Supplies", "price_npr": 950, "unit": "5 litre container"},
]


@pytest.fixture(scope="session", autouse=True)
def migrate_database() -> None:
    service_dir = Path(__file__).resolve().parents[1]
    config = Config(service_dir / "alembic.ini")
    command.upgrade(config, "head")


@pytest.fixture()
def db_session(migrate_database: None) -> Generator[Session, None, None]:
    test_engine = create_engine(test_database_url)
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        session.execute(delete(Product))
        session.commit()
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        test_engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_products(db_session: Session) -> None:
    db_session.add_all(Product(**product) for product in SAMPLE_PRODUCTS)
    db_session.commit()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ready(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_list_products_contains_samples(client: TestClient, sample_products: None) -> None:
    response = client.get("/products")
    assert response.status_code == 200
    assert len(response.json()) == 5
    assert response.json()[0]["sku"] == "RICE-BASMATI-25KG"


def test_get_product(client: TestClient, sample_products: None) -> None:
    response = client.get("/products/3")
    assert response.status_code == 200
    assert response.json()["name"] == "Fresh Whole Chicken"


def test_get_missing_product_returns_404(client: TestClient) -> None:
    response = client.get("/products/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_create_product(client: TestClient) -> None:
    new_product = {
        "id": 6,
        "sku": "FLOUR-WHEAT-10KG",
        "name": "Whole Wheat Flour",
        "category": "Grains",
        "price_npr": 980,
        "unit": "10 kg bag",
    }
    response = client.post("/products", json=new_product)
    assert response.status_code == 201
    assert response.json() == new_product
    assert client.get("/products/6").json() == new_product


def test_duplicate_product_id_returns_conflict(client: TestClient, sample_products: None) -> None:
    response = client.post("/products", json=SAMPLE_PRODUCTS[0])
    assert response.status_code == 409
    assert response.json() == {"detail": "Product ID already exists"}


def test_duplicate_sku_returns_conflict(client: TestClient, sample_products: None) -> None:
    duplicate = {**SAMPLE_PRODUCTS[0], "id": 6}
    response = client.post("/products", json=duplicate)
    assert response.status_code == 409
    assert response.json() == {"detail": "Product SKU already exists"}


def test_invalid_product_returns_validation_error(client: TestClient) -> None:
    response = client.post(
        "/products",
        json={"id": 6, "sku": "BAD", "name": "Bad", "category": "Other", "price_npr": -1, "unit": "item"},
    )
    assert response.status_code == 422
