from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field

class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: Annotated[int, Field(gt=0)]
    sku: Annotated[str, Field(min_length=1, max_length=100)]
    quantity_available: Annotated[int, Field(ge=0)]
    quantity_reserved: Annotated[int, Field(ge=0)]

class QuantityRequest(BaseModel):
    quantity: Annotated[int, Field(gt=0)]
