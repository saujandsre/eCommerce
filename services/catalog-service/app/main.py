from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


class Product(BaseModel):
    id: Annotated[int, Field(gt=0)]
    sku: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    category: Annotated[str, Field(min_length=1)]
    price_npr: Annotated[float, Field(gt=0)]
    unit: Annotated[str, Field(min_length=1)]


SAMPLE_PRODUCTS = [
    Product(id=1, sku="RICE-BASMATI-25KG", name="Basmati Rice", category="Grains", price_npr=4250, unit="25 kg bag"),
    Product(id=2, sku="OIL-SUNFLOWER-15L", name="Sunflower Cooking Oil", category="Cooking Oils", price_npr=3450, unit="15 litre tin"),
    Product(id=3, sku="CHICKEN-WHOLE-1KG", name="Fresh Whole Chicken", category="Meat & Poultry", price_npr=480, unit="kg"),
    Product(id=4, sku="TOMATO-LOCAL-1KG", name="Fresh Local Tomatoes", category="Fresh Produce", price_npr=110, unit="kg"),
    Product(id=5, sku="CLEAN-DISHWASH-5L", name="Commercial Dishwashing Liquid", category="Cleaning Supplies", price_npr=950, unit="5 litre container"),
]

products: dict[int, Product] = {product.id: product for product in SAMPLE_PRODUCTS}

app = FastAPI(title="Catalog Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/products", response_model=list[Product])
def list_products() -> list[Product]:
    return list(products.values())


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int) -> Product:
    product = products.get(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@app.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(product: Product) -> Product:
    if product.id in products:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product ID already exists")
    products[product.id] = product
    return product
