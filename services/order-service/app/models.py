from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
ORDER_STATUSES=("PENDING","CONFIRMED","REJECTED","CANCELLED")
class Order(Base):
    __tablename__="orders"
    __table_args__=(CheckConstraint("total_npr > 0",name="ck_orders_total_positive"),)
    id: Mapped[int]=mapped_column(primary_key=True,autoincrement=True)
    restaurant_id: Mapped[int]=mapped_column(nullable=False)
    status: Mapped[str]=mapped_column(Enum(*ORDER_STATUSES,name="order_status"),nullable=False)
    total_npr: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,server_default=func.now())
    items: Mapped[list["OrderItem"]]=relationship(back_populates="order",cascade="all, delete-orphan",lazy="selectin",order_by="OrderItem.id")
class OrderItem(Base):
    __tablename__="order_items"
    __table_args__=(CheckConstraint("quantity > 0",name="ck_order_items_quantity_positive"),CheckConstraint("unit_price_npr > 0",name="ck_order_items_price_positive"))
    id: Mapped[int]=mapped_column(primary_key=True,autoincrement=True)
    order_id: Mapped[int]=mapped_column(ForeignKey("orders.id",ondelete="CASCADE"),nullable=False,index=True)
    product_id: Mapped[int]=mapped_column(nullable=False)
    quantity: Mapped[int]=mapped_column(nullable=False)
    unit_price_npr: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    order: Mapped[Order]=relationship(back_populates="items")
