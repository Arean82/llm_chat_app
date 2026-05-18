# logic/storage_drivers/libsql_driver.py
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from logic.storage_drivers.base_driver import BaseStorageDriver

class LibSQLStorageDriver(BaseStorageDriver):
    """
    Concrete libSQL / Turso cloud storage driver implementing BaseStorageDriver.
    Connects to Turso cloud database-per-tenant shards over libSQL with edge replication.
    """

    def __init__(self, url: str, auth_token: str = None):
        """
        Initializes the libSQL driver.

        Args:
            url (str): Connection URL (e.g., libsql://database-name.turso.io).
            auth_token (str): Optional. Turso database authentication token.
        """
        self.url = url
        self.auth_token = auth_token
        
        # Verify package availability dynamically
        try:
            import libsql_client
        except ImportError:
            raise ImportError(
                "[LibSQLStorageDriver] 'libsql-client' package is required. "
                "Please run: pip install libsql-client"
            )
            
        self.init_db()

    def init_db(self) -> None:
        """
        Initializes the libSQL database tables and high-speed timestamp indices.
        """
        import libsql_client
        with libsql_client.create_client_sync(self.url, auth_token=self.auth_token) as client:
            # Create conversations schema
            client.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    timestamp TEXT,
                    model_id TEXT,
                    messages_json TEXT,
                    messages_html TEXT
                )
            ''')
            
            # Index high-traffic timestamp column to preserve sidebar speed over scale
            client.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp);')
            
            # Migration check: Ensure messages_html column exists for older database migrations
            try:
                client.execute('ALTER TABLE conversations ADD COLUMN messages_html TEXT')
            except Exception:
                pass 

    def save_conversation(self, conversation: list, title: str = "New Conversation", 
                          conv_id: int = None, model_id: str = "", 
                          messages_html: str = None, timestamp: str = None) -> Optional[int]:
        """
        Saves or updates a conversation thread in the libSQL/Turso database.
        """
        import libsql_client
        messages_json = json.dumps(conversation)
        if not timestamp:
            timestamp = datetime.now().isoformat()
            
        with libsql_client.create_client_sync(self.url, auth_token=self.auth_token) as client:
            if conv_id is not None:
                # Update existing conversation record
                client.execute('''
                    UPDATE conversations 
                    SET title = ?, timestamp = ?, messages_json = ?, messages_html = ? 
                    WHERE id = ?
                ''', (title, timestamp, messages_json, messages_html, conv_id))
            else:
                # Insert new conversation record and fetch last inserted ID within a single transaction
                with client.transaction() as tx:
                    tx.execute('''
                        INSERT INTO conversations (title, timestamp, model_id, messages_json, messages_html)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (title, timestamp, model_id, messages_json, messages_html))
                    
                    res = tx.execute("SELECT last_insert_rowid()")
                    if res.rows:
                        conv_id = int(res.rows[0][0])
                    tx.commit()
                    
        return conv_id

    def load_conversation(self, conv_id: int) -> Optional[dict]:
        """
        Loads a single conversation thread from the libSQL database by its ID.
        """
        import libsql_client
        with libsql_client.create_client_sync(self.url, auth_token=self.auth_token) as client:
            res = client.execute(
                'SELECT title, timestamp, model_id, messages_json, messages_html FROM conversations WHERE id = ?', 
                (conv_id,)
            )
            if res.rows:
                row = res.rows[0]
                return {
                    "id": conv_id,
                    "title": row[0],
                    "timestamp": row[1],
                    "model_id": row[2],
                    "messages": json.loads(row[3]),
                    "messages_html": row[4]
                }
        return None

    def get_all_conversations(self) -> List[tuple]:
        """
        Retrieves a lightweight summary list of all conversations, ordered by most recent.
        """
        import libsql_client
        rows = []
        with libsql_client.create_client_sync(self.url, auth_token=self.auth_token) as client:
            res = client.execute('SELECT id, title, timestamp FROM conversations ORDER BY timestamp DESC')
            for row in res.rows:
                rows.append((int(row[0]), str(row[1]), str(row[2])))
        return rows

    def delete_conversation(self, conv_id: int) -> None:
        """
        Deletes a specific conversation thread and all its history from the database by its ID.
        """
        import libsql_client
        with libsql_client.create_client_sync(self.url, auth_token=self.auth_token) as client:
            client.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))

    def clear_all(self) -> None:
        """
        Wipes all conversations from the database tables. Used for global cleanups.
        """
        import libsql_client
        with libsql_client.create_client_sync(self.url, auth_token=self.auth_token) as client:
            client.execute('DELETE FROM conversations')
