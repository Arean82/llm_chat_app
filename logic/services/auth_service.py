import logging
import datetime
import hashlib
from .base_service import BaseService, ServiceRegistry
from saas.tenant_db import TenantDatabaseManager

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


# Register AuthService automatically
ServiceRegistry.register("auth", AuthService())
