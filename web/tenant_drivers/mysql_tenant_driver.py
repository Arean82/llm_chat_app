# saas/tenant_drivers/mysql_tenant_driver.py
"""
MySQL/MariaDB Tenant Driver (Phase 10.2)
Implements BaseTenantDriver using PyMySQL for enterprise scaling.
Compatible with MySQL 8.x, MariaDB 10.x, and TiDB.
Requires: pip install pymysql
"""

import hashlib
from web.tenant_drivers.base_tenant_driver import BaseTenantDriver


class MySQLTenantDriver(BaseTenantDriver):
    """
    Concrete MySQL implementation of the SaaS tenant database.
    Uses pymysql with parameterized queries and InnoDB row-level locking.
    """

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.conn_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "cursorclass": None  # Will be set dynamically
        }
        self.init_db()

    def get_connection(self):
        import pymysql
        import pymysql.cursors
        conn = pymysql.connect(
            host=self.conn_params["host"],
            port=self.conn_params["port"],
            user=self.conn_params["user"],
            password=self.conn_params["password"],
            database=self.conn_params["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn

    def init_db(self):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            # 1. Core Users Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    api_key VARCHAR(255) UNIQUE NOT NULL,
                    key_type ENUM('byok', 'admin_funded') NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active',
                    settings_blob TEXT DEFAULT '{}'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 2. Usage Accounting Ledger
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_usage (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    date DATE DEFAULT (CURRENT_DATE),
                    prompt_tokens INT DEFAULT 0,
                    completion_tokens INT DEFAULT 0,
                    total_tokens INT DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            cur.execute("CREATE INDEX idx_user_api_key ON users(api_key)")

            # 3. Public Orbit Sharing
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shared_orbits (
                    share_hash VARCHAR(64) PRIMARY KEY,
                    user_id INT NOT NULL,
                    conversation_data LONGTEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 4. BYOK Tenant Credentials
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tenant_credentials (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    provider VARCHAR(255) NOT NULL,
                    api_key TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uniq_user_provider (user_id, provider),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 5. L2 Chunk Cache (Phase 9)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunk_cache (
                    chunk_hash VARCHAR(128) PRIMARY KEY,
                    user_id INT NOT NULL,
                    chunk_text LONGTEXT NOT NULL,
                    embedding_blob LONGTEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 6. L3 Semantic Query Cache (Phase 9)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS semantic_query_cache (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    query_text TEXT NOT NULL,
                    response_text LONGTEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # Phase 9 Indexes (ignore if already exists)
            try:
                cur.execute("CREATE INDEX idx_chunk_cache_user ON chunk_cache(user_id)")
            except Exception:
                pass
            try:
                cur.execute("CREATE INDEX idx_semantic_cache_lookup ON semantic_query_cache(user_id)")
            except Exception:
                pass
            conn.commit()

            # SEED DEFAULT SUPER ADMIN
            cur.execute("SELECT COUNT(*) as cnt FROM users")
            if cur.fetchone()['cnt'] == 0:
                admin_hash = BaseTenantDriver.hash_password("admin")
                try:
                    cur.execute("""
                        INSERT INTO users (username, email, password_hash, api_key, key_type)
                        VALUES (%s, %s, %s, %s, %s)
                    """, ("admin", "admin@synora-studio.local", admin_hash, "admin_master_passport", "admin_funded"))
                    conn.commit()
                    print(f"===========================================================")
                    print(f"[SECURITY NOTIFICATION]: Default Super Admin Provisioned (MySQL)")
                    print(f"Username: admin")
                    print(f"Password: admin")
                    print(f"===========================================================")
                except Exception as e:
                    conn.rollback()
                    print(f"[SQL Warning]: Super Admin provisioning aborted: {e}")
        except Exception as e:
            conn.rollback()
            # Silently pass on duplicate index errors
            if "Duplicate" not in str(e):
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
                VALUES (%s, %s, %s, %s, %s)
            """, (username, email, pw_hash, api_key.strip(), key_type))
            conn.commit()
            return cur.lastrowid, None
        except Exception as e:
            conn.rollback()
            err_msg = str(e).lower()
            if "username" in err_msg or "duplicate" in err_msg:
                return None, "Username or email already taken."
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
            return cur.fetchone()
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
            res = cur.fetchone()
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
            return False, f"Profile Synchronization Error: {str(e)}"
        finally:
            conn.close()

    def get_user_settings(self, user_id: int) -> dict:
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT settings_blob FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row and row.get('settings_blob'):
                import json
                try:
                    return json.loads(row['settings_blob'])
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
                    INSERT INTO tenant_credentials (user_id, provider, api_key)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE api_key = VALUES(api_key), updated_at = CURRENT_TIMESTAMP
                """, (user_id, provider, BaseTenantDriver.encrypt_byok(api_key)))
            conn.commit()
        finally:
            conn.close()

    def get_tenant_credentials(self, user_id: int) -> dict:
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT provider, api_key FROM tenant_credentials WHERE user_id = %s", (user_id,))
            return {row['provider']: BaseTenantDriver.decrypt_byok(row['api_key']) for row in cur.fetchall()}
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
            return cur.fetchall()
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
            agg = cur.fetchone() or {"total_prompt": 0, "total_completion": 0}
            cur.execute("""
                SELECT date, SUM(total_tokens) as daily_total
                FROM user_usage
                GROUP BY date
                ORDER BY date DESC LIMIT 7
            """)
            daily = cur.fetchall()
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
            return cur.fetchone()
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
                    return json.loads(row['embedding_blob'])
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
                ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id), chunk_text = VALUES(chunk_text), embedding_blob = VALUES(embedding_blob)
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
                c_tokens = set(re.findall(r'\w+', row['query_text'].lower()))
                if not c_tokens: continue
                union = q_tokens.union(c_tokens)
                if not union: continue
                similarity = len(q_tokens.intersection(c_tokens)) / len(union)
                if similarity > 0.85 and similarity > highest_sim:
                    highest_sim = similarity
                    best_match = row['response_text']
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
