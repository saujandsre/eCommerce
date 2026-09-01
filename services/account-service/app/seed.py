from decimal import Decimal
from sqlalchemy.dialects.postgresql import insert
from app.database import SessionLocal
from app.models import RestaurantAccount
ROWS=[(1,"Himalayan Kitchen",500000),(2,"Kathmandu Bistro",300000),(3,"Everest Momo House",150000),(4,"Patan Newari Bhansa",250000),(5,"Pokhara Lakeside Cafe",200000),(6,"Bhaktapur Bhojanalaya",175000),(7,"Thamel Garden Restaurant",350000),(8,"Chitwan Family Kitchen",225000)]
def main():
    values=[dict(restaurant_id=i,restaurant_name=n,credit_limit_npr=Decimal(v),available_credit_npr=Decimal(v),reserved_credit_npr=Decimal("0")) for i,n,v in ROWS]
    with SessionLocal.begin() as db: db.execute(insert(RestaurantAccount).values(values).on_conflict_do_nothing())
    print(f"Account seed complete ({len(values)} definitions).")
if __name__=="__main__": main()
