from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

Price = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    PlainSerializer(float, return_type=float, when_used="json"),
]


class ProductCreate(BaseModel):
    id: Annotated[int, Field(gt=0)]
    sku: Annotated[str, Field(min_length=1, max_length=100)]
    name: Annotated[str, Field(min_length=1, max_length=255)]
    category: Annotated[str, Field(min_length=1, max_length=100)]
    price_npr: Price
    unit: Annotated[str, Field(min_length=1, max_length=100)]


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
