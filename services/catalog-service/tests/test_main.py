import pytest
from fastapi.testclient import TestClient

from app.main import SAMPLE_PRODUCTS, app, products


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_products() -> None:
    products.clear()
    products.update({product.id: product for product in SAMPLE_PRODUCTS})


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_products_contains_samples() -> None:
    response = client.get("/products")
    assert response.status_code == 200
    assert len(response.json()) == 5
    assert response.json()[0]["sku"] == "RICE-BASMATI-25KG"


def test_get_product() -> None:
    response = client.get("/products/3")
    assert response.status_code == 200
    assert response.json()["name"] == "Fresh Whole Chicken"


def test_get_missing_product_returns_404() -> None:
    response = client.get("/products/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_create_product() -> None:
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


def test_duplicate_product_id_returns_conflict() -> None:
    response = client.post("/products", json=SAMPLE_PRODUCTS[0].model_dump())
    assert response.status_code == 409
    assert response.json() == {"detail": "Product ID already exists"}


def test_invalid_product_returns_validation_error() -> None:
    response = client.post(
        "/products",
        json={"id": 6, "sku": "BAD", "name": "Bad", "category": "Other", "price_npr": -1, "unit": "item"},
    )
    assert response.status_code == 422
