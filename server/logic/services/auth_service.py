import logging
import datetime
import hashlib
from .base_service import BaseService, ServiceRegistry
from web.core.tenant_db import TenantDatabaseManager

logger = logging.getLogger("QuantumAuthService")

class AuthService(BaseService):
    """
    Central authentication and sandboxed user management service.
    Orchestrates login checks, BYOK provider key registries, profile security,
    and JWT token issuance/verification lifecycles.
    """
    def __init__(self):
        super().__init__()
        self.db = None

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Authentication Service...")
        self.db = TenantDatabaseManager()
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Authentication Service...")
        self.db = None
        return True

    def authenticate_login(self, username_or_email: str, password_raw: str) -> dict:
        """Authenticate user credentials against hashed password profiles."""
        if not self.db:
            return None
        return self.db.authenticate_by_login(username_or_email, password_raw)

    def authenticate_passport(self, api_key: str) -> dict:
        """Authenticate and load user context via standard API passport token."""
        if not self.db:
            return None
        return self.db.authenticate_by_passport(api_key)

    def register_tenant(self, api_key: str, username: str, email: str, password: str, key_type: str = "byok"):
        """Register and provision a new user sandbox, verifying inputs."""
        if not self.db:
            return None, "Database not initialized"
        return self.db.register_user(api_key, username, email, password, key_type)

    def update_profile(self, user_id: int, username: str = None, password_raw: str = None, api_key: str = None):
        """Rotate security parameters (display name, keys, passwords)."""
        if not self.db:
            return False, "Database not initialized"
        return self.db.update_user_profile(user_id, username, password_raw, api_key)

    def get_tenant_keys(self, user_id: int) -> dict:
        """Fetch secure custom provider keys (BYOK credentials)."""
        if not self.db:
            return {}
        return self.db.get_tenant_credentials(user_id)

    def set_tenant_key(self, user_id: int, provider: str, api_key: str) -> bool:
        """Insert or rotate a BYOK key for a tenant."""
        if not self.db:
            return False
        try:
            self.db.set_tenant_credential(user_id, provider, api_key)
            return True
        except Exception as e:
            logger.error(f"Failed to update tenant credential for {user_id} ({provider}): {str(e)}")
            return False

    def get_user_settings(self, user_id: int) -> dict:
        """Retrieve user configuration settings JSON blob."""
        if not self.db:
            return {}
        return self.db.get_user_settings(user_id)

    def update_user_settings(self, user_id: int, settings: dict) -> bool:
        """Update and save user settings blob."""
        if not self.db:
            return False
        return self.db.update_user_settings(user_id, settings)

    def generate_token(self, user_dict: dict, expires_in: int = 86400) -> str:
        """
        Generates a cryptographically signed stateless JSON Web Token (JWT) using HMAC-SHA256.
        Avoids external dependencies like PyJWT to prevent deployment breaks.
        """
        import base64
        import json
        import hmac
        import hashlib
        import time

        def base64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

        header = {"alg": "HS256", "typ": "JWT"}
        
        # Build payload with expiration claims
        payload = {
            "id": user_dict.get("id"),
            "username": user_dict.get("username"),
            "email": user_dict.get("email"),
            "key_type": user_dict.get("key_type"),
            "exp": time.time() + expires_in
        }

        header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
        payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))
        
        signature_base = f"{header_b64}.{payload_b64}"
        
        # Cryptographic signing using master salt secret
        secret = "Quantum_SaaS_JWT_Secret_Salt_v9_SuperSecureKey"
        signature = hmac.new(
            secret.encode('utf-8'),
            signature_base.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        signature_b64 = base64url_encode(signature)
        return f"{signature_base}.{signature_b64}"

    def verify_token(self, token: str) -> dict:
        """
        Verifies a cryptographically signed JWT token signature and expiration state.
        Returns the decoded payload dict if valid, or None if expired or invalid.
        """
        import base64
        import json
        import hmac
        import hashlib
        import time

        def base64url_decode(data: str) -> bytes:
            padding = '=' * (4 - len(data) % 4)
            return base64.urlsafe_b64decode((data + padding).encode('utf-8'))

        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
                
            header_b64, payload_b64, signature_b64 = parts
            
            # Verify signature
            signature_base = f"{header_b64}.{payload_b64}"
            secret = "Quantum_SaaS_JWT_Secret_Salt_v9_SuperSecureKey"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                signature_base.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            def base64url_encode(data: bytes) -> str:
                return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
                
            expected_signature_b64 = base64url_encode(expected_signature)
            
            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return None
                
            payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
            
            # Verify expiration timestamp
            if "exp" in payload and time.time() > payload["exp"]:
                logger.warning(f"Expired JWT token presented for user '{payload.get('username')}'")
                return None
                
            return payload
        except Exception as e:
            logger.error(f"JWT Token validation failed: {str(e)}")
            return None


# Register AuthService automatically
ServiceRegistry.register("auth", AuthService())

