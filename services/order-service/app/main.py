from datetime import datetime, timezone
from enum import Enum
import os
from threading import Lock
from typing import Annotated

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:8001").rstrip("/")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8002").rstrip("/")
ACCOUNT_SERVICE_URL = os.getenv("ACCOUNT_SERVICE_URL", "http://localhost:8003").rstrip("/")
DOWNSTREAM_TIMEOUT_SECONDS = 5.0


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderItem(BaseModel):
    product_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[int, Field(gt=0)]
    unit_price_npr: Annotated[float, Field(gt=0)]


class CreateOrderItem(BaseModel):
    product_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[int, Field(gt=0)]


class CreateOrderRequest(BaseModel):
    restaurant_id: Annotated[int, Field(gt=0)]
    items: Annotated[list[CreateOrderItem], Field(min_length=1)]


class Order(BaseModel):
    id: int
    restaurant_id: int
    items: list[OrderItem]
    status: OrderStatus
    total_npr: float
    created_at: datetime


orders: dict[int, Order] = {}
next_order_id = 1
order_id_lock = Lock()

app = FastAPI(title="Order Service", version="0.1.0")


def find_order(order_id: int) -> Order:
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/orders", response_model=list[Order])
def list_orders() -> list[Order]:
    return list(orders.values())


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int) -> Order:
    return find_order(order_id)


def call_downstream(client: httpx.Client, method: str, url: str, service_name: str, **kwargs: object) -> httpx.Response:
    try:
        response = client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{service_name} is unavailable") from exc
    if response.is_success:
        return response
    if response.status_code in {status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT}:
        try:
            downstream_detail = response.json().get("detail")
        except (ValueError, AttributeError):
            downstream_detail = None
        raise HTTPException(status_code=response.status_code, detail=downstream_detail or f"{service_name} rejected the request")
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"{service_name} returned an unexpected response")


@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(request: CreateOrderRequest) -> Order:
    global next_order_id
    priced_items: list[OrderItem] = []
    with httpx.Client(timeout=DOWNSTREAM_TIMEOUT_SECONDS) as client:
        for item in request.items:
            response = call_downstream(client, "GET", f"{CATALOG_SERVICE_URL}/products/{item.product_id}", "Catalog service")
            try:
                priced_items.append(OrderItem(product_id=item.product_id, quantity=item.quantity, unit_price_npr=response.json()["price_npr"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Catalog service returned invalid product data") from exc
        for item in request.items:
            call_downstream(client, "POST", f"{INVENTORY_SERVICE_URL}/inventory/{item.product_id}/reserve", "Inventory service", json={"quantity": item.quantity})
        total_npr = sum(item.quantity * item.unit_price_npr for item in priced_items)
        call_downstream(client, "POST", f"{ACCOUNT_SERVICE_URL}/accounts/{request.restaurant_id}/reserve-credit", "Account service", json={"amount_npr": total_npr})

    with order_id_lock:
        order_id = next_order_id
        next_order_id += 1
    order = Order(id=order_id, restaurant_id=request.restaurant_id, items=priced_items, status=OrderStatus.CONFIRMED, total_npr=total_npr, created_at=datetime.now(timezone.utc))
    orders[order.id] = order
    return order


@app.post("/orders/{order_id}/confirm", response_model=Order)
def confirm_order(order_id: int) -> Order:
    order = find_order(order_id)
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending orders can be confirmed")
    order.status = OrderStatus.CONFIRMED
    return order


@app.post("/orders/{order_id}/cancel", response_model=Order)
def cancel_order(order_id: int) -> Order:
    order = find_order(order_id)
    if order.status not in {OrderStatus.PENDING, OrderStatus.CONFIRMED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order cannot be cancelled from its current status")
    order.status = OrderStatus.CANCELLED
    return order
