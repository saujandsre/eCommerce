from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    product_id: Annotated[int, Field(gt=0)]
    sku: Annotated[str, Field(min_length=1)]
    quantity_available: Annotated[int, Field(ge=0)]
    quantity_reserved: Annotated[int, Field(ge=0)]


class QuantityRequest(BaseModel):
    quantity: Annotated[int, Field(gt=0)]


SAMPLE_INVENTORY = [
    InventoryItem(product_id=1, sku="RICE-BASMATI-25KG", quantity_available=120, quantity_reserved=0),
    InventoryItem(product_id=2, sku="OIL-SUNFLOWER-15L", quantity_available=75, quantity_reserved=5),
    InventoryItem(product_id=3, sku="CHICKEN-WHOLE-1KG", quantity_available=250, quantity_reserved=20),
    InventoryItem(product_id=4, sku="TOMATO-LOCAL-1KG", quantity_available=400, quantity_reserved=30),
    InventoryItem(product_id=5, sku="CLEAN-DISHWASH-5L", quantity_available=60, quantity_reserved=0),
]

inventory: dict[int, InventoryItem] = {item.product_id: item.model_copy() for item in SAMPLE_INVENTORY}

app = FastAPI(title="Inventory Service", version="0.1.0")


def find_inventory(product_id: int) -> InventoryItem:
    item = inventory.get(product_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return item


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/inventory", response_model=list[InventoryItem])
def list_inventory() -> list[InventoryItem]:
    return list(inventory.values())


@app.get("/inventory/{product_id}", response_model=InventoryItem)
def get_inventory(product_id: int) -> InventoryItem:
    return find_inventory(product_id)


@app.post("/inventory/{product_id}/reserve", response_model=InventoryItem)
def reserve_inventory(product_id: int, request: QuantityRequest) -> InventoryItem:
    item = find_inventory(product_id)
    if request.quantity > item.quantity_available:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient inventory")
    item.quantity_available -= request.quantity
    item.quantity_reserved += request.quantity
    return item


@app.post("/inventory/{product_id}/release", response_model=InventoryItem)
def release_inventory(product_id: int, request: QuantityRequest) -> InventoryItem:
    item = find_inventory(product_id)
    if request.quantity > item.quantity_reserved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot release more than reserved inventory")
    item.quantity_reserved -= request.quantity
    item.quantity_available += request.quantity
    return item
