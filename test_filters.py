import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/cars"

def test_get_all():
    print("\nTesting GET /api/cars (all)")
    r = requests.get(BASE_URL)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Count: {len(r.json())}")

def test_get_location_id(loc_id):
    print(f"\nTesting GET /api/cars?location_id={loc_id}")
    r = requests.get(f"{BASE_URL}?location_id={loc_id}")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Count: {len(r.json())}")
        for car in r.json():
            print(f" - {car['brand']} {car['model']} (Location ID: {loc_id})")

def test_get_availability():
    pickup = (datetime.now() + timedelta(days=1)).isoformat()
    ret = (datetime.now() + timedelta(days=2)).isoformat()
    print(f"\nTesting GET /api/cars?pickup_date={pickup}&return_date={ret}")
    r = requests.get(f"{BASE_URL}?pickup_date={pickup}&return_date={ret}")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Count: {len(r.json())}")

def test_backward_compat():
    print("\nTesting GET /api/cars (backward compat - other filters)")
    # Testing if seats still works (it should)
    r = requests.get(f"{BASE_URL}?seats=5&min_price=1000")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Count: {len(r.json())}")

if __name__ == "__main__":
    test_get_all()
    # Note: These values depend on existing DB content
    test_get_location_id(1) 
    test_get_availability()
    test_backward_compat()
