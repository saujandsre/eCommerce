import pytest
from fastapi.testclient import TestClient

from app.main import SAMPLE_INVENTORY, app, inventory


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_inventory() -> None:
    inventory.clear()
    inventory.update({item.product_id: item.model_copy() for item in SAMPLE_INVENTORY})


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_inventory() -> None:
    response = client.get("/inventory")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_get_inventory() -> None:
    response = client.get("/inventory/1")
    assert response.status_code == 200
    assert response.json()["sku"] == "RICE-BASMATI-25KG"


def test_missing_inventory_returns_404() -> None:
    response = client.get("/inventory/999")
    assert response.status_code == 404


def test_reserve_inventory() -> None:
    response = client.post("/inventory/1/reserve", json={"quantity": 5})
    assert response.status_code == 200
    assert response.json()["quantity_available"] == 115
    assert response.json()["quantity_reserved"] == 5


def test_reserve_requires_positive_quantity() -> None:
    response = client.post("/inventory/1/reserve", json={"quantity": 0})
    assert response.status_code == 422


def test_reserve_missing_inventory_returns_404() -> None:
    response = client.post("/inventory/999/reserve", json={"quantity": 1})
    assert response.status_code == 404


def test_insufficient_inventory_returns_conflict() -> None:
    response = client.post("/inventory/1/reserve", json={"quantity": 121})
    assert response.status_code == 409
    assert response.json() == {"detail": "Insufficient inventory"}


def test_release_inventory() -> None:
    response = client.post("/inventory/2/release", json={"quantity": 3})
    assert response.status_code == 200
    assert response.json()["quantity_available"] == 78
    assert response.json()["quantity_reserved"] == 2


def test_excessive_release_returns_conflict() -> None:
    response = client.post("/inventory/2/release", json={"quantity": 6})
    assert response.status_code == 409
    assert response.json() == {"detail": "Cannot release more than reserved inventory"}
