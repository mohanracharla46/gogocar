"""
Test script for POST /api/mobile/kyc/upload

Usage:
    python test_kyc_upload.py

Steps it performs:
    1. Login to get a JWT token
    2. Upload aadhaar_front + aadhaar_back (required)
    3. Optionally upload drivinglicense files too
    4. Verify response: {"message": "KYC uploaded successfully", "kyc_status": "PENDING"}
"""

import io
import requests

BASE_URL = "http://localhost:8000"

# ── Step 1: Login ──────────────────────────────────────────────────────────────
LOGIN_URL = f"{BASE_URL}/api/mobile/login"

login_payload = {
    "username": "testuser",   # ← change to a valid mobile user
    "password": "test1234",   # ← change to match
}

print("Step 1: Logging in...")
login_resp = requests.post(LOGIN_URL, json=login_payload)
print(f"  Status : {login_resp.status_code}")

if login_resp.status_code != 200:
    print(f"  Error  : {login_resp.text}")
    print("\nCannot continue without a valid token. Check username/password.")
    exit(1)

token = login_resp.json()["access_token"]
print(f"  Token  : {token[:40]}...")

headers = {"Authorization": f"Bearer {token}"}

# ── Step 2: Upload KYC documents ───────────────────────────────────────────────
KYC_URL = f"{BASE_URL}/api/mobile/kyc/upload"

# Create minimal in-memory PNG bytes (1x1 white pixel)
DUMMY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
    b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
    b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)

files = {
    "aadhaar_front":          ("aadhaar_front.png",  io.BytesIO(DUMMY_PNG), "image/png"),
    "aadhaar_back":           ("aadhaar_back.png",   io.BytesIO(DUMMY_PNG), "image/png"),
    "drivinglicense_front":   ("dl_front.png",       io.BytesIO(DUMMY_PNG), "image/png"),
    "drivinglicense_back":    ("dl_back.png",        io.BytesIO(DUMMY_PNG), "image/png"),
}

print("\nStep 2: Uploading KYC documents (all 4)...")
kyc_resp = requests.post(KYC_URL, headers=headers, files=files)
print(f"  Status  : {kyc_resp.status_code}")
print(f"  Response: {kyc_resp.json()}")

assert kyc_resp.status_code == 200, "Expected HTTP 200"
body = kyc_resp.json()
assert body.get("message") == "KYC uploaded successfully", "Wrong message"
assert body.get("kyc_status") == "PENDING", "kyc_status should be PENDING"

print("\n✅ All assertions passed. Endpoint is working correctly.")

# ── Step 3: Upload aadhaar only (optional docs omitted) ───────────────────────
print("\nStep 3: Uploading KYC with mandatory docs only (no DL)...")

files_minimal = {
    "aadhaar_front": ("aadhaar_front.png", io.BytesIO(DUMMY_PNG), "image/png"),
    "aadhaar_back":  ("aadhaar_back.png",  io.BytesIO(DUMMY_PNG), "image/png"),
}

kyc_resp2 = requests.post(KYC_URL, headers=headers, files=files_minimal)
print(f"  Status  : {kyc_resp2.status_code}")
print(f"  Response: {kyc_resp2.json()}")

assert kyc_resp2.status_code == 200, "Expected HTTP 200 for mandatory-only upload"
print("\n✅ Mandatory-only upload also works correctly.")
