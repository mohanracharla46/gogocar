"""
CCAvenue payment gateway service
Handles order creation, encryption, decryption, and payment verification
Uses official CCAvenue Python kit for encryption/decryption
"""
import urllib.parse
from typing import Dict, Optional, Any
from app.core.config import settings
from app.core.logging_config import logger
from app.utils.ccavutil import encrypt, decrypt


class CCAvenueService:
    """CCAvenue payment gateway service using official CCAvenue Python kit"""
    
    def __init__(self):
        """Initialize CCAvenue service with credentials"""
        self.merchant_id = settings.CCAVENUE_MERCHANT_ID
        self.access_code = settings.CCAVENUE_ACCESS_CODE
        self.working_key = settings.CCAVENUE_WORKING_KEY
        self.environment = settings.CCAVENUE_ENVIRONMENT
        
        # Validate credentials
        if not self.merchant_id or not self.access_code or not self.working_key:
            logger.warning("CCAvenue credentials not fully configured. Payment integration may not work.")
        
        # CCAvenue URLs
        if self.environment == "production":
            self.payment_url = "https://secure.ccavenue.com/transaction/transaction.do?command=initiateTransaction"
            self.status_url = "https://secure.ccavenue.com/transaction/getStatusByJson"
        else:
            self.payment_url = "https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction"
            self.status_url = "https://test.ccavenue.com/transaction/getStatusByJson"
        
        logger.info(f"CCAvenue service initialized with environment: {self.environment}")
    
    
    def create_order_data(
        self,
        order_id: str,
        amount: float,
        currency: str = "INR",
        redirect_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        billing_name: Optional[str] = None,
        billing_address: Optional[str] = None,
        billing_city: Optional[str] = None,
        billing_state: Optional[str] = None,
        billing_zip: Optional[str] = None,
        billing_country: Optional[str] = "India",
        billing_tel: Optional[str] = None,
        billing_email: Optional[str] = None,
        delivery_name: Optional[str] = None,
        delivery_address: Optional[str] = None,
        delivery_city: Optional[str] = None,
        delivery_state: Optional[str] = None,
        delivery_zip: Optional[str] = None,
        delivery_country: Optional[str] = "India",
        delivery_tel: Optional[str] = None,
        merchant_param1: Optional[str] = None,
        merchant_param2: Optional[str] = None,
        merchant_param3: Optional[str] = None,
        merchant_param4: Optional[str] = None,
        merchant_param5: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create order data for CCAvenue payment
        
        Args:
            order_id: Unique order ID
            amount: Order amount
            currency: Currency code (default: INR)
            redirect_url: Redirect URL after payment
            cancel_url: Cancel URL
            billing_name: Billing name
            billing_address: Billing address
            billing_city: Billing city
            billing_state: Billing state
            billing_zip: Billing zip
            billing_country: Billing country
            billing_tel: Billing telephone
            billing_email: Billing email
            delivery_name: Delivery name
            delivery_address: Delivery address
            delivery_city: Delivery city
            delivery_state: Delivery state
            delivery_zip: Delivery zip
            delivery_country: Delivery country
            delivery_tel: Delivery telephone
            merchant_param1-5: Merchant parameters
            
        Returns:
            Dictionary with order data
        """
        if redirect_url is None:
            redirect_url = settings.CCAVENUE_REDIRECT_URL
        if cancel_url is None:
            cancel_url = settings.CCAVENUE_CANCEL_URL
        
        order_data = {
            "merchant_id": self.merchant_id,
            "order_id": order_id,
            "amount": str(amount),
            "currency": currency,
            "redirect_url": redirect_url,
            "cancel_url": cancel_url,
            "language": "EN",
        }
        
        # Add billing details if provided
        if billing_name:
            order_data["billing_name"] = billing_name
        if billing_address:
            order_data["billing_address"] = billing_address
        if billing_city:
            order_data["billing_city"] = billing_city
        if billing_state:
            order_data["billing_state"] = billing_state
        if billing_zip:
            order_data["billing_zip"] = billing_zip
        if billing_country:
            order_data["billing_country"] = billing_country
        if billing_tel:
            order_data["billing_tel"] = billing_tel
        if billing_email:
            order_data["billing_email"] = billing_email
        
        # Add delivery details if provided
        if delivery_name:
            order_data["delivery_name"] = delivery_name
        if delivery_address:
            order_data["delivery_address"] = delivery_address
        if delivery_city:
            order_data["delivery_city"] = delivery_city
        if delivery_state:
            order_data["delivery_state"] = delivery_state
        if delivery_zip:
            order_data["delivery_zip"] = delivery_zip
        if delivery_country:
            order_data["delivery_country"] = delivery_country
        if delivery_tel:
            order_data["delivery_tel"] = delivery_tel
        
        # Add merchant parameters
        if merchant_param1:
            order_data["merchant_param1"] = merchant_param1
        if merchant_param2:
            order_data["merchant_param2"] = merchant_param2
        if merchant_param3:
            order_data["merchant_param3"] = merchant_param3
        if merchant_param4:
            order_data["merchant_param4"] = merchant_param4
        if merchant_param5:
            order_data["merchant_param5"] = merchant_param5
        
        return order_data
    
    def get_payment_form_data(self, order_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Get payment form data with encrypted order data using official CCAvenue kit
        
        Args:
            order_data: Order data dictionary
            
        Returns:
            Dictionary with form data for payment page (encRequest and access_code)
        """
        # Validate credentials
        if not self.merchant_id:
            raise ValueError("Merchant ID is not configured")
        if not self.access_code:
            raise ValueError("Access code is not configured")
        if not self.working_key:
            raise ValueError("Working key is not configured")
        
        logger.info(f"Encrypting order data: {order_data}")
        
        try:
            # Build query string from order data (exactly as per CCAvenue official kit)
            # Format: key1=value1&key2=value2&... (NO URL encoding, direct concatenation)
            # The official kit does NOT URL encode values - just concatenates them
            query_parts = []
            for key, value in order_data.items():
                if value is not None:
                    # Convert to string - NO URL encoding (matching official kit behavior)
                    str_value = str(value)
                    query_parts.append(f"{key}={str_value}")
            
            # Join with & and add trailing & (as per CCAvenue specification)
            merchant_data = "&".join(query_parts) + "&"
            
            logger.debug(f"Merchant data query string length: {len(merchant_data)}")
            logger.debug(f"Merchant data (full): {merchant_data}")
            
            # Validate working key is not empty
            if not self.working_key or len(self.working_key.strip()) == 0:
                raise ValueError("Working key is empty or whitespace only")
            
            logger.debug(f"Working key length: {len(self.working_key)}, first 4 chars: {self.working_key[:4]}...")
            
            # Encrypt using official CCAvenue kit
            encrypted_data = encrypt(merchant_data, self.working_key)
            
            logger.info(f"Encryption successful. Encrypted data length: {len(encrypted_data)}")
            logger.debug(f"Encrypted data (first 100 chars): {encrypted_data[:100]}...")
            
            # Prepare form data for CCAvenue
            form_data = {
                "encRequest": encrypted_data,
                "access_code": self.access_code,
            }
            
            return form_data
        except Exception as e:
            logger.error(f"Error encrypting payment data: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to encrypt payment data: {str(e)}")
    
    def verify_payment(self, enc_response: str) -> Dict[str, Any]:
        """
        Verify payment response from CCAvenue using official CCAvenue kit
        
        Args:
            enc_response: Encrypted response from CCAvenue (encResponse parameter)
            
        Returns:
            Dictionary with payment response data
        """
        try:
            # Decrypt using official CCAvenue kit
            decrypted_response = decrypt(enc_response, self.working_key)
            
            # Parse the decrypted response string into a dictionary
            # Format: key1=value1&key2=value2&...
            response_data = {}
            for param in decrypted_response.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    # No URL decoding needed (matching official kit - they don't encode/decode)
                    response_data[key] = value
            
            logger.info(f"Payment verification response: {response_data}")
            
            return response_data
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}", exc_info=True)
            raise
    
    def get_payment_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get payment status from CCAvenue
        
        Args:
            order_id: Order ID to check status
            
        Returns:
            Dictionary with payment status
        """
        try:
            # Prepare request data
            request_data = {
                "reference_no": order_id,
                "order_no": order_id,
            }
            
            # This would typically make an API call to CCAvenue
            # For now, return a placeholder
            logger.info(f"Checking payment status for order: {order_id}")
            
            return {
                "status": "pending",
                "message": "Status check not implemented"
            }
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            raise


# Create global instance
ccavenue_service = CCAvenueService()

