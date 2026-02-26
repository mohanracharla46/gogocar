from app.db.session import SessionLocal
from app.db.models import Cars
from app.core.config import settings

db = SessionLocal()
cars_count = db.query(Cars).count()
print(f"Database URL: {settings.DATABASE_URL}")
print(f"Total cars in DB: {cars_count}")

# Print first two cars if any
if cars_count > 0:
    cars = db.query(Cars).limit(2).all()
    for car in cars:
        print(f"Car: {car.id} - {car.brand} {car.car_model} (Active: {car.active})")

db.close()
