"""
Script to seed test cars into the database.
"""
from app.db.session import SessionLocal
from app.db.models import Cars, NoOfSeats, FuelType, TransmissionType, CarType
from app.core.config import settings

def seed_cars():
    db = SessionLocal()
    try:
        # Check if table is empty
        cars_count = db.query(Cars).count()
        if cars_count > 0:
            print(f"Database already has {cars_count} cars. Skipping seeding.")
            return

        print("Seeding test cars...")
        test_cars = [
            Cars(
                brand="Maruti",
                car_model="Swift",
                base_price=100.0,
                damage_price=500.0,
                protection_price=200.0,
                no_of_km=100,
                active=True,
                fuel_type=FuelType.PETROL,
                transmission_type=TransmissionType.MANUAL,
                no_of_seats=NoOfSeats.FIVE,
                car_type=CarType.HATCHBACK,
                images="https://imgd.aeplcdn.com/664x374/n/cw/ec/159099/swift-exterior-right-front-three-quarter.jpeg",
                prices={"daily": 1500.0}
            ),
            Cars(
                brand="Hyundai",
                car_model="Creta",
                base_price=150.0,
                damage_price=1000.0,
                protection_price=400.0,
                no_of_km=100,
                active=True,
                fuel_type=FuelType.DIESEL,
                transmission_type=TransmissionType.AUTOMATIC,
                no_of_seats=NoOfSeats.FIVE,
                car_type=CarType.SUV,
                images="https://imgd.aeplcdn.com/664x374/n/cw/ec/141125/creta-exterior-right-front-three-quarter.jpeg",
                prices={"daily": 2500.0}
            )
        ]
        db.add_all(test_cars)
        db.commit()
        print("Successfully seeded 2 test cars.")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print(f"Target Database: {settings.DATABASE_URL}")
    seed_cars()
