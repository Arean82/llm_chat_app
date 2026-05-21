# logic/storage_drivers/sqlite_driver.py
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from logic.storage_drivers.base_driver import BaseStorageDriver, ConcurrencyError

class LocalSQLiteDriver(BaseStorageDriver):
    """
    Concrete SQLite database driver implementing BaseStorageDriver.
    Handles standard file-based SQL operations on local files, enabling
    localized single-user desktop storage and isolated File-per-Tenant partitions.

    Uses thread-local connection caching to prevent sqlite3 blockages
    during simultaneous threaded writes from the Flask SaaS threads.
    """

    def __init__(self, db_path: Path):
        """
        Initializes the SQLite driver.

        Args:
            db_path (Path): Absolute filesystem path to the target SQLite .db file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Returns a thread-local cached SQLite connection.
        Each thread gets its own connection instance, preventing cross-thread
        locking contention and 'database is locked' errors from concurrent SaaS requests.
        """
        conn = getattr(self._local, 'conn', None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('PRAGMA busy_timeout=5000;')
            self._local.conn = conn
        return conn

    def close_pool(self) -> None:
        """
        Closes the thread-local connection for the current thread.
        Should be called during thread teardown or application shutdown.
        """
        conn = getattr(self._local, 'conn', None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def init_db(self) -> None:
        """
        Initializes the SQLite database tables and high-speed timestamp indices.
        Enables WAL mode dynamically for superior read concurrency and crash safety.
        Includes migration for the OCC `version` column.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enable WAL mode for high-concurrency read-write and crash resilience
            cursor.execute('PRAGMA journal_mode=WAL;')
            
            # Create conversations schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    timestamp TEXT,
                    model_id TEXT,
                    messages_json TEXT,
                    messages_html TEXT,
                    version INTEGER DEFAULT 1
                )
            ''')
            
            # Audit ID 020: Index high-traffic timestamp column to preserve sidebar speed over scale
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp);')
            
            # Migration check: Ensure messages_html column exists for older database migrations
            try:
                cursor.execute('ALTER TABLE conversations ADD COLUMN messages_html TEXT')
            except sqlite3.OperationalError:
                pass 

            # Migration check: Ensure version column exists for OCC (Phase 6.3.1)
            try:
                cursor.execute('ALTER TABLE conversations ADD COLUMN version INTEGER DEFAULT 1')
            except sqlite3.OperationalError:
                pass

            conn.commit()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Database initialization error: {e}")
        finally:
            if conn:
                conn.close()

    def save_conversation(self, conversation: list, title: str = "New Conversation", 
                          conv_id: int = None, model_id: str = "", 
                          messages_html: str = None, timestamp: str = None,
                          expected_version: int = None) -> Optional[int]:
        """
        Saves or updates a conversation thread in the SQLite database.
        Supports Optimistic Concurrency Control (OCC) via the expected_version parameter.
        """
        messages_json = json.dumps(conversation)
        if not timestamp:
            timestamp = datetime.now().isoformat()
        conn = None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if conv_id is not None:
                if expected_version is not None:
                    # OCC-protected update: only succeed if stored version matches
                    cursor.execute('''
                        UPDATE conversations 
                        SET title = ?, timestamp = ?, messages_json = ?, messages_html = ?,
                            version = version + 1
                        WHERE id = ? AND version = ?
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
                        SET title = ?, timestamp = ?, messages_json = ?, messages_html = ?,
                            version = version + 1
                        WHERE id = ?
                    ''', (title, timestamp, messages_json, messages_html, conv_id))
            else:
                # Insert new conversation record (version starts at 1 by default)
                cursor.execute('''
                    INSERT INTO conversations (title, timestamp, model_id, messages_json, messages_html, version)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (title, timestamp, model_id, messages_json, messages_html))
                conv_id = cursor.lastrowid

            conn.commit()
        except ConcurrencyError:
            # Re-raise OCC errors without masking them
            raise
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Save error: {e}")
        return conv_id

    def load_conversation(self, conv_id: int) -> Optional[dict]:
        """
        Loads a single conversation thread from the SQLite database by its ID.
        Includes the OCC version number for concurrency-safe write-back operations.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT title, timestamp, model_id, messages_json, messages_html, version FROM conversations WHERE id = ?', 
                (conv_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "id": conv_id,
                    "title": row[0],
                    "timestamp": row[1],
                    "model_id": row[2],
                    "messages": json.loads(row[3]),
                    "messages_html": row[4],
                    "version": row[5] if row[5] is not None else 1
                }
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Load error: {e}")
        return None

    def get_all_conversations(self) -> List[tuple]:
        """
        Retrieves a lightweight summary list of all conversations, ordered by most recent.
        """
        conn = None
        rows = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, timestamp FROM conversations ORDER BY timestamp DESC')
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Get all error: {e}")
        return rows

    def delete_conversation(self, conv_id: int) -> None:
        """
        Deletes a specific conversation thread and all its history from the database by its ID.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Delete error: {e}")

    def clear_all(self) -> None:
        """
        Wipes all conversations from the database tables. Used for global cleanups.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations')
            conn.commit()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Clear all error: {e}")
