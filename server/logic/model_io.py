# logic/model_io.py
# Centralized Load/Save module managing multi-provider JSON fragmentation.

import os
import json
import glob
from server.utils.path_utils import get_resource_path, get_models_directory_path
import shutil

def get_models_directory():
    """Resolves the dedicated subfolder, performing lazy migration from legacy root if needed."""
    target_dir = str(get_models_directory_path())
    legacy_dir = os.path.dirname(get_resource_path("resources/models.json"))
    
    # Auto-Migration: If legacy items exist in root, migrate them to subfolder
    if os.path.isdir(legacy_dir) and target_dir != legacy_dir:
        pattern = os.path.join(legacy_dir, "models_*.json")
        for old_file in glob.glob(pattern):
            try:
                new_file = os.path.join(target_dir, os.path.basename(old_file))
                if not os.path.exists(new_file):
                     shutil.move(old_file, new_file)
                     print(f"MIGRATED model file: {os.path.basename(old_file)} -> subfolder")
            except Exception as e:
                print(f"Migration error on {old_file}: {e}")
                
    return target_dir

def load_provider_metadata() -> dict:
    """Loads the centralized static provider registry from the resources folder."""
    conf_path = get_resource_path("resources/api_providers.json")
    try:
        if os.path.exists(conf_path):
            with open(conf_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"providers": []}
    except Exception as e:
        print(f"Error loading provider metadata: {e}")
        return {"providers": []}

def _migrate_json_to_db(driver):
    """
    Phase 8: One-time automatic migration hook.
    If legacy JSON files are found during boot, parse them, insert them into the DB schema, 
    and permanently delete the .json files.
    """
    res_dir = get_models_directory()
    pattern = os.path.join(res_dir, "models_*.json")
    found_files = glob.glob(pattern)
    
    legacy_parent = os.path.dirname(get_resource_path("resources/models.json"))
    legacy_path = os.path.join(legacy_parent, "models.json")
    if os.path.exists(legacy_path):
        found_files.append(legacy_path)
        
    if not found_files:
        return
        
    print(f"Phase 8: Migrating {len(found_files)} JSON config files to database schema...")
    for file_path in sorted(found_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                model_list = data.get("models", [])
                
                basename = os.path.basename(file_path).lower()
                if basename == "models.json":
                    inferred_provider = "nvidia"
                else:
                    inferred_provider = basename.replace("models_", "").replace(".json", "")
                if not inferred_provider: inferred_provider = "nvidia"
                
                for m in model_list:
                    if "provider" not in m:
                        m["provider"] = inferred_provider
                    # Ensure models are safely inserted into DB
                    driver.save_model(m.get("id"), m.get("provider"), m)
            
            # Delete the file after successful ingestion
            os.remove(file_path)
            print(f"Migrated and purged: {file_path}")
        except Exception as e:
            print(f"WARNING: Failed to parse/migrate model file {file_path}: {e}")

def load_all_models() -> list:
    """
    Retrieves all models directly from the database schema (Phase 8).
    Runs a one-time migration hook if legacy JSON files are detected.
    """
    from server.logic.services.base_service import ServiceRegistry
    driver = ServiceRegistry.get("storage").get_driver("default_user")
    
    _migrate_json_to_db(driver)
    
    return driver.load_all_models()

def save_all_models(all_models: list):
    """
    Saves models directly to the database schema instead of flat JSON files (Phase 8).
    """
    from server.logic.services.base_service import ServiceRegistry
    driver = ServiceRegistry.get("storage").get_driver("default_user")
    
    for model in all_models:
        driver.save_model(model.get("id"), model.get("provider", "nvidia"), model)
    print(f"Saved {len(all_models)} models to the database.")
