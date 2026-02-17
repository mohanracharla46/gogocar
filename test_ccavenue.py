#!/usr/bin/env python
"""
Test script to verify CCAvenue credentials and encryption/decryption
"""
import sys
from app.core.config import settings
from app.utils.ccavutil import encrypt, decrypt

def test_ccavenue_credentials():
    """Test CCAvenue credentials and encryption"""
    print("=" * 60)
    print("CCAvenue Configuration Test")
    print("=" * 60)
    
    # Check credentials
    print(f"\n1. Checking Credentials:")
    print(f"   Merchant ID: {'OK' if settings.CCAVENUE_MERCHANT_ID else 'MISSING'}")
    print(f"   Access Code: {'OK' if settings.CCAVENUE_ACCESS_CODE else 'MISSING'}")
    print(f"   Working Key: {'OK' if settings.CCAVENUE_WORKING_KEY else 'MISSING'}")
    print(f"   Environment: {settings.CCAVENUE_ENVIRONMENT}")
    
    if not all([settings.CCAVENUE_MERCHANT_ID, settings.CCAVENUE_ACCESS_CODE, settings.CCAVENUE_WORKING_KEY]):
        print("\nERROR: CCAvenue credentials are not fully configured!")
        return False
    
    # Test encryption/decryption
    print(f"\n2. Testing Encryption/Decryption:")
    test_data = "merchant_id=123456&order_id=TEST12345&amount=1000&currency=INR&"
    
    try:
        # Encrypt
        encrypted = encrypt(test_data, settings.CCAVENUE_WORKING_KEY)
        print(f"   [OK] Encryption successful (length: {len(encrypted)})")
        
        # Decrypt
        decrypted = decrypt(encrypted, settings.CCAVENUE_WORKING_KEY)
        print(f"   [OK] Decryption successful")
        
        # Verify
        if test_data == decrypted:
            print(f"   [OK] Data integrity verified")
        else:
            print(f"   [FAIL] Data mismatch after decrypt")
            print(f"     Original: {test_data[:50]}...")
            print(f"     Decrypted: {decrypted[:50]}...")
            return False
            
    except Exception as e:
        print(f"   [FAIL] Encryption/Decryption failed: {str(e)}")
        return False
    
    # Show credential values (masked)
    print(f"\n3. Credential Values:")
    print(f"   Merchant ID: {settings.CCAVENUE_MERCHANT_ID}")
    print(f"   Access Code: {settings.CCAVENUE_ACCESS_CODE[:4]}...{settings.CCAVENUE_ACCESS_CODE[-4:]}")
    print(f"   Working Key: {settings.CCAVENUE_WORKING_KEY[:4]}...{settings.CCAVENUE_WORKING_KEY[-4:]}")
    
    # Test order data creation
    print(f"\n4. Testing CCAvenue Service:")
    try:
        from app.services.ccavenue_service import ccavenue_service
        
        test_order = ccavenue_service.create_order_data(
            order_id="TEST12345",
            amount=1000.00,
            billing_name="Test User",
            billing_email="test@example.com",
            billing_tel="9876543210"
        )
        print(f"   [OK] Order data created successfully")
        print(f"   [OK] Order ID: {test_order['order_id']}")
        print(f"   [OK] Amount: {test_order['amount']}")
        
        # Test form data preparation
        form_data = ccavenue_service.get_payment_form_data(test_order)
        print(f"   [OK] Payment form data prepared")
        print(f"   [OK] Encrypted request length: {len(form_data['encRequest'])}")
        print(f"   [OK] Access code: {form_data['access_code']}")
        
    except Exception as e:
        print(f"   [FAIL] CCAvenue service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("SUCCESS: All tests passed! CCAvenue is configured correctly.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_ccavenue_credentials()
    sys.exit(0 if success else 1)
