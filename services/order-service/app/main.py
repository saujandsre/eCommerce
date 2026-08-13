from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderItem(BaseModel):
    product_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[int, Field(gt=0)]
    unit_price_npr: Annotated[float, Field(gt=0)]


class CreateOrderRequest(BaseModel):
    restaurant_id: Annotated[int, Field(gt=0)]
    items: Annotated[list[OrderItem], Field(min_length=1)]


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


@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(request: CreateOrderRequest) -> Order:
    global next_order_id
    with order_id_lock:
        order_id = next_order_id
        next_order_id += 1

    order = Order(
        id=order_id,
        restaurant_id=request.restaurant_id,
        items=request.items,
        status=OrderStatus.PENDING,
        total_npr=sum(item.quantity * item.unit_price_npr for item in request.items),
        created_at=datetime.now(timezone.utc),
    )
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
