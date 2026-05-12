# logic/model_io.py
# Centralized Load/Save module managing multi-provider JSON fragmentation.

import os
import json
import glob
from utils.path_utils import get_resource_path, get_models_directory_path
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

def load_all_models() -> list:
    """
    Scans dedicated model_json folder for all models_*.json files and merges contents.
    """
    res_dir = get_models_directory()
    combined_models = []
    seen_ids = set()
    
    # 1. Gather dynamic files matching pattern models_*.json in SUBFOLDER
    pattern = os.path.join(res_dir, "models_*.json")
    found_files = glob.glob(pattern)
    
    # 2. Also include legacy models.json from parent if it STILL exists (final fallback)
    legacy_parent = os.path.dirname(get_resource_path("resources/models.json"))
    legacy_path = os.path.join(legacy_parent, "models.json")
    if os.path.exists(legacy_path):
        found_files.append(legacy_path)
        
    for file_path in sorted(found_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                model_list = data.get("models", [])
                
                # Detect provider based on filename fallback if missing (e.g., models_google.json -> google)
                basename = os.path.basename(file_path).lower()
                inferred_provider = "nvidia"
                if "google" in basename: inferred_provider = "google"
                elif "nvidia" in basename: inferred_provider = "nvidia"

                for m in model_list:
                    if m.get("id") not in seen_ids:
                        # Backfill default provider if missing
                        if "provider" not in m:
                            m["provider"] = inferred_provider
                        
                        combined_models.append(m)
                        seen_ids.add(m.get("id"))
        except Exception as e:
            print(f"WARNING: Failed to parse model file {file_path}: {e}")
            
    return combined_models

def save_all_models(all_models: list):
    """
    Intelligently splits models by their provider key and writes back to 
    individual models_{provider}.json files!
    """
    res_dir = get_models_directory()
    
    # Group them in memory
    buckets = {}
    
    for model in all_models:
        # Default unassigned ones back to NVIDIA
        p = model.get("provider", "nvidia").lower()
        if p not in buckets:
            buckets[p] = []
        buckets[p].append(model)
        
    # Write each bucket out to its isolated file
    for provider, models_sublist in buckets.items():
        filename = f"models_{provider}.json"
        target_path = os.path.join(res_dir, filename)
        
        try:
            output_data = {"models": models_sublist}
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(models_sublist)} models to {filename}")
        except Exception as e:
             print(f"ERROR writing to {target_path}: {e}")
             
    # OPTIONAL: We can also purge/rename legacy models.json to prevent duplication 
    # once users have adopted the new structure.
    legacy = os.path.join(res_dir, "models.json")
    if os.path.exists(legacy):
        try:
            backup = os.path.join(res_dir, "models.json.bak")
            if os.path.exists(backup): os.remove(backup)
            os.rename(legacy, backup)
            print("Archived legacy models.json to .bak")
        except: pass
