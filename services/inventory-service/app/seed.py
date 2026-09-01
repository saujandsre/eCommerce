from sqlalchemy.dialects.postgresql import insert
from app.database import SessionLocal
from app.models import InventoryItem
ROWS = [(1,"RICE-BASMATI-25KG",120),(2,"OIL-SUNFLOWER-15L",75),(3,"CHICKEN-WHOLE-1KG",250),(4,"TOMATO-LOCAL-1KG",400),(5,"CLEAN-DISHWASH-5L",60),(6,"FLOUR-WHEAT-10KG",100),(7,"LENTIL-MASOOR-5KG",140),(8,"POTATO-LOCAL-10KG",180),(9,"ONION-RED-10KG",160),(10,"MILK-FULLCREAM-1L",220),(11,"PANEER-FRESH-1KG",90),(12,"SPICE-MASALA-1KG",70),(13,"TEA-CTC-1KG",85),(14,"SUGAR-WHITE-25KG",110),(15,"NAPKIN-PAPER-100",200)]
def main() -> None:
    values = [dict(product_id=i, sku=s, quantity_available=q, quantity_reserved=0) for i,s,q in ROWS]
    with SessionLocal.begin() as db: db.execute(insert(InventoryItem).values(values).on_conflict_do_nothing())
    print(f"Inventory seed complete ({len(values)} definitions).")
if __name__ == "__main__": main()
