from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RestaurantAccount
from app.schemas import CreditRequest, RestaurantAccountRead
app = FastAPI(title="Account Service", version="0.2.0")
@app.get("/health")
def health() -> dict[str,str]: return {"status":"healthy"}
@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str,str]:
    try: db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc: raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status":"ready"}
@app.get("/accounts", response_model=list[RestaurantAccountRead])
def list_accounts(db: Session = Depends(get_db)) -> list[RestaurantAccount]: return list(db.scalars(select(RestaurantAccount).order_by(RestaurantAccount.restaurant_id)))
@app.get("/accounts/{restaurant_id}", response_model=RestaurantAccountRead)
def get_account(restaurant_id: int, db: Session = Depends(get_db)) -> RestaurantAccount:
    account = db.get(RestaurantAccount, restaurant_id)
    if account is None: raise HTTPException(status_code=404, detail="Restaurant account not found")
    return account
def change_credit(db: Session, restaurant_id: int, amount, reserve: bool) -> RestaurantAccount:
    eligible = RestaurantAccount.available_credit_npr >= amount if reserve else RestaurantAccount.reserved_credit_npr >= amount
    account = db.scalar(update(RestaurantAccount).where(RestaurantAccount.restaurant_id == restaurant_id, eligible).values(available_credit_npr=RestaurantAccount.available_credit_npr + (-amount if reserve else amount), reserved_credit_npr=RestaurantAccount.reserved_credit_npr + (amount if reserve else -amount)).returning(RestaurantAccount))
    if account is None:
        if db.get(RestaurantAccount, restaurant_id) is None: raise HTTPException(status_code=404, detail="Restaurant account not found")
        detail = "Insufficient available credit" if reserve else "Cannot release more than reserved credit"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    db.commit()
    return account
@app.post("/accounts/{restaurant_id}/reserve-credit", response_model=RestaurantAccountRead)
def reserve_credit(restaurant_id: int, request: CreditRequest, db: Session = Depends(get_db)) -> RestaurantAccount: return change_credit(db, restaurant_id, request.amount_npr, True)
@app.post("/accounts/{restaurant_id}/release-credit", response_model=RestaurantAccountRead)
def release_credit(restaurant_id: int, request: CreditRequest, db: Session = Depends(get_db)) -> RestaurantAccount: return change_credit(db, restaurant_id, request.amount_npr, False)
