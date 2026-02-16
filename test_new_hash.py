from app.core.security import get_password_hash
try:
    print(f"New hash: {get_password_hash('admin123')}")
except Exception as e:
    print(f"Error: {e}")
