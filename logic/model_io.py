# logic/model_io.py
# Centralized Load/Save module managing multi-provider JSON fragmentation.

import os
import json
import glob
from utils.path_utils import get_resource_path

def get_models_directory():
    """Resolves the parent folder containing resources."""
    base_path = get_resource_path("resources/models.json") # Used to find dir
    return os.path.dirname(base_path)

def load_all_models() -> list:
    """
    Scans resources folder for all models_*.json files and merges contents.
    Automatically falls back to root models.json if exists for backwards compatibility.
    """
    res_dir = get_models_directory()
    combined_models = []
    seen_ids = set()
    
    # 1. Gather dynamic files matching pattern models_*.json
    pattern = os.path.join(res_dir, "models_*.json")
    found_files = glob.glob(pattern)
    
    # 2. Also include legacy models.json if it exists
    legacy_path = os.path.join(res_dir, "models.json")
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
