# logic/storage_drivers/postgres_driver.py
import json
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from logic.storage_drivers.base_driver import BaseStorageDriver

class PostgreSQLStorageDriver(BaseStorageDriver):
    """
    Concrete PostgreSQL storage driver implementing BaseStorageDriver.
    Connects to high-concurrency remote or local PostgreSQL database engines,
    providing row-level locks and Multiversion Concurrency Control (MVCC).
    """

    def __init__(self, url: str):
        """
        Initializes the PostgreSQL driver using a connection URL.

        Args:
            url (str): Connection URL (e.g., postgresql://user:password@localhost:5432/db_name).
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
            
        self.init_db()

    def _get_connection(self):
        """Helper to establish a connection using the parsed URL parameters."""
        import pg8000.dbapi
        parsed = urlparse(self.url)
        
        # Extract connection details
        user = parsed.username or ""
        password = parsed.password or ""
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        database = parsed.path.lstrip('/') or "postgres"
        
        # Return connection context
        return pg8000.dbapi.connect(
            user=user,
            password=password,
            host=host,
            database=database,
            port=int(port)
        )

    def init_db(self) -> None:
        """
        Initializes the PostgreSQL database schema and high-speed timestamp indices.
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
                    messages_html TEXT
                )
            ''')
            
            # Index high-traffic timestamp column to preserve sidebar speed over scale
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp);')
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def save_conversation(self, conversation: list, title: str = "New Conversation", 
                          conv_id: int = None, model_id: str = "", 
                          messages_html: str = None, timestamp: str = None) -> Optional[int]:
        """
        Saves or updates a conversation thread in the PostgreSQL database.
        """
        messages_json = json.dumps(conversation)
        if not timestamp:
            timestamp = datetime.now().isoformat()
            
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if conv_id is not None:
                # Update existing conversation record
                cursor.execute('''
                    UPDATE conversations 
                    SET title = %s, timestamp = %s, messages_json = %s, messages_html = %s 
                    WHERE id = %s
                ''', (title, timestamp, messages_json, messages_html, conv_id))
            else:
                # Insert new conversation record and return the generated ID atomically via RETURNING
                cursor.execute('''
                    INSERT INTO conversations (title, timestamp, model_id, messages_json, messages_html)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (title, timestamp, model_id, messages_json, messages_html))
                res = cursor.fetchone()
                if res:
                    conv_id = int(res[0])
            conn.commit()
        finally:
            cursor.close()
            conn.close()
            
        return conv_id

    def load_conversation(self, conv_id: int) -> Optional[dict]:
        """
        Loads a single conversation thread from the PostgreSQL database by its ID.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT title, timestamp, model_id, messages_json, messages_html FROM conversations WHERE id = %s', 
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
                    "messages_html": res[4]
                }
        finally:
            cursor.close()
            conn.close()
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
            conn.close()
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
            conn.close()

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
            conn.close()
