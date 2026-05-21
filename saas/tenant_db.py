# saas/tenant_db.py
"""
SaaS Multi-Tenant SQLite Persistence Engine (Phase 6)
Governs robust, isolated multi-user account registration, 
token quota ledgers, and WAL-compliant read/write concurrency.
"""

import os
import sqlite3
import datetime
import hashlib
from pathlib import Path
from utils.storage_config import StorageManager

class TenantDatabaseManager:
    """
    Manages multi-tenant isolated SQL metadata, including security credentials,
    passport-based access gateways, and usage accounting.
    """
    def __init__(self, db_name="saas_tenants.db"):
        # Anchor SaaS DB directly inside Storage Root to maintain portability
        storage_root = StorageManager.get_instance().get_storage_root()
        self.db_path = storage_root / "data" / db_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self):
        """Establish atomic connection with robust busy_timeouts for concurrency safety."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        # Enforce WAL Mode for high-occupancy SaaS multi-user concurrency (Audit ID 006 Fix)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Generates normalized relational schemas tracking user sandboxes."""
        with self.get_connection() as conn:
            # 1. Core Users Table (Login Passport Key Integration)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    key_type TEXT NOT NULL CHECK (key_type IN ('byok', 'admin_funded')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)

            # 2. Usage Accounting Ledger (Economic Gate Limits)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date DATE DEFAULT CURRENT_DATE,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Establish Index to speed up user-token gateway lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_api_key ON users(api_key);")
            
            # 3. Public Orbit Sharing
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_orbits (
                    share_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    conversation_data TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # 4. BYOK Tenant Credentials
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, provider),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

            # 4. SEED DEFAULT SUPER ADMIN (Critical First-Run Bootloader Fix)
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                # Dynamically hash the default administrative password
                admin_hash = TenantDatabaseManager.hash_password("admin")
                try:
                    conn.execute("""
                        INSERT INTO users (username, email, password_hash, api_key, key_type)
                        VALUES (?, ?, ?, ?, ?)
                    """, ("admin", "admin@quantum-saas.local", admin_hash, "admin_master_passport", "admin_funded"))
                    conn.commit()
                    print("[SQL Seeder]: Successfully provisioned default Super Admin account (admin/admin).")
                except Exception as e:
                    print(f"[SQL Warning]: Super Admin provisioning aborted: {e}")

    # --- SECURITY & PASSWORD HELPERS ---

    @staticmethod
    def hash_password(password: str) -> str:
        """Secure SHA-256 salted password hashing routine."""
        salt = "SaaS_Passport_Salt_v7_"
        return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

    # --- CORE MULTI-TENANT GATEWAYS ---

    def register_user(self, api_key: str, username: str, email: str, password: str, key_type: str = "byok"):
        """
        Provisions a new user node.
        Ensures API validation took place prior to updating profile details.
        """
        pw_hash = self.hash_password(password)
        with self.get_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, api_key, key_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (username, email, pw_hash, api_key.strip(), key_type))
                conn.commit()
                return cursor.lastrowid, None
            except sqlite3.IntegrityError as e:
                err_msg = str(e).lower()
                if "username" in err_msg:
                    return None, "Username already taken."
                if "email" in err_msg:
                    return None, "Email already registered."
                if "api_key" in err_msg:
                    return None, "This API Key Passport has already been registered."
                return None, f"Database Error: {str(e)}"

    def authenticate_by_passport(self, api_key: str):
        """Looks up a user instantly by their API passport."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT id, username, email, api_key, key_type, status FROM users 
                WHERE api_key = ? AND status = 'active'
            """, (api_key.strip(),)).fetchone()
            
            if row:
                return dict(row)
            return None

    def authenticate_by_login(self, username_or_email: str, password_raw: str):
        """Authenticates via standard web dashboard profile inputs."""
        pw_hash = self.hash_password(password_raw)
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT id, username, email, api_key, key_type, status FROM users 
                WHERE (username = ? OR email = ?) AND password_hash = ? AND status = 'active'
            """, (username_or_email, username_or_email, pw_hash)).fetchone()
            
            if row:
                res = dict(row)
                # Explicitly map the API passport token for modern client framework injection
                res['passport_token'] = res.get('api_key', '')
                return res
            return None

    def update_user_profile(self, user_id: int, username: str = None, password_raw: str = None, api_key: str = None):
        """Updates user credentials safely in the database, supporting dynamic partial overrides."""
        updates = []
        params = []
        
        if username:
            updates.append("username = ?")
            params.append(username.strip())
            
        if password_raw:
            pw_hash = self.hash_password(password_raw)
            updates.append("password_hash = ?")
            params.append(pw_hash)
            
        if api_key:
            updates.append("api_key = ?")
            params.append(api_key.strip())
            
        if not updates:
            return True, "No updates required."
            
        params.append(user_id)
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        
        with self.get_connection() as conn:
            try:
                conn.execute(sql, tuple(params))
                conn.commit()
                return True, "Security parameters synced successfully."
            except sqlite3.IntegrityError as e:
                err_msg = str(e).lower()
                if "username" in err_msg:
                    return False, "This Display Name has already been claimed by another pilot."
                if "api_key" in err_msg:
                    return False, "This API Key Passport is already bound to an active tenant space."
                return False, f"Profile Synchronization Error: {str(e)}"

    # --- ISOLATION DATA ROUTING ---

    @staticmethod
    def get_user_workspace(user_id: int) -> dict:
        """
        Generates absolute sandboxed storage partitions enforced by user isolation guidelines.
        Guarantees physical folder isolation preventing semantic cross-contamination.
        """
        storage_root = StorageManager.get_instance().get_storage_root()
        
        # Partition A: Chat history isolation
        conversations_dir = storage_root / "conversations" / f"user_{user_id}"
        
        # Partition B: Semantic vector isolation
        vector_dir = storage_root / "vector_db" / "collections" / f"user_{user_id}"
        
        # Provision physically
        conversations_dir.mkdir(parents=True, exist_ok=True)
        vector_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "conversations_path": conversations_dir,
            "vector_path": vector_dir
        }

    # --- LEDGER RECORDING ---

    def record_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        """Logs usage block into the ledger ensuring daily consumption accounting."""
        total = prompt_tokens + completion_tokens
        with self.get_connection() as conn:
            # Attempt update first
            cursor = conn.execute("""
                UPDATE user_usage 
                SET prompt_tokens = prompt_tokens + ?, 
                    completion_tokens = completion_tokens + ?,
                    total_tokens = total_tokens + ?
                WHERE user_id = ? AND date = CURRENT_DATE
            """, (prompt_tokens, completion_tokens, total, user_id))
            
            # If no rows were updated, insert a fresh row for today
            if cursor.rowcount == 0:
                conn.execute("""
                    INSERT INTO user_usage (user_id, prompt_tokens, completion_tokens, total_tokens)
                    VALUES (?, ?, ?, ?)
                """, (user_id, prompt_tokens, completion_tokens, total))
            conn.commit()

    def log_api_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        """Records token burndown for the active billing cycle."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO user_usage (user_id, prompt_tokens, completion_tokens, total_tokens)
                VALUES (?, ?, ?, ?)
            """, (user_id, prompt_tokens, completion_tokens, prompt_tokens + completion_tokens))
            conn.commit()

    def set_tenant_credential(self, user_id: int, provider: str, api_key: str):
        """Securely inserts or updates a BYOK LLM provider credential for a specific tenant."""
        with self.get_connection() as conn:
            if not api_key:
                # If key is empty, delete the credential entry
                conn.execute("DELETE FROM tenant_credentials WHERE user_id = ? AND provider = ?", (user_id, provider))
            else:
                conn.execute("""
                    INSERT INTO tenant_credentials (user_id, provider, api_key, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, provider) DO UPDATE SET
                    api_key=excluded.api_key, updated_at=CURRENT_TIMESTAMP
                """, (user_id, provider, api_key))
            conn.commit()
            
    def get_tenant_credentials(self, user_id: int) -> dict:
        """Retrieves all BYOK LLM provider credentials for a specific tenant."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT provider, api_key FROM tenant_credentials WHERE user_id = ?", (user_id,))
            return {row['provider']: row['api_key'] for row in cursor.fetchall()}

    # --- ADMIN ROUTINES ---

    def reset_admin_account(self):
        """Forcefully resets the super admin account to default credentials."""
        admin_hash = self.hash_password("admin")
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM users WHERE username = 'admin'")
            row = cursor.fetchone()
            if row:
                conn.execute("""
                    UPDATE users 
                    SET password_hash = ?, api_key = 'admin_master_passport', email = 'admin@quantum-saas.local', key_type = 'admin_funded', status = 'active'
                    WHERE username = 'admin'
                """, (admin_hash,))
            else:
                conn.execute("""
                    INSERT INTO users (username, email, password_hash, api_key, key_type, status)
                    VALUES ('admin', 'admin@quantum-saas.local', ?, 'admin_master_passport', 'admin_funded', 'active')
                """, (admin_hash,))
            conn.commit()
            return True

    def get_all_tenants(self):
        """Retrieves a master roster of all provisioned accounts for operator analytics."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT u.id, u.username, u.email, u.key_type, u.created_at, u.status,
                       COALESCE(SUM(uu.total_tokens), 0) as total_tokens
                FROM users u
                LEFT JOIN user_usage uu ON u.id = uu.user_id
                GROUP BY u.id
                ORDER BY u.id DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def update_user_status(self, user_id: int, status: str):
        """Allows operator to instantly ban/kick or reactivate a user's web passport."""
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
            conn.commit()
            return True

    def get_global_usage(self):
        """Aggregates all telemetry tokens consumed across the platform."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    SUM(prompt_tokens) as total_prompt, 
                    SUM(completion_tokens) as total_completion 
                FROM user_usage
            """).fetchone()
            
            # Additional logic to retrieve daily graph over past 7 days
            daily = conn.execute("""
                SELECT date, SUM(total_tokens) as daily_total
                FROM user_usage
                GROUP BY date
                ORDER BY date DESC LIMIT 7
            """).fetchall()
            
            return {
                "aggregate": dict(row) if row else {"total_prompt": 0, "total_completion": 0},
                "daily_trend": [dict(d) for d in daily]
            }

    # --- SHARING NODE ---

    def create_share_link(self, user_id: int, conversation_data: str) -> str:
        """Persists a specific orbital message array into a static accessible share hash."""
        share_hash = hashlib.sha256((str(user_id) + str(datetime.datetime.now().timestamp())).encode('utf-8')).hexdigest()[:16]
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO shared_orbits (share_hash, user_id, conversation_data)
                VALUES (?, ?, ?)
            """, (share_hash, user_id, conversation_data))
            conn.commit()
            return share_hash

    def get_shared_orbit(self, share_hash: str):
        """Retrieves read-only conversational logs mapped to a public hash."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM shared_orbits WHERE share_hash = ?", (share_hash,)).fetchone()
            return dict(row) if row else None

