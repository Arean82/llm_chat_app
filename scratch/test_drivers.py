# scratch/test_drivers.py
import os
import json
import shutil
import unittest
from pathlib import Path
from datetime import datetime

from logic.storage_drivers.sqlite_driver import LocalSQLiteDriver
from logic.conversation_manager import ConversationManager

class TestStorageDrivers(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("./test_conversations_temp")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.test_dir / "test_chat.db"

    def tearDown(self):
        # Clean up test directories
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            
        # Clean up local libsql file if any
        libsql_file = Path("test_libsql.db")
        if libsql_file.exists():
            try: libsql_file.unlink()
            except Exception: pass

    def test_local_sqlite_driver_lifecycle(self):
        """Tests the complete BaseStorageDriver interface lifecycle using LocalSQLiteDriver."""
        print("\n--- Running LocalSQLiteDriver Tests ---")
        driver = LocalSQLiteDriver(self.db_path)
        
        # 1. Initialize Tables (Idempotent)
        driver.init_db()
        
        # 2. Save Conversation (Insert)
        conv = [
            {"role": "user", "content": "Hello, is this the modular driver?"},
            {"role": "assistant", "content": "Yes, this is LocalSQLiteDriver!"}
        ]
        conv_id = driver.save_conversation(
            conversation=conv,
            title="Driver Verification Thread",
            conv_id=None,
            model_id="meta/llama-3-8b",
            messages_html="<p>Hello...</p>",
            timestamp=datetime.now().isoformat()
        )
        self.assertIsNotNone(conv_id)
        self.assertIsInstance(conv_id, int)
        print(f"[SQLite Test] Insert successful. Assigned ID: {conv_id}")

        # 3. Load Conversation
        loaded = driver.load_conversation(conv_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["id"], conv_id)
        self.assertEqual(loaded["title"], "Driver Verification Thread")
        self.assertEqual(loaded["model_id"], "meta/llama-3-8b")
        self.assertEqual(len(loaded["messages"]), 2)
        self.assertEqual(loaded["messages"][0]["role"], "user")
        self.assertEqual(loaded["messages_html"], "<p>Hello...</p>")
        print("[SQLite Test] Loaded conversation fields match successfully.")

        # 4. Save Conversation (Update)
        conv.append({"role": "user", "content": "Excellent work!"})
        updated_id = driver.save_conversation(
            conversation=conv,
            title="Updated Verification Thread",
            conv_id=conv_id,
            model_id="meta/llama-3-8b",
            messages_html="<p>Updated...</p>"
        )
        self.assertEqual(updated_id, conv_id)
        
        # Reload and check update fields
        reloaded = driver.load_conversation(conv_id)
        self.assertEqual(reloaded["title"], "Updated Verification Thread")
        self.assertEqual(len(reloaded["messages"]), 3)
        self.assertEqual(reloaded["messages_html"], "<p>Updated...</p>")
        print("[SQLite Test] Conversation update persistent and validated.")

        # 5. Get All Conversations
        all_convs = driver.get_all_conversations()
        self.assertEqual(len(all_convs), 1)
        self.assertEqual(all_convs[0][0], conv_id)
        self.assertEqual(all_convs[0][1], "Updated Verification Thread")
        print("[SQLite Test] Sidebar summary query verified.")

        # 6. Delete Conversation
        driver.delete_conversation(conv_id)
        self.assertIsNone(driver.load_conversation(conv_id))
        self.assertEqual(len(driver.get_all_conversations()), 0)
        print("[SQLite Test] Deletion sweep completed successfully.")

    def test_libsql_driver_lifecycle(self):
        """Tests LibSQLStorageDriver using a local file client if the SDK package is installed."""
        print("\n--- Running LibSQLStorageDriver Tests ---")
        try:
            import libsql_client
        except ImportError:
            print("[LibSQL Test] Skipping LibSQLStorageDriver test. 'libsql-client' package is not installed.")
            return

        from logic.storage_drivers.libsql_driver import LibSQLStorageDriver
        
        # Use file scheme to test LibSQL driver locally without needing active Cloud Turso DB URL
        driver = LibSQLStorageDriver(url="file:test_libsql.db")
        
        # 1. Initialize Tables
        driver.init_db()
        
        # 2. Save Conversation (Insert)
        conv = [
            {"role": "user", "content": "Hello Turso!"},
            {"role": "assistant", "content": "Hello edge database!"}
        ]
        conv_id = driver.save_conversation(
            conversation=conv,
            title="Turso verification",
            conv_id=None,
            model_id="google/gemini-1.5-pro",
            messages_html="<b>Turso</b>",
            timestamp=datetime.now().isoformat()
        )
        self.assertIsNotNone(conv_id)
        print(f"[LibSQL Test] Insert successful. Assigned ID: {conv_id}")

        # 3. Load Conversation
        loaded = driver.load_conversation(conv_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["title"], "Turso verification")
        self.assertEqual(loaded["messages"][0]["content"], "Hello Turso!")
        print("[LibSQL Test] Loaded conversation matches successfully.")

        # 4. Save Conversation (Update)
        conv.append({"role": "user", "content": "Is edge fast?"})
        updated_id = driver.save_conversation(
            conversation=conv,
            title="Turso updated thread",
            conv_id=conv_id,
            messages_html="<i>Turso updated</i>"
        )
        self.assertEqual(updated_id, conv_id)
        
        reloaded = driver.load_conversation(conv_id)
        self.assertEqual(reloaded["title"], "Turso updated thread")
        self.assertEqual(len(reloaded["messages"]), 3)
        print("[LibSQL Test] Update verified successfully.")

        # 5. Get All Summary List
        all_convs = driver.get_all_conversations()
        self.assertEqual(len(all_convs), 1)
        self.assertEqual(all_convs[0][1], "Turso updated thread")

        # 6. Clear All
        driver.clear_all()
        self.assertEqual(len(driver.get_all_conversations()), 0)
        print("[LibSQL Test] Table clear completed successfully.")

if __name__ == "__main__":
    unittest.main()
