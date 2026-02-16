import requests

url = "http://localhost:8000/auth/api/signup"
data = {
    "username": "testuser_" + str(int(__import__('time').time())),
    "email": "test" + str(int(__import__('time').time())) + "@example.com",
    "password": "testpassword123",
    "firstname": "Test",
    "lastname": "User"
}

try:
    response = requests.post(url, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
