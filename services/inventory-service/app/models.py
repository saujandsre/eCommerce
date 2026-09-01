from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (CheckConstraint("quantity_available >= 0", name="ck_inventory_available_nonnegative"), CheckConstraint("quantity_reserved >= 0", name="ck_inventory_reserved_nonnegative"))
    product_id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    quantity_available: Mapped[int] = mapped_column(nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(nullable=False, default=0)
