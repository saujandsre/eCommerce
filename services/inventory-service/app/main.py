from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import InventoryItem
from app.schemas import InventoryItemRead, QuantityRequest

app = FastAPI(title="Inventory Service", version="0.2.0")

@app.get("/health")
def health() -> dict[str, str]: return {"status": "healthy"}

@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try: db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc: raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}

@app.get("/inventory", response_model=list[InventoryItemRead])
def list_inventory(db: Session = Depends(get_db)) -> list[InventoryItem]:
    return list(db.scalars(select(InventoryItem).order_by(InventoryItem.product_id)))

@app.get("/inventory/{product_id}", response_model=InventoryItemRead)
def get_inventory(product_id: int, db: Session = Depends(get_db)) -> InventoryItem:
    item = db.get(InventoryItem, product_id)
    if item is None: raise HTTPException(status_code=404, detail="Inventory item not found")
    return item

def change_inventory(db: Session, product_id: int, quantity: int, reserve: bool) -> InventoryItem:
    eligible = InventoryItem.quantity_available >= quantity if reserve else InventoryItem.quantity_reserved >= quantity
    item = db.scalar(update(InventoryItem).where(InventoryItem.product_id == product_id, eligible).values(
        quantity_available=InventoryItem.quantity_available + (-quantity if reserve else quantity),
        quantity_reserved=InventoryItem.quantity_reserved + (quantity if reserve else -quantity)).returning(InventoryItem))
    if item is None:
        if db.get(InventoryItem, product_id) is None: raise HTTPException(status_code=404, detail="Inventory item not found")
        detail = "Insufficient inventory" if reserve else "Cannot release more than reserved inventory"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    db.commit()
    return item

@app.post("/inventory/{product_id}/reserve", response_model=InventoryItemRead)
def reserve_inventory(product_id: int, request: QuantityRequest, db: Session = Depends(get_db)) -> InventoryItem:
    return change_inventory(db, product_id, request.quantity, True)

@app.post("/inventory/{product_id}/release", response_model=InventoryItemRead)
def release_inventory(product_id: int, request: QuantityRequest, db: Session = Depends(get_db)) -> InventoryItem:
    return change_inventory(db, product_id, request.quantity, False)
