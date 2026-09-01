from decimal import Decimal
from sqlalchemy import CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
class RestaurantAccount(Base):
    __tablename__ = "restaurant_accounts"
    __table_args__ = (CheckConstraint("credit_limit_npr >= 0", name="ck_accounts_limit_nonnegative"), CheckConstraint("available_credit_npr >= 0", name="ck_accounts_available_nonnegative"), CheckConstraint("reserved_credit_npr >= 0", name="ck_accounts_reserved_nonnegative"), CheckConstraint("available_credit_npr + reserved_credit_npr <= credit_limit_npr", name="ck_accounts_credit_within_limit"))
    restaurant_id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_limit_npr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    available_credit_npr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reserved_credit_npr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
