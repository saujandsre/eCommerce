from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2), PlainSerializer(float, return_type=float, when_used="json")]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
class RestaurantAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    restaurant_id: Annotated[int, Field(gt=0)]
    restaurant_name: Annotated[str, Field(min_length=1, max_length=255)]
    credit_limit_npr: Money
    available_credit_npr: Money
    reserved_credit_npr: Money
class CreditRequest(BaseModel): amount_npr: PositiveMoney
