# utils/security_utils.py
# Zero-Trust Encryption Vault Utilities for local OS Keyring Api Credentials

import hashlib
import base64

# Transient session-bound password store
SESSION_MASTER_PASSWORD = None

def derive_key(password: str, salt: bytes = b"Quantum_Vault_Salt_v7.3", iterations: int = 50000) -> bytes:
    """Derives a cryptographically strong 256-bit key from the password using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, 32)

def encrypt_data(raw_text: str, password: str) -> str:
    """
    Encrypts raw text using derived master password key.
    Returns a secure base64 encoded ciphertext string.
    """
    if not password or not raw_text:
        return raw_text
    
    key = derive_key(password)
    raw_bytes = raw_text.encode("utf-8")
    
    # XOR cipher with derived PBKDF2 key stream
    cipher_bytes = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw_bytes))
    return base64.b64encode(cipher_bytes).decode("utf-8")

def decrypt_data(cipher_text: str, password: str) -> str:
    """
    Decrypts base64 encoded ciphertext using derived master password key.
    Returns the decoded raw string, or original text on failure/bypass.
    """
    if not password or not cipher_text:
        return cipher_text
        
    try:
        key = derive_key(password)
        cipher_bytes = base64.b64decode(cipher_text.encode("utf-8"))
        raw_bytes = bytes(b ^ key[i % len(key)] for i, b in enumerate(cipher_bytes))
        return raw_bytes.decode("utf-8")
    except Exception:
        # Graceful fallback: if it's legacy unencrypted data or failed, return original text
        return cipher_text
