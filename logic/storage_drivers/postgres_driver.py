# logic/storage_drivers/postgres_driver.py
import json
import threading
import queue
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from logic.storage_drivers.base_driver import BaseStorageDriver, ConcurrencyError


class PostgreSQLConnectionPool:
    """
    A lightweight, thread-safe connection pool for pg8000.
    Maintains a bounded queue of reusable connections to prevent socket exhaustion
    under heavy concurrent load from multiple SaaS tenant threads.
    """

    def __init__(self, url: str, max_connections: int = 10):
        """
        Args:
            url (str): PostgreSQL connection URL.
            max_connections (int): Maximum number of pooled connections.
        """
        self._url = url
        self._max_connections = max_connections
        self._pool = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._created_count = 0

    def _create_connection(self):
        """Creates a fresh pg8000 connection from the URL."""
        import pg8000.dbapi
        parsed = urlparse(self._url)
        user = parsed.username or ""
        password = parsed.password or ""
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        database = parsed.path.lstrip('/') or "postgres"

        return pg8000.dbapi.connect(
            user=user,
            password=password,
            host=host,
            database=database,
            port=int(port)
        )

    def get_connection(self):
        """
        Returns a connection from the pool. If the pool is empty and we haven't
        hit the max, creates a new one. Otherwise blocks until one is returned.
        """
        try:
            conn = self._pool.get_nowait()
            # Validate the connection is still alive
            try:
                conn.cursor().execute("SELECT 1")
                return conn
            except Exception:
                # Dead connection, create a new one
                with self._lock:
                    self._created_count -= 1
        except queue.Empty:
            pass

        with self._lock:
            if self._created_count < self._max_connections:
                self._created_count += 1
                return self._create_connection()

        # Block until a connection is returned to the pool
        return self._pool.get(timeout=30)

    def return_connection(self, conn):
        """Returns a connection back to the pool for reuse."""
        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created_count -= 1

    def close_all(self):
        """Drains and closes all pooled connections."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        with self._lock:
            self._created_count = 0


class PostgreSQLStorageDriver(BaseStorageDriver):
    """
    Concrete PostgreSQL storage driver implementing BaseStorageDriver.
    Connects to high-concurrency remote or local PostgreSQL database engines,
    providing row-level locks and Multiversion Concurrency Control (MVCC).

    Uses a bounded connection pool to prevent socket exhaustion under heavy
    concurrent load from multiple SaaS tenant threads.
    """

    def __init__(self, url: str, pool_size: int = 10):
        """
        Initializes the PostgreSQL driver using a connection URL.

        Args:
            url (str): Connection URL (e.g., postgresql://user:password@localhost:5432/db_name).
            pool_size (int): Maximum number of pooled database connections.
        """
        self.url = url
        
        # Verify package availability dynamically
        try:
            import pg8000.dbapi
        except ImportError:
            raise ImportError(
                "[PostgreSQLStorageDriver] 'pg8000' package is required for PostgreSQL connections. "
                "Please run: pip install pg8000"
            )

        self._pool = PostgreSQLConnectionPool(url, max_connections=pool_size)
        self.init_db()

    def _get_connection(self):
        """Returns a connection from the pool."""
        return self._pool.get_connection()

    def _return_connection(self, conn):
        """Returns a connection back to the pool."""
        self._pool.return_connection(conn)

    def init_db(self) -> None:
        """
        Initializes the PostgreSQL database schema and high-speed timestamp indices.
        Includes migration for the OCC `version` column.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Create conversations schema (PostgreSQL uses SERIAL for autoincrement)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    timestamp TEXT,
                    model_id TEXT,
                    messages_json TEXT,
                    messages_html TEXT,
                    version INTEGER DEFAULT 1
                )
            ''')
            
            # Index high-traffic timestamp column to preserve sidebar speed over scale
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp);')

            # Migration check: Add version column for OCC (Phase 6.3.1)
            try:
                cursor.execute('ALTER TABLE conversations ADD COLUMN version INTEGER DEFAULT 1')
            except Exception:
                conn.rollback()

            conn.commit()
        finally:
            cursor.close()
            self._return_connection(conn)

    def save_conversation(self, conversation: list, title: str = "New Conversation", 
                          conv_id: int = None, model_id: str = "", 
                          messages_html: str = None, timestamp: str = None,
                          expected_version: int = None) -> Optional[int]:
        """
        Saves or updates a conversation thread in the PostgreSQL database.
        Supports Optimistic Concurrency Control (OCC) via the expected_version parameter.
        """
        messages_json = json.dumps(conversation)
        if not timestamp:
            timestamp = datetime.now().isoformat()
            
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if conv_id is not None:
                if expected_version is not None:
                    # OCC-protected update: only succeed if stored version matches
                    cursor.execute('''
                        UPDATE conversations 
                        SET title = %s, timestamp = %s, messages_json = %s, messages_html = %s,
                            version = version + 1
                        WHERE id = %s AND version = %s
                    ''', (title, timestamp, messages_json, messages_html, conv_id, expected_version))

                    if cursor.rowcount == 0:
                        raise ConcurrencyError(
                            f"Concurrency conflict on conversation {conv_id}: "
                            f"expected version {expected_version} but row was modified by another writer."
                        )
                else:
                    # Standard update (no OCC enforcement) — backwards compatible
                    cursor.execute('''
                        UPDATE conversations 
                        SET title = %s, timestamp = %s, messages_json = %s, messages_html = %s,
                            version = version + 1
                        WHERE id = %s
                    ''', (title, timestamp, messages_json, messages_html, conv_id))
            else:
                # Insert new conversation record and return the generated ID atomically via RETURNING
                cursor.execute('''
                    INSERT INTO conversations (title, timestamp, model_id, messages_json, messages_html, version)
                    VALUES (%s, %s, %s, %s, %s, 1)
                    RETURNING id
                ''', (title, timestamp, model_id, messages_json, messages_html))
                res = cursor.fetchone()
                if res:
                    conv_id = int(res[0])
            conn.commit()
        except ConcurrencyError:
            conn.rollback()
            raise
        finally:
            cursor.close()
            self._return_connection(conn)
            
        return conv_id

    def load_conversation(self, conv_id: int) -> Optional[dict]:
        """
        Loads a single conversation thread from the PostgreSQL database by its ID.
        Includes the OCC version number for concurrency-safe write-back operations.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT title, timestamp, model_id, messages_json, messages_html, version FROM conversations WHERE id = %s', 
                (conv_id,)
            )
            res = cursor.fetchone()
            if res:
                return {
                    "id": conv_id,
                    "title": res[0],
                    "timestamp": res[1],
                    "model_id": res[2],
                    "messages": json.loads(res[3]),
                    "messages_html": res[4],
                    "version": res[5] if res[5] is not None else 1
                }
        finally:
            cursor.close()
            self._return_connection(conn)
        return None

    def get_all_conversations(self) -> List[tuple]:
        """
        Retrieves a lightweight summary list of all conversations, ordered by most recent.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        rows = []
        try:
            cursor.execute('SELECT id, title, timestamp FROM conversations ORDER BY timestamp DESC')
            results = cursor.fetchall()
            for row in results:
                rows.append((int(row[0]), str(row[1]), str(row[2])))
        finally:
            cursor.close()
            self._return_connection(conn)
        return rows

    def delete_conversation(self, conv_id: int) -> None:
        """
        Deletes a specific conversation thread and all its history from the database by its ID.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM conversations WHERE id = %s', (conv_id,))
            conn.commit()
        finally:
            cursor.close()
            self._return_connection(conn)

    def clear_all(self) -> None:
        """
        Wipes all conversations from the database tables. Used for global cleanups.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('TRUNCATE TABLE conversations')
            conn.commit()
        finally:
            cursor.close()
            self._return_connection(conn)
