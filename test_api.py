import requests
import json

try:
    response = requests.get("http://localhost:8000/api/cars")
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.content.decode()}")
    try:
        print(f"Formatted JSON: {json.dumps(response.json(), indent=2)}")
    except:
        pass
except Exception as e:
    print(f"Error: {e}")
