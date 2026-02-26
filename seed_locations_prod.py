"""
Seed locations into the database using SQLAlchemy.
Works with both SQLite (local) and PostgreSQL (production).

Usage:
    python seed_locations_prod.py

On production server (e.g., Render):
    Set DATABASE_URL env var, then run this script.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine
from app.db import models
from app.core.logging_config import logger

# ─── Define your desired locations here ─────────────────────────────────────
LOCATIONS_TO_SEED = [
    {"location": "Madhapur (HYD)", "maps_link": None},
    {"location": "Chilakalurupet",  "maps_link": None},
    {"location": "Guntur",          "maps_link": None},
]
# ─────────────────────────────────────────────────────────────────────────────


def seed_locations():
    db = SessionLocal()
    try:
        added = 0
        skipped = 0
        for entry in LOCATIONS_TO_SEED:
            existing = db.query(models.Location).filter(
                models.Location.location == entry["location"]
            ).first()

            if existing:
                print(f"  [SKIP]  '{entry['location']}' already exists (id={existing.id})")
                skipped += 1
            else:
                loc = models.Location(
                    location=entry["location"],
                    maps_link=entry.get("maps_link")
                )
                db.add(loc)
                print(f"  [ADD]   '{entry['location']}' added")
                added += 1

        db.commit()
        print(f"\nDone! Added: {added}, Skipped: {skipped}")

        # Show all locations after seeding
        all_locs = db.query(models.Location).order_by(models.Location.id).all()
        print("\nAll locations in DB:")
        for loc in all_locs:
            print(f"  id={loc.id}  name='{loc.location}'  maps={loc.maps_link}")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print(f"Seeding locations...")
    print(f"Database: {os.getenv('DATABASE_URL', 'sqlite:///./gogocar.db')}\n")
    seed_locations()
