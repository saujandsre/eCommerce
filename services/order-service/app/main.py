from decimal import Decimal, InvalidOperation
import os
import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, OrderItem
from app.schemas import CreateOrderRequest, OrderRead

CATALOG_SERVICE_URL=os.getenv("CATALOG_SERVICE_URL","http://localhost:8001").rstrip("/")
INVENTORY_SERVICE_URL=os.getenv("INVENTORY_SERVICE_URL","http://localhost:8002").rstrip("/")
ACCOUNT_SERVICE_URL=os.getenv("ACCOUNT_SERVICE_URL","http://localhost:8003").rstrip("/")
DOWNSTREAM_TIMEOUT_SECONDS=5.0
app=FastAPI(title="Order Service",version="0.3.0")

@app.get("/health")
def health()->dict[str,str]: return {"status":"healthy"}
@app.get("/ready")
def ready(db:Session=Depends(get_db))->dict[str,str]:
    try: db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc: raise HTTPException(status_code=503,detail="Database unavailable") from exc
    return {"status":"ready"}
@app.get("/orders",response_model=list[OrderRead])
def list_orders(db:Session=Depends(get_db))->list[Order]: return list(db.scalars(select(Order).order_by(Order.id)))
def find_order(db:Session,order_id:int,for_update:bool=False)->Order:
    statement=select(Order).where(Order.id==order_id)
    if for_update:
        statement=statement.with_for_update()
    order=db.scalar(statement)
    if order is None: raise HTTPException(status_code=404,detail="Order not found")
    return order
@app.get("/orders/{order_id}",response_model=OrderRead)
def get_order(order_id:int,db:Session=Depends(get_db))->Order: return find_order(db,order_id)

def call_downstream(client:httpx.Client,method:str,url:str,service_name:str,**kwargs:object)->httpx.Response:
    try: response=client.request(method,url,**kwargs)
    except httpx.RequestError as exc: raise HTTPException(status_code=502,detail=f"{service_name} is unavailable") from exc
    if response.is_success: return response
    if response.status_code in {404,409}:
        try: detail=response.json().get("detail")
        except (ValueError,AttributeError): detail=None
        raise HTTPException(status_code=response.status_code,detail=detail or f"{service_name} rejected the request")
    raise HTTPException(status_code=502,detail=f"{service_name} returned an unexpected response")

def compensate_inventory(client:httpx.Client,reserved:list[tuple[int,int]])->None:
    for product_id,quantity in reversed(reserved):
        try: call_downstream(client,"POST",f"{INVENTORY_SERVICE_URL}/inventory/{product_id}/release","Inventory service",json={"quantity":quantity})
        except HTTPException: pass
def compensate_credit(client:httpx.Client,restaurant_id:int,total:Decimal)->None:
    try: call_downstream(client,"POST",f"{ACCOUNT_SERVICE_URL}/accounts/{restaurant_id}/release-credit","Account service",json={"amount_npr":float(total)})
    except HTTPException: pass

@app.post("/orders",response_model=OrderRead,status_code=201)
def create_order(request:CreateOrderRequest,db:Session=Depends(get_db))->Order:
    priced:list[tuple[int,int,Decimal]]=[]
    reserved:list[tuple[int,int]]=[]
    credit_reserved=False
    with httpx.Client(timeout=DOWNSTREAM_TIMEOUT_SECONDS) as client:
        for item in request.items:
            response=call_downstream(client,"GET",f"{CATALOG_SERVICE_URL}/products/{item.product_id}","Catalog service")
            try:
                price=Decimal(str(response.json()["price_npr"]))
                if price <= 0: raise ValueError
            except (KeyError,TypeError,ValueError,InvalidOperation) as exc:
                raise HTTPException(status_code=502,detail="Catalog service returned invalid product data") from exc
            priced.append((item.product_id,item.quantity,price))
        try:
            for product_id,quantity,_ in priced:
                call_downstream(client,"POST",f"{INVENTORY_SERVICE_URL}/inventory/{product_id}/reserve","Inventory service",json={"quantity":quantity})
                reserved.append((product_id,quantity))
            total=sum((Decimal(quantity)*price for _,quantity,price in priced),Decimal("0"))
            call_downstream(client,"POST",f"{ACCOUNT_SERVICE_URL}/accounts/{request.restaurant_id}/reserve-credit","Account service",json={"amount_npr":float(total)})
            credit_reserved=True
        except HTTPException:
            compensate_inventory(client,reserved)
            raise
        order=Order(restaurant_id=request.restaurant_id,status="CONFIRMED",total_npr=total,items=[OrderItem(product_id=p,quantity=q,unit_price_npr=price) for p,q,price in priced])
        db.add(order)
        try: db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            if credit_reserved: compensate_credit(client,request.restaurant_id,total)
            compensate_inventory(client,reserved)
            raise HTTPException(status_code=503,detail="Order could not be persisted") from exc
        db.refresh(order)
        return order

@app.post("/orders/{order_id}/confirm",response_model=OrderRead)
def confirm_order(order_id:int,db:Session=Depends(get_db))->Order:
    order=find_order(db,order_id)
    if order.status!="PENDING": raise HTTPException(status_code=409,detail="Only pending orders can be confirmed")
    order.status="CONFIRMED"; db.commit(); return order
@app.post("/orders/{order_id}/cancel",response_model=OrderRead)
def cancel_order(order_id:int,db:Session=Depends(get_db))->Order:
    order=find_order(db,order_id,for_update=True)
    if order.status not in {"PENDING","CONFIRMED"}: raise HTTPException(status_code=409,detail="Order cannot be cancelled from its current status")
    if order.status=="CONFIRMED":
        reserved=[(item.product_id,item.quantity) for item in order.items]
        with httpx.Client(timeout=DOWNSTREAM_TIMEOUT_SECONDS) as client:
            compensate_inventory(client,reserved)
            compensate_credit(client,order.restaurant_id,order.total_npr)
    order.status="CANCELLED"; db.commit(); return order
