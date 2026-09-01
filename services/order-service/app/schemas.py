from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
Money=Annotated[Decimal,Field(gt=0,max_digits=14,decimal_places=2),PlainSerializer(float,return_type=float,when_used="json")]
class OrderStatus(str,Enum):
    PENDING="PENDING"; CONFIRMED="CONFIRMED"; REJECTED="REJECTED"; CANCELLED="CANCELLED"
class CreateOrderItem(BaseModel):
    product_id: Annotated[int,Field(gt=0)]
    quantity: Annotated[int,Field(gt=0)]
class CreateOrderRequest(BaseModel):
    restaurant_id: Annotated[int,Field(gt=0)]
    items: Annotated[list[CreateOrderItem],Field(min_length=1)]
class OrderItemRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    product_id:int
    quantity:int
    unit_price_npr:Money
class OrderRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    restaurant_id:int
    items:list[OrderItemRead]
    status:OrderStatus
    total_npr:Money
    created_at:datetime
