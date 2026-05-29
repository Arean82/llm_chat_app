# saas/tenant_db.py
"""
SaaS Multi-Tenant Database Factory Manager (Phase 10.2 Refactor)
Acts as a switchboard that dynamically loads the correct tenant driver
based on config.ini settings. Downstream callers never need to change.

Supported backends:
  - turso   (default) — Turso/libSQL via local sqlite3 with WAL
  - postgres          — PostgreSQL via psycopg2
  - mysql             — MySQL/MariaDB/TiDB via pymysql
"""

import os
import configparser
from pathlib import Path


def _load_tenant_config() -> dict:
    """
    Reads the [TENANT_DB] section from saas/config.ini.
    Returns a dict with at minimum {'driver': 'turso'}.
    """
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent / "config.ini"
    if config_path.exists():
        config.read(str(config_path))
    
    result = {
        "driver": "turso",
        "db_name": "saas_tenants.db",
    }
    
    if config.has_section("TENANT_DB"):
        result["driver"] = config.get("TENANT_DB", "driver", fallback="turso").strip().lower()
        result["db_name"] = config.get("TENANT_DB", "db_name", fallback="saas_tenants.db").strip()
        # PostgreSQL
        result["pg_connection_string"] = config.get("TENANT_DB", "pg_connection_string", fallback="").strip()
        # MySQL
        result["mysql_host"] = config.get("TENANT_DB", "mysql_host", fallback="127.0.0.1").strip()
        result["mysql_port"] = config.getint("TENANT_DB", "mysql_port", fallback=3306)
        result["mysql_user"] = config.get("TENANT_DB", "mysql_user", fallback="root").strip()
        result["mysql_password"] = config.get("TENANT_DB", "mysql_password", fallback="").strip()
        result["mysql_database"] = config.get("TENANT_DB", "mysql_database", fallback="saas_tenants").strip()
    
    return result


class TenantDatabaseManager:
    """
    Factory switchboard for the SaaS tenant database.
    
    Reads config.ini [TENANT_DB] section to determine which backend to use.
    Delegates ALL method calls to the underlying concrete driver instance.
    
    Usage (unchanged from before):
        db = TenantDatabaseManager()
        user = db.authenticate_by_passport("my_api_key")
    """
    
    _instance = None
    _driver = None
    
    def __new__(cls, db_name=None):
        """Singleton pattern — reuse the same driver across all callers."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._driver = cls._create_driver(db_name)
        return cls._instance
    
    @classmethod
    def _create_driver(cls, db_name_override=None):
        """Factory method that instantiates the correct driver based on config."""
        config = _load_tenant_config()
        driver_type = config["driver"]
        
        if driver_type == "postgres":
            conn_str = config.get("pg_connection_string", "")
            if not conn_str:
                raise ValueError("[TENANT_DB] driver=postgres requires pg_connection_string in config.ini")
            from web.tenant_drivers.postgres_tenant_driver import PostgresTenantDriver
            print(f"[TenantDB Factory] Loading PostgreSQL driver...")
            return PostgresTenantDriver(conn_str)
        
        elif driver_type == "mysql":
            from web.tenant_drivers.mysql_tenant_driver import MySQLTenantDriver
            print(f"[TenantDB Factory] Loading MySQL driver...")
            return MySQLTenantDriver(
                host=config.get("mysql_host", "127.0.0.1"),
                port=config.get("mysql_port", 3306),
                user=config.get("mysql_user", "root"),
                password=config.get("mysql_password", ""),
                database=config.get("mysql_database", "saas_tenants")
            )
        
        else:
            # Default: Turso/libSQL (backward compatible)
            from web.tenant_drivers.turso_tenant_driver import TursoTenantDriver
            name = db_name_override or config.get("db_name", "saas_tenants.db")
            return TursoTenantDriver(db_name=name)
    
    @classmethod
    def reset_instance(cls):
        """Force re-creation of the singleton (useful after config changes or migration)."""
        cls._instance = None
        cls._driver = None
    
    # --- DELEGATE ALL METHOD CALLS TO THE UNDERLYING DRIVER ---
    
    def __getattr__(self, name):
        """
        Magic delegation: any method call on TenantDatabaseManager that isn't
        defined here is forwarded to the underlying concrete driver.
        This ensures 100% backward compatibility with all existing callers.
        """
        return getattr(self._driver, name)
    
    # --- STATIC HELPERS (remain on the manager for backward compat) ---
    
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

    @staticmethod
    def get_user_workspace(user_id: int) -> dict:
        """
        Generates absolute sandboxed storage partitions enforced by user isolation guidelines.
        This is filesystem-based and shared across all drivers.
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
