#!/usr/bin/env python
"""
CCAvenue encryption/decryption utilities
Official CCAvenue Python kit - Python 3 compatible version
"""

from Crypto.Cipher import AES
import hashlib


def pad(data):
    """
    Pad data to be multiple of 16 bytes (AES block size)
    
    Args:
        data: String to pad
        
    Returns:
        Padded string
    """
    length = 16 - (len(data) % 16)
    data += chr(length) * length
    return data


def encrypt(plain_text, working_key):
    """
    Encrypt plain text using CCAvenue working key
    
    Args:
        plain_text: Plain text string to encrypt
        working_key: CCAvenue working key
        
    Returns:
        Hex-encoded encrypted string
    """
    # Fixed IV as per CCAvenue specification
    iv = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
    
    # Pad the plain text
    padded_text = pad(plain_text)
    
    # Create MD5 hash of working key
    enc_digest = hashlib.md5()
    enc_digest.update(working_key.encode('utf-8'))
    
    # Create AES cipher with MD5 hash as key
    enc_cipher = AES.new(enc_digest.digest(), AES.MODE_CBC, iv)
    
    # Encrypt and convert to hex
    encrypted_text = enc_cipher.encrypt(padded_text.encode('utf-8'))
    return encrypted_text.hex()


def decrypt(cipher_text, working_key):
    """
    Decrypt cipher text using CCAvenue working key
    
    Args:
        cipher_text: Hex-encoded encrypted string
        working_key: CCAvenue working key
        
    Returns:
        Decrypted string
    """
    # Fixed IV as per CCAvenue specification
    iv = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
    
    # Create MD5 hash of working key
    dec_digest = hashlib.md5()
    dec_digest.update(working_key.encode('utf-8'))
    
    # Convert hex string to bytes
    encrypted_text = bytes.fromhex(cipher_text)
    
    # Create AES cipher with MD5 hash as key
    dec_cipher = AES.new(dec_digest.digest(), AES.MODE_CBC, iv)
    
    # Decrypt
    decrypted_text = dec_cipher.decrypt(encrypted_text)
    
    # Remove PKCS7 padding (last byte indicates padding length)
    # Padding length should be between 1 and 16
    padding_length = decrypted_text[-1]
    if 1 <= padding_length <= 16:
        decrypted_text = decrypted_text[:-padding_length]
    # If padding is invalid, try to decode anyway (some responses might not have proper padding)
    
    return decrypted_text.decode('utf-8', errors='ignore')

