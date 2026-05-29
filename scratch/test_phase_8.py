# scratch/test_phase_8.py
import unittest
import os
import sys
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock

# Ensure the app can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.logic.storage_drivers.sqlite_driver import LocalSQLiteDriver
from server.logic.migration_bridge import migrate_database
from server.logic.model_io import load_all_models, save_all_models
from server.logic.services.base_service import ServiceRegistry
from server.utils.path_utils import get_models_directory_path, get_resource_path

class TestPhase8DataMigration(unittest.TestCase):
    def setUp(self):
        """Set up isolated test databases and mock directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.db1_path = os.path.join(self.temp_dir, "source.db")
        self.db2_path = os.path.join(self.temp_dir, "dest.db")
        
        self.source_driver = LocalSQLiteDriver(self.db1_path)
        self.dest_driver = LocalSQLiteDriver(self.db2_path)
        
        # We'll mock the StorageService to return our source driver
        self.mock_storage_service = MagicMock()
        self.mock_storage_service.get_driver.return_value = self.source_driver
        ServiceRegistry.register("storage", self.mock_storage_service)

    def tearDown(self):
        """Clean up the test files."""
        self.source_driver.close_pool()
        self.dest_driver.close_pool()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("server.logic.model_io.get_models_directory")
    def test_8_1_2_json_purge_and_migration_hook(self, mock_get_models_dir):
        """Test that legacy JSON files are parsed into the DB and then deleted."""
        # Create a mock models directory
        models_dir = os.path.join(self.temp_dir, "models_dir")
        os.makedirs(models_dir, exist_ok=True)
        mock_get_models_dir.return_value = models_dir
        
        # Create a dummy legacy JSON file
        dummy_models = {
            "models": [
                {"id": "gpt-4", "provider": "openai", "max_tokens": 8192},
                {"id": "claude-3", "provider": "anthropic", "max_tokens": 100000}
            ]
        }
        json_path = os.path.join(models_dir, "models_test.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dummy_models, f)
            
        self.assertTrue(os.path.exists(json_path))
        
        # 1. Trigger the one-time migration hook via load_all_models
        loaded_models = load_all_models()
        
        # 2. Verify the JSON file was permanently deleted (Purged)
        self.assertFalse(os.path.exists(json_path))
        
        # 3. Verify the models were inserted into the database schema
        db_models = self.source_driver.load_all_models()
        self.assertEqual(len(db_models), 2)
        
        ids = [m["id"] for m in db_models]
        self.assertIn("gpt-4", ids)
        self.assertIn("claude-3", ids)
        
        # 4. Verify save_all_models bypasses flat files and writes to DB
        new_model = [{"id": "llama-3", "provider": "meta"}]
        save_all_models(new_model)
        
        updated_db_models = self.source_driver.load_all_models()
        # the save_model does an upsert but we just pushed a new one, the old ones are still there
        # so total is 3
        self.assertEqual(len(updated_db_models), 3)

    def test_8_1_3_migration_bridge_transfers_config(self):
        """Test that migration_bridge.py safely transfers models and system_config."""
        # Setup source data
        self.source_driver.save_model("test-model-1", "test-prov", {"id": "test-model-1", "prop": "val"})
        self.source_driver.set_config("user_prompts", {"greeting": "hello"})
        
        # Verify dest is empty
        self.assertEqual(len(self.dest_driver.load_all_models()), 0)
        self.assertIsNone(self.dest_driver.get_config("user_prompts"))
        
        # Run migration bridge
        migrated = migrate_database(self.source_driver, self.dest_driver)
        
        # Verify data was transferred
        dest_models = self.dest_driver.load_all_models()
        self.assertEqual(len(dest_models), 1)
        self.assertEqual(dest_models[0]["id"], "test-model-1")
        
        dest_config = self.dest_driver.get_config("user_prompts")
        self.assertIsNotNone(dest_config)
        self.assertEqual(dest_config["greeting"], "hello")

if __name__ == "__main__":
    unittest.main()
