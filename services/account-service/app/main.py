from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


class RestaurantAccount(BaseModel):
    restaurant_id: Annotated[int, Field(gt=0)]
    restaurant_name: Annotated[str, Field(min_length=1)]
    credit_limit_npr: Annotated[float, Field(ge=0)]
    available_credit_npr: Annotated[float, Field(ge=0)]
    reserved_credit_npr: Annotated[float, Field(ge=0)]


class CreditRequest(BaseModel):
    amount_npr: Annotated[float, Field(gt=0)]


SAMPLE_ACCOUNTS = [
    RestaurantAccount(restaurant_id=1, restaurant_name="Himalayan Kitchen", credit_limit_npr=500000, available_credit_npr=450000, reserved_credit_npr=50000),
    RestaurantAccount(restaurant_id=2, restaurant_name="Kathmandu Bistro", credit_limit_npr=300000, available_credit_npr=300000, reserved_credit_npr=0),
    RestaurantAccount(restaurant_id=3, restaurant_name="Everest Momo House", credit_limit_npr=150000, available_credit_npr=125000, reserved_credit_npr=25000),
]

accounts: dict[int, RestaurantAccount] = {account.restaurant_id: account.model_copy() for account in SAMPLE_ACCOUNTS}

app = FastAPI(title="Account Service", version="0.1.0")


def find_account(restaurant_id: int) -> RestaurantAccount:
    account = accounts.get(restaurant_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant account not found")
    return account


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/accounts", response_model=list[RestaurantAccount])
def list_accounts() -> list[RestaurantAccount]:
    return list(accounts.values())


@app.get("/accounts/{restaurant_id}", response_model=RestaurantAccount)
def get_account(restaurant_id: int) -> RestaurantAccount:
    return find_account(restaurant_id)


@app.post("/accounts/{restaurant_id}/reserve-credit", response_model=RestaurantAccount)
def reserve_credit(restaurant_id: int, request: CreditRequest) -> RestaurantAccount:
    account = find_account(restaurant_id)
    if request.amount_npr > account.available_credit_npr:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient available credit")
    account.available_credit_npr -= request.amount_npr
    account.reserved_credit_npr += request.amount_npr
    return account


@app.post("/accounts/{restaurant_id}/release-credit", response_model=RestaurantAccount)
def release_credit(restaurant_id: int, request: CreditRequest) -> RestaurantAccount:
    account = find_account(restaurant_id)
    if request.amount_npr > account.reserved_credit_npr:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot release more than reserved credit")
    account.reserved_credit_npr -= request.amount_npr
    account.available_credit_npr += request.amount_npr
    return account
