from app.db.session import SessionLocal
from app.db.models import Cars
db = SessionLocal()
cars = db.query(Cars).all()
for car in cars:
    print(f"ID: {car.id}, Brand: {car.brand}, Model: {car.car_model}, Type: {car.car_type}, Fuel: {car.fuel_type}, Active: {car.active}")
db.close()
