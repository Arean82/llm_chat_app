# saas/tenant_drivers/turso_tenant_driver.py
"""
Turso/libSQL Tenant Driver (Phase 10.2)
Extracted from the original saas/tenant_db.py TenantDatabaseManager.
Implements BaseTenantDriver using local sqlite3 connections with WAL mode.
"""

import os
import sqlite3
import datetime
import hashlib
from pathlib import Path
from web.tenant_drivers.base_tenant_driver import BaseTenantDriver
from server.utils.storage_config import StorageManager


class TursoTenantDriver(BaseTenantDriver):
    """
    Concrete Turso/libSQL implementation of the SaaS tenant database.
    Uses local sqlite3 with WAL mode for high-occupancy concurrency.
    """

    def __init__(self, db_name="saas_tenants.db"):
        storage_root = StorageManager.get_instance().get_storage_root()
        self.db_path = storage_root / "data" / db_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self):
        """Establish atomic connection with robust busy_timeouts for concurrency safety."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Generates normalized relational schemas tracking user sandboxes."""
        with self.get_connection() as conn:
            # 1. Core Users Table
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

            # 2. Usage Accounting Ledger
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

            # 2.5 Migration: Add settings_blob if missing
            try:
                conn.execute("ALTER TABLE users ADD COLUMN settings_blob TEXT DEFAULT '{}'")
            except sqlite3.OperationalError:
                pass

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

            # 5. L2 Chunk Cache (Phase 9)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunk_cache (
                    chunk_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    embedding_blob BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # 6. L3 Semantic Query Cache (Phase 9)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_query_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query_text TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Phase 9 Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk_cache_user ON chunk_cache(user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_cache_lookup ON semantic_query_cache(user_id, query_text);")

            # 7. Hermes Agent Integration Tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    agent_name TEXT DEFAULT 'Hermes',
                    status TEXT DEFAULT 'stopped',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    memory_text TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    skill_name TEXT NOT NULL,
                    skill_code TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

            # 4. SEED DEFAULT SUPER ADMIN
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                admin_hash = BaseTenantDriver.hash_password("admin")
                try:
                    conn.execute("""
                        INSERT INTO users (username, email, password_hash, api_key, key_type)
                        VALUES (?, ?, ?, ?, ?)
                    """, ("admin", "admin@synora-studio.local", admin_hash, "admin_master_passport", "admin_funded"))
                    conn.commit()
                    print(f"===========================================================")
                    print(f"[SECURITY NOTIFICATION]: Default Super Admin Provisioned")
                    print(f"Username: admin")
                    print(f"Password: admin")
                    print(f"===========================================================")
                except Exception as e:
                    print(f"[SQL Warning]: Super Admin provisioning aborted: {e}")

    # --- CORE MULTI-TENANT GATEWAYS ---

    def register_user(self, api_key: str, username: str, email: str, password: str, key_type: str = "byok"):
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
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT id, username, email, api_key, key_type, status FROM users 
                WHERE api_key = ? AND status = 'active'
            """, (api_key.strip(),)).fetchone()
            if row:
                return dict(row)
            return None

    def authenticate_by_login(self, username_or_email: str, password_raw: str):
        pw_hash = self.hash_password(password_raw)
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT id, username, email, api_key, key_type, status FROM users 
                WHERE (username = ? OR email = ?) AND password_hash = ? AND status = 'active'
            """, (username_or_email, username_or_email, pw_hash)).fetchone()
            if row:
                res = dict(row)
                res['passport_token'] = res.get('api_key', '')
                return res
            return None

    def update_user_profile(self, user_id: int, username: str = None, password_raw: str = None, api_key: str = None):
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

    def get_user_settings(self, user_id: int) -> dict:
        with self.get_connection() as conn:
            row = conn.execute("SELECT settings_blob FROM users WHERE id = ?", (user_id,)).fetchone()
            if row and row['settings_blob']:
                try:
                    import json
                    return json.loads(row['settings_blob'])
                except Exception:
                    pass
            return {}

    def update_user_settings(self, user_id: int, settings: dict):
        import json
        settings_str = json.dumps(settings)
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET settings_blob = ? WHERE id = ?", (settings_str, user_id))
            conn.commit()
            return True

    # --- LEDGER RECORDING ---

    def record_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        total = prompt_tokens + completion_tokens
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE user_usage 
                SET prompt_tokens = prompt_tokens + ?, 
                    completion_tokens = completion_tokens + ?,
                    total_tokens = total_tokens + ?
                WHERE user_id = ? AND date = CURRENT_DATE
            """, (prompt_tokens, completion_tokens, total, user_id))
            if cursor.rowcount == 0:
                conn.execute("""
                    INSERT INTO user_usage (user_id, prompt_tokens, completion_tokens, total_tokens)
                    VALUES (?, ?, ?, ?)
                """, (user_id, prompt_tokens, completion_tokens, total))
            conn.commit()

    def log_api_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO user_usage (user_id, prompt_tokens, completion_tokens, total_tokens)
                VALUES (?, ?, ?, ?)
            """, (user_id, prompt_tokens, completion_tokens, prompt_tokens + completion_tokens))
            conn.commit()

    def set_tenant_credential(self, user_id: int, provider: str, api_key: str):
        with self.get_connection() as conn:
            if not api_key:
                conn.execute("DELETE FROM tenant_credentials WHERE user_id = ? AND provider = ?", (user_id, provider))
            else:
                conn.execute("""
                    INSERT INTO tenant_credentials (user_id, provider, api_key, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, provider) DO UPDATE SET
                    api_key=excluded.api_key, updated_at=CURRENT_TIMESTAMP
                """, (user_id, provider, BaseTenantDriver.encrypt_byok(api_key)))
            conn.commit()

    def get_tenant_credentials(self, user_id: int) -> dict:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT provider, api_key FROM tenant_credentials WHERE user_id = ?", (user_id,))
            return {row['provider']: BaseTenantDriver.decrypt_byok(row['api_key']) for row in cursor.fetchall()}

    # --- ADMIN ROUTINES ---

    def reset_admin_account(self, new_password="admin"):
        admin_hash = self.hash_password(new_password)
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM users WHERE username = 'admin'")
            row = cursor.fetchone()
            if row:
                conn.execute("""
                    UPDATE users 
                    SET password_hash = ?, api_key = 'admin_master_passport', email = 'admin@synora-studio.local', key_type = 'admin_funded', status = 'active'
                    WHERE username = 'admin'
                """, (admin_hash,))
            else:
                conn.execute("""
                    INSERT INTO users (username, email, password_hash, api_key, key_type, status)
                    VALUES ('admin', 'admin@synora-studio.local', ?, 'admin_master_passport', 'admin_funded', 'active')
                """, (admin_hash,))
            conn.commit()
            return True

    def get_all_tenants(self):
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
        with self.get_connection() as conn:
            conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
            conn.commit()
            return True

    def get_global_usage(self):
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    SUM(prompt_tokens) as total_prompt, 
                    SUM(completion_tokens) as total_completion 
                FROM user_usage
            """).fetchone()
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
        import datetime as dt
        share_hash = hashlib.sha256((str(user_id) + str(dt.datetime.now().timestamp())).encode('utf-8')).hexdigest()[:16]
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO shared_orbits (share_hash, user_id, conversation_data)
                VALUES (?, ?, ?)
            """, (share_hash, user_id, conversation_data))
            conn.commit()
            return share_hash

    def get_shared_orbit(self, share_hash: str):
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM shared_orbits WHERE share_hash = ?", (share_hash,)).fetchone()
            return dict(row) if row else None

    # --- PHASE 9: SEMANTIC CACHE WAREHOUSING ---

    def get_cached_embedding(self, chunk_hash: str):
        with self.get_connection() as conn:
            row = conn.execute("SELECT embedding_blob FROM chunk_cache WHERE chunk_hash = ?", (chunk_hash,)).fetchone()
            if row:
                import json
                try:
                    return json.loads(row['embedding_blob'])
                except Exception:
                    pass
            return None

    def set_cached_embedding(self, chunk_hash: str, user_id: int, text: str, vector: list):
        import json
        blob = json.dumps(vector)
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO chunk_cache (chunk_hash, user_id, chunk_text, embedding_blob)
                VALUES (?, ?, ?, ?)
            """, (chunk_hash, user_id, text, blob))
            conn.commit()

    def get_semantic_cache_hit(self, query_text: str, user_id: int):
        import re
        q_tokens = set(re.findall(r'\w+', query_text.lower()))
        if not q_tokens:
            return None
        with self.get_connection() as conn:
            rows = conn.execute("SELECT query_text, response_text FROM semantic_query_cache WHERE user_id = ?", (user_id,)).fetchall()
            best_match = None
            highest_sim = 0.0
            for row in rows:
                c_text = row['query_text']
                c_tokens = set(re.findall(r'\w+', c_text.lower()))
                if not c_tokens: continue
                union = q_tokens.union(c_tokens)
                if not union: continue
                similarity = len(q_tokens.intersection(c_tokens)) / len(union)
                if similarity > 0.85 and similarity > highest_sim:
                    highest_sim = similarity
                    best_match = row['response_text']
            return best_match

    def set_semantic_cache_hit(self, query_text: str, user_id: int, response_text: str):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO semantic_query_cache (user_id, query_text, response_text)
                VALUES (?, ?, ?)
            """, (user_id, query_text, response_text))
            conn.commit()

    def clear_tenant_cache(self, user_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM chunk_cache WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM semantic_query_cache WHERE user_id = ?", (user_id,))
            conn.commit()
            return True

    # --- HERMES AGENT INTEGRATION ---

    def get_agent_instance(self, user_id: int):
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_instances WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def update_agent_instance(self, user_id: int, agent_name: str, status: str):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO agent_instances (user_id, agent_name, status, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET 
                agent_name=EXCLUDED.agent_name, status=EXCLUDED.status, updated_at=CURRENT_TIMESTAMP
            """, (user_id, agent_name, status))
            conn.commit()
            return True

    def get_agent_memory(self, user_id: int):
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM agent_memory WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def add_agent_memory(self, user_id: int, memory_text: str):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO agent_memory (user_id, memory_text)
                VALUES (?, ?)
            """, (user_id, memory_text))
            conn.commit()
            return True

    def get_agent_skills(self, user_id: int):
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM agent_skills WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def add_agent_skill(self, user_id: int, skill_name: str, skill_code: str):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO agent_skills (user_id, skill_name, skill_code)
                VALUES (?, ?, ?)
            """, (user_id, skill_name, skill_code))
            conn.commit()
            return True
