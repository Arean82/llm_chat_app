# saas/tenant_drivers/base_tenant_driver.py
"""
Abstract Base Class (ABC) for all Tenant Database Drivers.
Mirrors the BaseStorageDriver pattern used for conversation storage.
Each concrete driver (Turso, PostgreSQL, MySQL) must implement every method.
"""

from abc import ABC, abstractmethod


class BaseTenantDriver(ABC):
    """
    Blueprint contract for all SaaS tenant database backends.
    Every method here must be implemented by concrete drivers to ensure
    seamless hot-swapping between Turso/libSQL, PostgreSQL, and MySQL.
    """

    # --- INITIALIZATION ---

    @abstractmethod
    def init_db(self):
        """Create all required tables and indexes if they do not exist."""
        pass

    @abstractmethod
    def get_connection(self):
        """Return an active database connection object."""
        pass

    # --- SECURITY & PASSWORD HELPERS ---

    @staticmethod
    def hash_password(password: str) -> str:
        """Secure SHA-256 salted password hashing routine."""
        import hashlib
        salt = "SaaS_Passport_Salt_v7_"
        return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

    @staticmethod
    def encrypt_byok(key: str) -> str:
        import base64
        return base64.b64encode(key.encode('utf-8')).decode('utf-8')

    @staticmethod
    def decrypt_byok(cipher: str) -> str:
        import base64
        try:
            return base64.b64decode(cipher.encode('utf-8')).decode('utf-8')
        except Exception:
            return cipher

    # --- CORE MULTI-TENANT GATEWAYS ---

    @abstractmethod
    def register_user(self, api_key: str, username: str, email: str, password: str, key_type: str = "byok"):
        """Provisions a new user node. Returns (user_id, error_message)."""
        pass

    @abstractmethod
    def authenticate_by_passport(self, api_key: str):
        """Looks up a user instantly by their API passport. Returns dict or None."""
        pass

    @abstractmethod
    def authenticate_by_login(self, username_or_email: str, password_raw: str):
        """Authenticates via standard web dashboard profile inputs. Returns dict or None."""
        pass

    @abstractmethod
    def update_user_profile(self, user_id: int, username: str = None, password_raw: str = None, api_key: str = None):
        """Updates user credentials safely. Returns (success: bool, message: str)."""
        pass

    @abstractmethod
    def get_user_settings(self, user_id: int) -> dict:
        """Retrieves the JSON configuration blob for the user."""
        pass

    @abstractmethod
    def update_user_settings(self, user_id: int, settings: dict):
        """Persists the JSON configuration blob for the user."""
        pass

    # --- LEDGER RECORDING ---

    @abstractmethod
    def record_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        """Logs usage block into the ledger ensuring daily consumption accounting."""
        pass

    @abstractmethod
    def log_api_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        """Records token burndown for the active billing cycle."""
        pass

    @abstractmethod
    def set_tenant_credential(self, user_id: int, provider: str, api_key: str):
        """Securely inserts or updates a BYOK LLM provider credential."""
        pass

    @abstractmethod
    def get_tenant_credentials(self, user_id: int) -> dict:
        """Retrieves all BYOK LLM provider credentials for a specific tenant."""
        pass

    # --- ADMIN ROUTINES ---

    @abstractmethod
    def reset_admin_account(self, new_password="admin"):
        """Forcefully resets the super admin account to default credentials."""
        pass

    @abstractmethod
    def get_all_tenants(self):
        """Retrieves a master roster of all provisioned accounts."""
        pass

    @abstractmethod
    def update_user_status(self, user_id: int, status: str):
        """Allows operator to instantly ban/kick or reactivate a user."""
        pass

    @abstractmethod
    def get_global_usage(self):
        """Aggregates all telemetry tokens consumed across the platform."""
        pass

    # --- SHARING NODE ---

    @abstractmethod
    def create_share_link(self, user_id: int, conversation_data: str) -> str:
        """Persists a conversational snapshot into a public hash. Returns hash string."""
        pass

    @abstractmethod
    def get_shared_orbit(self, share_hash: str):
        """Retrieves read-only conversational logs mapped to a public hash."""
        pass

    # --- PHASE 9: SEMANTIC CACHE WAREHOUSING ---

    @abstractmethod
    def get_cached_embedding(self, chunk_hash: str):
        """Retrieves a cached embedding vector for a given chunk hash, or None."""
        pass

    @abstractmethod
    def set_cached_embedding(self, chunk_hash: str, user_id: int, text: str, vector: list):
        """Stores an embedding vector keyed by its chunk hash."""
        pass

    @abstractmethod
    def get_semantic_cache_hit(self, query_text: str, user_id: int):
        """Checks if a semantically similar query exists. Returns cached response or None."""
        pass

    @abstractmethod
    def set_semantic_cache_hit(self, query_text: str, user_id: int, response_text: str):
        """Stores a query-response pair in the semantic cache."""
        pass

    @abstractmethod
    def clear_tenant_cache(self, user_id: int):
        """Purges all cached embeddings and semantic query results for a tenant."""
        pass

    # --- ISOLATION DATA ROUTING ---

    # --- HERMES AGENT INTEGRATION ---

    @abstractmethod
    def get_agent_instance(self, user_id: int):
        pass

    @abstractmethod
    def update_agent_instance(self, user_id: int, agent_name: str, status: str):
        pass

    @abstractmethod
    def get_agent_memory(self, user_id: int):
        pass

    @abstractmethod
    def add_agent_memory(self, user_id: int, memory_text: str):
        pass

    @abstractmethod
    def get_agent_skills(self, user_id: int):
        pass

    @abstractmethod
    def add_agent_skill(self, user_id: int, skill_name: str, skill_code: str):
        pass

    @staticmethod
    def get_user_workspace(user_id: int) -> dict:
        """
        Generates absolute sandboxed storage partitions enforced by user isolation guidelines.
        This is shared across all drivers since it operates on the filesystem, not the DB.
        """
        from server.utils.storage_config import StorageManager
        storage_root = StorageManager.get_instance().get_storage_root()

        conversations_dir = storage_root / "conversations" / f"user_{user_id}"
        vector_dir = storage_root / "vector_db" / "collections" / f"user_{user_id}"

        conversations_dir.mkdir(parents=True, exist_ok=True)
        vector_dir.mkdir(parents=True, exist_ok=True)

        return {
            "conversations_path": conversations_dir,
            "vector_path": vector_dir
        }
