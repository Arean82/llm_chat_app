# logic/conversation_manager.py
import json
from datetime import datetime
from pathlib import Path

from utils.storage_config import StorageManager
from logic.storage_drivers.sqlite_driver import LocalSQLiteDriver

class ConversationManager:
    """
    High-level conversation orchestrator for the application.
    Dynamically initializes and interfaces with BaseStorageDriver subclasses
    to handle chat histories, JSON migrations, and backup operations.
    """

    def __init__(self, tenant_id: str = "default_user"):
        self.base_dir = StorageManager.get_instance().get_storage_root()
        self.conversations_dir = self.base_dir / "conversations"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        # Dynamic Tenant Database Resolution (Phase 2.1.4)
        self.active_tenant_id = None
        self.db_path = None
        self.driver = None
        self.set_tenant(tenant_id)

    def set_tenant(self, tenant_id: str):
        """
        Dynamically shifts the database storage path to isolate a specific tenant/user.
        If 'default_user' is specified, it maintains the legacy desktop path for backward-compatibility.
        """
        self.active_tenant_id = tenant_id
        
        # Map tenant ID to its isolated database path
        if tenant_id == "default_user":
            self.db_path = self.conversations_dir / "chat_history.db"
        else:
            self.db_path = self.conversations_dir / "tenants" / tenant_id / "chat_history.db"
            
        # Guarantee parent directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Instantiate the database driver for this tenant's path
        self.driver = LocalSQLiteDriver(self.db_path)
        
        # Run legacy json migrations (if any JSON files exist to import)
        self.migrate_json_to_sqlite()

    def migrate_json_to_sqlite(self):
        """Finds existing JSON files and imports them into the DB if they aren't already there."""
        json_files = list(self.conversations_dir.glob("*.json"))
        if not json_files:
            return

        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Use filename as title if not present
                title = file_path.stem.replace("conversation_", "").replace("_", " ")
                timestamp = data.get("timestamp", datetime.now().isoformat())
                model_id = data.get("model_id", "")
                messages = data.get("messages", [])

                # Save into the database via the dynamic driver interface
                self.driver.save_conversation(
                    conversation=messages,
                    title=title,
                    conv_id=None,
                    model_id=model_id,
                    messages_html=None,
                    timestamp=timestamp
                )
                
                # Immediately delete source JSON after verified insertion to prevent clutter
                file_path.unlink()
            except Exception as e:
                print(f"[ConversationManager] Migration error for {file_path}: {e}")

        # Global Housekeeping: Search and destroy any previously left behind .bak files
        for bak_file in self.conversations_dir.glob("*.json.bak"):
             try:
                 bak_file.unlink()
             except Exception:
                 pass

    def save_conversation(self, conversation: list, title: str = "New Conversation", 
                          conv_id: int = None, model_id: str = "", messages_html: str = None) -> int:
        """Saves or updates a conversation in the active database via the pluggable driver."""
        return self.driver.save_conversation(
            conversation=conversation,
            title=title,
            conv_id=conv_id,
            model_id=model_id,
            messages_html=messages_html
        )

    def load_conversation(self, conv_id: int) -> dict:
        """Loads a specific conversation by its ID via the pluggable driver."""
        return self.driver.load_conversation(conv_id)

    def get_all_conversations(self) -> list:
        """Returns a list of all conversations for the sidebar via the pluggable driver."""
        return self.driver.get_all_conversations()

    def delete_conversation(self, conv_id: int):
        """Deletes a specific conversation by ID via the pluggable driver."""
        self.driver.delete_conversation(conv_id)

    def clear_all(self):
        """Wipes the entire conversations table via the pluggable driver."""
        self.driver.clear_all()

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
