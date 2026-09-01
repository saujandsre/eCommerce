from decimal import Decimal
from sqlalchemy.dialects.postgresql import insert
from app.database import SessionLocal
from app.models import Product
ROWS=[(1,"RICE-BASMATI-25KG","Basmati Rice","Grains",4250,"25 kg bag"),(2,"OIL-SUNFLOWER-15L","Sunflower Cooking Oil","Cooking Oils",3450,"15 litre tin"),(3,"CHICKEN-WHOLE-1KG","Fresh Whole Chicken","Meat & Poultry",480,"kg"),(4,"TOMATO-LOCAL-1KG","Fresh Local Tomatoes","Fresh Produce",110,"kg"),(5,"CLEAN-DISHWASH-5L","Commercial Dishwashing Liquid","Cleaning Supplies",950,"5 litre container"),(6,"FLOUR-WHEAT-10KG","Whole Wheat Flour","Grains",980,"10 kg bag"),(7,"LENTIL-MASOOR-5KG","Masoor Dal","Pulses",925,"5 kg bag"),(8,"POTATO-LOCAL-10KG","Local Potatoes","Fresh Produce",750,"10 kg sack"),(9,"ONION-RED-10KG","Red Onions","Fresh Produce",900,"10 kg sack"),(10,"MILK-FULLCREAM-1L","Full Cream Milk","Dairy",120,"litre"),(11,"PANEER-FRESH-1KG","Fresh Paneer","Dairy",780,"kg"),(12,"SPICE-MASALA-1KG","Restaurant Garam Masala","Spices",650,"kg"),(13,"TEA-CTC-1KG","Nepali CTC Tea","Beverages",720,"kg"),(14,"SUGAR-WHITE-25KG","White Sugar","Pantry",2600,"25 kg bag"),(15,"NAPKIN-PAPER-100","Paper Napkins","Consumables",180,"pack of 100")]
def main():
    values=[dict(id=i,sku=s,name=n,category=c,price_npr=Decimal(p),unit=u) for i,s,n,c,p,u in ROWS]
    with SessionLocal.begin() as db: db.execute(insert(Product).values(values).on_conflict_do_nothing())
    print(f"Catalog seed complete ({len(values)} definitions).")
if __name__=="__main__": main()
