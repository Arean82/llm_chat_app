# logic/storage_drivers/sqlite_driver.py
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from logic.storage_drivers.base_driver import BaseStorageDriver

class LocalSQLiteDriver(BaseStorageDriver):
    """
    Concrete SQLite database driver implementing BaseStorageDriver.
    Handles standard file-based SQL operations on local files, enabling
    localized single-user desktop storage and isolated File-per-Tenant partitions.
    """

    def __init__(self, db_path: Path):
        """
        Initializes the SQLite driver.

        Args:
            db_path (Path): Absolute filesystem path to the target SQLite .db file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self) -> None:
        """
        Initializes the SQLite database tables and high-speed timestamp indices.
        Enables WAL mode dynamically for superior read concurrency and crash safety.
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
                    messages_html TEXT
                )
            ''')
            
            # Audit ID 020: Index high-traffic timestamp column to preserve sidebar speed over scale
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp);')
            
            # Migration check: Ensure messages_html column exists for older database migrations
            try:
                cursor.execute('ALTER TABLE conversations ADD COLUMN messages_html TEXT')
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
                          messages_html: str = None, timestamp: str = None) -> Optional[int]:
        """
        Saves or updates a conversation thread in the SQLite database.
        """
        messages_json = json.dumps(conversation)
        if not timestamp:
            timestamp = datetime.now().isoformat()
        conn = None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if conv_id is not None:
                # Update existing conversation record
                cursor.execute('''
                    UPDATE conversations 
                    SET title = ?, timestamp = ?, messages_json = ?, messages_html = ? 
                    WHERE id = ?
                ''', (title, timestamp, messages_json, messages_html, conv_id))
            else:
                # Insert new conversation record
                cursor.execute('''
                    INSERT INTO conversations (title, timestamp, model_id, messages_json, messages_html)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, timestamp, model_id, messages_json, messages_html))
                conv_id = cursor.lastrowid

            conn.commit()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Save error: {e}")
        finally:
            if conn:
                conn.close()
        return conv_id

    def load_conversation(self, conv_id: int) -> Optional[dict]:
        """
        Loads a single conversation thread from the SQLite database by its ID.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT title, timestamp, model_id, messages_json, messages_html FROM conversations WHERE id = ?', 
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
                    "messages_html": row[4]
                }
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Load error: {e}")
        finally:
            if conn:
                conn.close()
        return None

    def get_all_conversations(self) -> List[tuple]:
        """
        Retrieves a lightweight summary list of all conversations, ordered by most recent.
        """
        conn = None
        rows = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, timestamp FROM conversations ORDER BY timestamp DESC')
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Get all error: {e}")
        finally:
            if conn:
                conn.close()
        return rows

    def delete_conversation(self, conv_id: int) -> None:
        """
        Deletes a specific conversation thread and all its history from the database by its ID.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Delete error: {e}")
        finally:
            if conn:
                conn.close()

    def clear_all(self) -> None:
        """
        Wipes all conversations from the database tables. Used for global cleanups.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations')
            conn.commit()
        except sqlite3.Error as e:
            print(f"[LocalSQLiteDriver] Clear all error: {e}")
        finally:
            if conn:
                conn.close()
