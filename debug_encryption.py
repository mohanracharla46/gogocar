from app.services.ccavenue_service import ccavenue_service
from app.utils.ccavutil import decrypt

# Payload simulating real request
order_data = {
    "merchant_id": "4400029",
    "order_id": "TEST12345",
    "amount": "100.00",
    "currency": "INR",
    "redirect_url": "http://127.0.0.1:8000/payments/callback",
    "cancel_url": "http://127.0.0.1:8000/payments/cancel",
    "language": "EN"
}

print("--- 1. Generating Order Data ---")
# Manually replicate create_order_data logic from current service file to see exactly what's passing
# (Or just call the method if I could, but create_form_data does the encryption)

print(f"Redirect URL in dict: {order_data['redirect_url']}")

print("--- 2. Building Merchant Data String ---")
query_parts = []
for key, value in order_data.items():
    if value is not None:
        str_value = str(value)
        query_parts.append(f"{key}={str_value}")

merchant_data = "&".join(query_parts) + "&"
print(f"Merchant Data Raw: {merchant_data}")

print("--- 3. Encrypting ---")
try:
    encrypted = ccavenue_service.get_payment_form_data(order_data)['encRequest']
    print(f"Encrypted length: {len(encrypted)}")
    
    print("--- 4. Decrypting back to verify ---")
    decrypted = decrypt(encrypted, ccavenue_service.working_key)
    print(f"Decrypted: {decrypted}")
    
    if "http://127.0.0.1" in decrypted:
        print("SUCCESS: Protocol http:// preserved in decryption")
    else:
        print("FAILURE: Protocol lost/mangled")

except Exception as e:
    print(f"Error: {e}")
