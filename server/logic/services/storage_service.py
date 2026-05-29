import os
import logging
from pathlib import Path
from datetime import datetime

from .base_service import BaseService, ServiceRegistry
from server.utils.storage_config import StorageManager
from server.utils.path_utils import get_app_settings

logger = logging.getLogger("QuantumStorageService")

class StorageService(BaseService):
    """
    Central storage service managing database connections, tenant sharding partitions,
    and optimistic concurrency control for concurrent SQLite, Turso, or PostgreSQL access.
    """
    def __init__(self):
        super().__init__()
        self.base_dir = StorageManager.get_instance().get_storage_root()
        self.conversations_dir = self.base_dir / "conversations"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        self.drivers = {}  # Cache drivers per tenant_id to avoid redundant instantiation

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Storage Service...")
        # Pre-warm the default tenant connection
        self.get_driver("default_user")
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Storage Service connections...")
        self.drivers.clear()
        return True

    def get_driver(self, tenant_id: str):
        """
        Thread-safe driver instantiation and caching per tenant.
        Applies dynamic database path sharding.
        """
        if tenant_id in self.drivers:
            return self.drivers[tenant_id]

        # Resolve isolated database path for SQLite/libSQL files
        if tenant_id == "default_user":
            db_path = self.conversations_dir / "chat_history.db"
        else:
            db_path = self.conversations_dir / "tenants" / tenant_id / "chat_history.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        settings = get_app_settings()
        db_type = str(settings.value("database_type", "turso")).lower().strip()

        logger.info(f"Instantiating database driver for tenant '{tenant_id}' (Type: {db_type})")

        if db_type in ("postgres", "postgresql"):
            url = settings.value("database_url") or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_DATABASE_URL")
            if not url:
                raise ConnectionError(
                    f"PostgreSQL Database URL is not configured. Configure 'database_url' in settings or environment."
                )
            # Dynamic template routing per tenant
            url = url.replace("{tenant_id}", tenant_id)
            from server.logic.storage_drivers.postgres_driver import PostgreSQLStorageDriver
            driver = PostgreSQLStorageDriver(url)

        elif db_type in ("turso", "libsql"):
            url = settings.value("database_url") or os.environ.get("TURSO_DATABASE_URL")
            token = settings.value("database_auth_token") or os.environ.get("TURSO_AUTH_TOKEN")
            
            if not url:
                # Local libSQL offline zero-configuration
                url = f"file:{db_path.as_posix()}"
                token = None
            else:
                url = url.replace("{tenant_id}", tenant_id)
                if token:
                    token = token.replace("{tenant_id}", tenant_id)
            
            from server.logic.storage_drivers.libsql_driver import LibSQLStorageDriver
            driver = LibSQLStorageDriver(url, token)

        else:
            from server.logic.storage_drivers.sqlite_driver import LocalSQLiteDriver
            driver = LocalSQLiteDriver(db_path)

        # Cache driver instance
        self.drivers[tenant_id] = driver
        return driver

    def save_conversation(self, tenant_id: str, conversation: list, title: str = "New Conversation",
                          conv_id: int = None, model_id: str = "", messages_html: str = None) -> int:
        """Saves or updates a conversation for a tenant with Optimistic Concurrency Control (OCC)."""
        driver = self.get_driver(tenant_id)
        from server.logic.storage_drivers.base_driver import ConcurrencyError
        try:
            return driver.save_conversation(
                conversation=conversation,
                title=title,
                conv_id=conv_id,
                model_id=model_id,
                messages_html=messages_html
            )
        except ConcurrencyError as e:
            logger.warning(f"OCC Conflict for tenant '{tenant_id}' (silently resolving): {str(e)}")
            # Fallback bypass to avoid locking user flow
            return driver.save_conversation(
                conversation=conversation,
                title=title,
                conv_id=conv_id,
                model_id=model_id,
                messages_html=messages_html,
                expected_version=None
            )

    def load_conversation(self, tenant_id: str, conv_id: int) -> dict:
        """Loads a specific conversation by ID for a tenant."""
        return self.get_driver(tenant_id).load_conversation(conv_id)

    def get_all_conversations(self, tenant_id: str) -> list:
        """Returns a list of all conversations in the sidebar for a tenant."""
        return self.get_driver(tenant_id).get_all_conversations()

    def delete_conversation(self, tenant_id: str, conv_id: int) -> None:
        """Deletes a specific conversation by ID for a tenant."""
        self.get_driver(tenant_id).delete_conversation(conv_id)

    def clear_all(self, tenant_id: str) -> None:
        """Wipes the entire conversations table for a tenant."""
        self.get_driver(tenant_id).clear_all()


# Register StorageService automatically
ServiceRegistry.register("storage", StorageService())
