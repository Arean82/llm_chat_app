# logic/conversation_manager.py
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from utils.storage_config import StorageManager

class ConversationManager:
    def __init__(self):
        self.base_dir = StorageManager.get_instance().get_storage_root()
        self.conversations_dir = self.base_dir / "conversations"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.conversations_dir / "chat_history.db"
        self.init_db()
        self.migrate_json_to_sqlite()

    def init_db(self):
        """Initializes the SQLite database and creates the conversations table."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Enable WAL mode for better concurrency and crash resistance
            cursor.execute('PRAGMA journal_mode=WAL;')
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
            # Migration: Ensure messages_html column exists for older databases
            try:
                cursor.execute('ALTER TABLE conversations ADD COLUMN messages_html TEXT')
            except sqlite3.OperationalError:
                pass 

            conn.commit()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
        finally:
            if conn:
                conn.close()

    def migrate_json_to_sqlite(self):
        """Finds existing JSON files and imports them into the DB if they aren't already there."""
        json_files = list(self.conversations_dir.glob("*.json"))
        if not json_files:
            return

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Use filename as title if not present
                    title = file_path.stem.replace("conversation_", "").replace("_", " ")
                    timestamp = data.get("timestamp", datetime.now().isoformat())
                    model_id = data.get("model_id", "")
                    messages = json.dumps(data.get("messages", []))

                    # Insert into DB
                    cursor.execute('''
                        INSERT INTO conversations (title, timestamp, model_id, messages_json)
                        VALUES (?, ?, ?, ?)
                    ''', (title, timestamp, model_id, messages))
                    
                    # Rename file to prevent re-migration
                    file_path.rename(file_path.with_suffix(".json.bak"))
                except Exception as e:
                    print(f"Migration error for {file_path}: {e}")

            conn.commit()
        except sqlite3.Error as e:
            print(f"Migration error: {e}")
        finally:
            if conn:
                conn.close()

    def save_conversation(self, conversation: list, title: str = "New Conversation", conv_id: int = None, model_id: str = "", messages_html: str = None):
        """Saves or updates a conversation in the SQLite DB."""
        messages_json = json.dumps(conversation)

        timestamp = datetime.now().isoformat()
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if conv_id is not None:
                # Update existing
                cursor.execute('''
                    UPDATE conversations 
                    SET title = ?, timestamp = ?, messages_json = ?, messages_html = ? 
                    WHERE id = ?
                ''', (title, timestamp, messages_json, messages_html, conv_id))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO conversations (title, timestamp, model_id, messages_json, messages_html)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, timestamp, model_id, messages_json, messages_html))
                conv_id = cursor.lastrowid

            conn.commit()
        except sqlite3.Error as e:
            print(f"Save error: {e}")
        finally:
            if conn:
                conn.close()
        return conv_id

    def load_conversation(self, conv_id: int) -> dict:
        """Loads a specific conversation by its ID."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT title, timestamp, model_id, messages_json, messages_html FROM conversations WHERE id = ?', (conv_id,))
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
            print(f"Load error: {e}")
        finally:
            if conn:
                conn.close()
        return None

    def get_all_conversations(self):
        """Returns a list of all conversations for the sidebar."""
        conn = None
        rows = []
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, timestamp FROM conversations ORDER BY timestamp DESC')
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Get all error: {e}")
        finally:
            if conn:
                conn.close()
        return rows

    def delete_conversation(self, conv_id: int):
        """Deletes a specific conversation by ID."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Delete error: {e}")
        finally:
            if conn:
                conn.close()

    def clear_all(self):
        """Wipes the entire conversations table."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations')
            conn.commit()
        except sqlite3.Error as e:
            print(f"Clear all error: {e}")
        finally:
            if conn:
                conn.close()

    def export_to_json(self, conversation: list, file_path: str, model_id: str = ""):
        """Manually exports a conversation to a JSON file (standard format)."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "model_id": model_id,
            "messages": conversation
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_from_json(self, file_path: str) -> dict:
        """Loads a conversation from a standard JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)