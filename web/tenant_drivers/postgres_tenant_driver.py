# saas/tenant_drivers/postgres_tenant_driver.py
"""
PostgreSQL Tenant Driver (Phase 10.2)
Implements BaseTenantDriver using psycopg2 for enterprise MVCC row-level locking.
"""

import hashlib
from web.tenant_drivers.base_tenant_driver import BaseTenantDriver


class PostgresTenantDriver(BaseTenantDriver):
    """
    Concrete PostgreSQL implementation of the SaaS tenant database.
    Uses psycopg2 with strict parameterized queries for security.
    Requires: pip install psycopg2-binary
    """

    def __init__(self, connection_string: str):
        """
        Args:
            connection_string: PostgreSQL DSN, e.g. 'postgresql://user:pass@host:5432/dbname'
        """
        self.connection_string = connection_string
        self.init_db()

    def get_connection(self):
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(self.connection_string)
        conn.autocommit = False
        return conn

    def _fetchone_dict(self, cursor):
        """Convert a psycopg2 row to dict."""
        if cursor.description is None:
            return None
        cols = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        if row:
            return dict(zip(cols, row))
        return None

    def _fetchall_dict(self, cursor):
        """Convert all psycopg2 rows to list of dicts."""
        if cursor.description is None:
            return []
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def init_db(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            # 1. Core Users Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    key_type TEXT NOT NULL CHECK (key_type IN ('byok', 'admin_funded')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    settings_blob TEXT DEFAULT '{}'
                )
            """)

            # 2. Usage Accounting Ledger
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    date DATE DEFAULT CURRENT_DATE,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0
                )
            """)

            cur.execute("CREATE INDEX IF NOT EXISTS idx_user_api_key ON users(api_key);")

            # 3. Public Orbit Sharing
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shared_orbits (
                    share_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    conversation_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. BYOK Tenant Credentials
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tenant_credentials (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, provider)
                )
            """)

            # 5. L2 Chunk Cache (Phase 9)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunk_cache (
                    chunk_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    chunk_text TEXT NOT NULL,
                    embedding_blob TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. L3 Semantic Query Cache (Phase 9)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS semantic_query_cache (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    query_text TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("CREATE INDEX IF NOT EXISTS idx_chunk_cache_user ON chunk_cache(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_semantic_cache_lookup ON semantic_query_cache(user_id, query_text);")
            
            # 7. Hermes Agent Integration Tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_instances (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                    agent_name TEXT DEFAULT 'Hermes',
                    status TEXT DEFAULT 'stopped',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    memory_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_skills (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    skill_name TEXT NOT NULL,
                    skill_code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            # SEED DEFAULT SUPER ADMIN
            cur.execute("SELECT COUNT(*) FROM users")
            if cur.fetchone()[0] == 0:
                admin_hash = BaseTenantDriver.hash_password("admin")
                try:
                    cur.execute("""
                        INSERT INTO users (username, email, password_hash, api_key, key_type)
                        VALUES (%s, %s, %s, %s, %s)
                    """, ("admin", "admin@synora-studio.local", admin_hash, "admin_master_passport", "admin_funded"))
                    conn.commit()
                    print(f"===========================================================")
                    print(f"[SECURITY NOTIFICATION]: Default Super Admin Provisioned (PostgreSQL)")
                    print(f"Username: admin")
                    print(f"Password: admin")
                    print(f"===========================================================")
                except Exception as e:
                    conn.rollback()
                    print(f"[SQL Warning]: Super Admin provisioning aborted: {e}")
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # --- CORE MULTI-TENANT GATEWAYS ---

    def register_user(self, api_key: str, username: str, email: str, password: str, key_type: str = "byok"):
        pw_hash = self.hash_password(password)
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (username, email, password_hash, api_key, key_type)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, (username, email, pw_hash, api_key.strip(), key_type))
            row = cur.fetchone()
            conn.commit()
            return row[0], None
        except Exception as e:
            conn.rollback()
            err_msg = str(e).lower()
            if "username" in err_msg:
                return None, "Username already taken."
            if "email" in err_msg:
                return None, "Email already registered."
            if "api_key" in err_msg:
                return None, "This API Key Passport has already been registered."
            return None, f"Database Error: {str(e)}"
        finally:
            conn.close()

    def authenticate_by_passport(self, api_key: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, email, api_key, key_type, status FROM users 
                WHERE api_key = %s AND status = 'active'
            """, (api_key.strip(),))
            return self._fetchone_dict(cur)
        finally:
            conn.close()

    def authenticate_by_login(self, username_or_email: str, password_raw: str):
        pw_hash = self.hash_password(password_raw)
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, email, api_key, key_type, status FROM users 
                WHERE (username = %s OR email = %s) AND password_hash = %s AND status = 'active'
            """, (username_or_email, username_or_email, pw_hash))
            res = self._fetchone_dict(cur)
            if res:
                res['passport_token'] = res.get('api_key', '')
            return res
        finally:
            conn.close()

    def update_user_profile(self, user_id: int, username: str = None, password_raw: str = None, api_key: str = None):
        updates = []
        params = []
        if username:
            updates.append("username = %s")
            params.append(username.strip())
        if password_raw:
            updates.append("password_hash = %s")
            params.append(self.hash_password(password_raw))
        if api_key:
            updates.append("api_key = %s")
            params.append(api_key.strip())
        if not updates:
            return True, "No updates required."
        params.append(user_id)
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            conn.commit()
            return True, "Security parameters synced successfully."
        except Exception as e:
            conn.rollback()
            err_msg = str(e).lower()
            if "username" in err_msg:
                return False, "This Display Name has already been claimed by another pilot."
            if "api_key" in err_msg:
                return False, "This API Key Passport is already bound to an active tenant space."
            return False, f"Profile Synchronization Error: {str(e)}"
        finally:
            conn.close()

    def get_user_settings(self, user_id: int) -> dict:
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT settings_blob FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row and row[0]:
                import json
                try:
                    return json.loads(row[0])
                except Exception:
                    pass
            return {}
        finally:
            conn.close()

    def update_user_settings(self, user_id: int, settings: dict):
        import json
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET settings_blob = %s WHERE id = %s", (json.dumps(settings), user_id))
            conn.commit()
            return True
        finally:
            conn.close()

    # --- LEDGER RECORDING ---

    def record_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        total = prompt_tokens + completion_tokens
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE user_usage 
                SET prompt_tokens = prompt_tokens + %s, 
                    completion_tokens = completion_tokens + %s,
                    total_tokens = total_tokens + %s
                WHERE user_id = %s AND date = CURRENT_DATE
            """, (prompt_tokens, completion_tokens, total, user_id))
            if cur.rowcount == 0:
                cur.execute("""
                    INSERT INTO user_usage (user_id, prompt_tokens, completion_tokens, total_tokens)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, prompt_tokens, completion_tokens, total))
            conn.commit()
        finally:
            conn.close()

    def log_api_usage(self, user_id: int, prompt_tokens: int, completion_tokens: int):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_usage (user_id, prompt_tokens, completion_tokens, total_tokens)
                VALUES (%s, %s, %s, %s)
            """, (user_id, prompt_tokens, completion_tokens, prompt_tokens + completion_tokens))
            conn.commit()
        finally:
            conn.close()

    def set_tenant_credential(self, user_id: int, provider: str, api_key: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            if not api_key:
                cur.execute("DELETE FROM tenant_credentials WHERE user_id = %s AND provider = %s", (user_id, provider))
            else:
                cur.execute("""
                    INSERT INTO tenant_credentials (user_id, provider, api_key, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, provider) DO UPDATE SET
                    api_key=EXCLUDED.api_key, updated_at=CURRENT_TIMESTAMP
                """, (user_id, provider, BaseTenantDriver.encrypt_byok(api_key)))
            conn.commit()
        finally:
            conn.close()

    def get_tenant_credentials(self, user_id: int) -> dict:
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT provider, api_key FROM tenant_credentials WHERE user_id = %s", (user_id,))
            return {row[0]: BaseTenantDriver.decrypt_byok(row[1]) for row in cur.fetchall()}
        finally:
            conn.close()

    # --- ADMIN ROUTINES ---

    def reset_admin_account(self, new_password="admin"):
        admin_hash = self.hash_password(new_password)
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = 'admin'")
            row = cur.fetchone()
            if row:
                cur.execute("""
                    UPDATE users 
                    SET password_hash = %s, api_key = 'admin_master_passport', email = 'admin@synora-studio.local', key_type = 'admin_funded', status = 'active'
                    WHERE username = 'admin'
                """, (admin_hash,))
            else:
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, api_key, key_type, status)
                    VALUES ('admin', 'admin@synora-studio.local', %s, 'admin_master_passport', 'admin_funded', 'active')
                """, (admin_hash,))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_all_tenants(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.id, u.username, u.email, u.key_type, u.created_at, u.status,
                       COALESCE(SUM(uu.total_tokens), 0) as total_tokens
                FROM users u
                LEFT JOIN user_usage uu ON u.id = uu.user_id
                GROUP BY u.id, u.username, u.email, u.key_type, u.created_at, u.status
                ORDER BY u.id DESC
            """)
            return self._fetchall_dict(cur)
        finally:
            conn.close()

    def update_user_status(self, user_id: int, status: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_global_usage(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    SUM(prompt_tokens) as total_prompt, 
                    SUM(completion_tokens) as total_completion 
                FROM user_usage
            """)
            agg = self._fetchone_dict(cur) or {"total_prompt": 0, "total_completion": 0}
            cur.execute("""
                SELECT date, SUM(total_tokens) as daily_total
                FROM user_usage
                GROUP BY date
                ORDER BY date DESC LIMIT 7
            """)
            daily = self._fetchall_dict(cur)
            return {"aggregate": agg, "daily_trend": daily}
        finally:
            conn.close()

    # --- SHARING NODE ---

    def create_share_link(self, user_id: int, conversation_data: str) -> str:
        import datetime as dt
        share_hash = hashlib.sha256((str(user_id) + str(dt.datetime.now().timestamp())).encode('utf-8')).hexdigest()[:16]
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO shared_orbits (share_hash, user_id, conversation_data)
                VALUES (%s, %s, %s)
            """, (share_hash, user_id, conversation_data))
            conn.commit()
            return share_hash
        finally:
            conn.close()

    def get_shared_orbit(self, share_hash: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM shared_orbits WHERE share_hash = %s", (share_hash,))
            return self._fetchone_dict(cur)
        finally:
            conn.close()

    # --- PHASE 9: SEMANTIC CACHE WAREHOUSING ---

    def get_cached_embedding(self, chunk_hash: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT embedding_blob FROM chunk_cache WHERE chunk_hash = %s", (chunk_hash,))
            row = cur.fetchone()
            if row:
                import json
                try:
                    return json.loads(row[0])
                except Exception:
                    pass
            return None
        finally:
            conn.close()

    def set_cached_embedding(self, chunk_hash: str, user_id: int, text: str, vector: list):
        import json
        blob = json.dumps(vector)
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chunk_cache (chunk_hash, user_id, chunk_text, embedding_blob)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(chunk_hash) DO UPDATE SET
                user_id=EXCLUDED.user_id, chunk_text=EXCLUDED.chunk_text, embedding_blob=EXCLUDED.embedding_blob
            """, (chunk_hash, user_id, text, blob))
            conn.commit()
        finally:
            conn.close()

    def get_semantic_cache_hit(self, query_text: str, user_id: int):
        import re
        q_tokens = set(re.findall(r'\w+', query_text.lower()))
        if not q_tokens:
            return None
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT query_text, response_text FROM semantic_query_cache WHERE user_id = %s", (user_id,))
            best_match = None
            highest_sim = 0.0
            for row in cur.fetchall():
                c_tokens = set(re.findall(r'\w+', row[0].lower()))
                if not c_tokens: continue
                union = q_tokens.union(c_tokens)
                if not union: continue
                similarity = len(q_tokens.intersection(c_tokens)) / len(union)
                if similarity > 0.85 and similarity > highest_sim:
                    highest_sim = similarity
                    best_match = row[1]
            return best_match
        finally:
            conn.close()

    def set_semantic_cache_hit(self, query_text: str, user_id: int, response_text: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO semantic_query_cache (user_id, query_text, response_text)
                VALUES (%s, %s, %s)
            """, (user_id, query_text, response_text))
            conn.commit()
        finally:
            conn.close()

    def clear_tenant_cache(self, user_id: int):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM chunk_cache WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM semantic_query_cache WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # --- HERMES AGENT INTEGRATION ---

    def get_agent_instance(self, user_id: int):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM agent_instances WHERE user_id = %s", (user_id,))
            return self._fetchone_dict(cur)
        finally:
            conn.close()

    def update_agent_instance(self, user_id: int, agent_name: str, status: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO agent_instances (user_id, agent_name, status, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET 
                agent_name=EXCLUDED.agent_name, status=EXCLUDED.status, updated_at=CURRENT_TIMESTAMP
            """, (user_id, agent_name, status))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_agent_memory(self, user_id: int):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM agent_memory WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            return self._fetchall_dict(cur)
        finally:
            conn.close()

    def add_agent_memory(self, user_id: int, memory_text: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO agent_memory (user_id, memory_text)
                VALUES (%s, %s)
            """, (user_id, memory_text))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_agent_skills(self, user_id: int):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM agent_skills WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            return self._fetchall_dict(cur)
        finally:
            conn.close()

    def add_agent_skill(self, user_id: int, skill_name: str, skill_code: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO agent_skills (user_id, skill_name, skill_code)
                VALUES (%s, %s, %s)
            """, (user_id, skill_name, skill_code))
            conn.commit()
            return True
        finally:
            conn.close()
