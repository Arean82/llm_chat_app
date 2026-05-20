# utils/model_config.py
import json
import os
from utils.path_utils import get_models_path

MODEL_CONTEXT_LIMITS = {
    "llama-4-scout": 40_000_000,
    "kimi-k2": 4_000_000,
    "deepseek-v3.1": 4_000_000,
    "llama-3.3": 512_000,
    "qwen3.5": 512_000,
    "glm5": 512_000,
    "mistral-large": 1_000_000,
    "gemma-3": 256_000,
}

import glob
from utils.path_utils import get_resource_path, get_models_directory_path

# In-memory cache to prevent redundant disk I/O
_models_cache = None
_last_scan_mtime = 0

def _load_models_data():
    """Loads models scanning all models_*.json shards safely with a global cache timer."""
    global _models_cache, _last_scan_mtime
    
    # Resolve dedicated subdirectory
    res_dir = get_models_directory_path()
    
    # Locate all shards inside subfolder
    pattern = os.path.join(res_dir, "models_*.json")
    found_files = glob.glob(pattern)
    
    # Also check root for fallback
    base_file = get_resource_path("resources/models.json")
    if base_file.exists():
        found_files.append(str(base_file))
        
    if not found_files:
        return []
        
    try:
        # Calculate max modification time across ALL found files
        current_max_mtime = max(os.path.getmtime(f) for f in found_files)
        
        # Only reload if never loaded, or ANY file changed
        if _models_cache is None or current_max_mtime > _last_scan_mtime:
            all_models = []
            seen_ids = set()
            
            for fp in found_files:
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        sub_models = data.get("models", [])
                        for m in sub_models:
                            m_id = m.get("id")
                            if m_id and m_id not in seen_ids:
                                all_models.append(m)
                                seen_ids.add(m_id)
                except:
                    pass # Skip corrupt shards gracefully
                    
            _models_cache = all_models
            _last_scan_mtime = current_max_mtime
            
        return _models_cache
    except Exception as e:
        print(f"Critical error in distributed model data load: {e}")
        return _models_cache or []

def get_context_limit(model_id: str) -> int:
    """Get TOKEN limit for specific model, prioritizing cached dynamic data."""
    if not model_id:
        return 512_000

    # 1. Try to get from cached JSON data
    models = _load_models_data()
    for model in models:
        if model.get("id") == model_id and model.get("context_length"):
            try:
                return int(model["context_length"])
            except (ValueError, TypeError):
                continue
        
    # 2. Fallback to hardcoded estimates if not in JSON
    model_lower = model_id.lower()
    
    if "llama-4" in model_lower or "scout" in model_lower:
        return MODEL_CONTEXT_LIMITS["llama-4-scout"]
    elif "kimi" in model_lower:
        return MODEL_CONTEXT_LIMITS["kimi-k2"]
    elif "deepseek" in model_lower:
        return MODEL_CONTEXT_LIMITS["deepseek-v3.1"]
    elif "llama-3.3" in model_lower:
        return MODEL_CONTEXT_LIMITS["llama-3.3"]
    elif "qwen" in model_lower:
        return MODEL_CONTEXT_LIMITS["qwen3.5"]
    elif "glm" in model_lower:
        return MODEL_CONTEXT_LIMITS["glm5"]
    elif "mistral" in model_lower:
        return MODEL_CONTEXT_LIMITS["mistral-large"]
    elif "gemma" in model_lower:
        return MODEL_CONTEXT_LIMITS["gemma-3"]
        
    # Final default
    return 512_000  # Safe default

def does_model_support_tools(model_id: str) -> bool:
    """Checks if the model is flagged as supporting tools (defaulting to True)."""
    if not model_id:
        return True
    models = _load_models_data()
    for model in models:
        if model.get("id") == model_id:
            # Returns the saved status, defaulting to True if not yet set/tested
            return model.get("supports_tools", True)
    return True

def update_model_capability(model_id: str, supports_tools: bool):
    """Updates and saves the supports_tools metadata flag inside the models JSON shards."""
    if not model_id:
        return
    
    res_dir = get_models_directory_path()
    pattern = os.path.join(res_dir, "models_*.json")
    found_files = glob.glob(pattern)
    
    base_file = get_resource_path("resources/models.json")
    if base_file.exists():
        found_files.append(str(base_file))
        
    for fp in found_files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            models = data.get("models", [])
            updated = False
            for m in models:
                if m.get("id") == model_id:
                    m["supports_tools"] = supports_tools
                    updated = True
            if updated:
                with open(fp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                # Purge global memory cache to force dynamic re-scan on next load
                global _models_cache
                _models_cache = None
                print(f"[ModelConfig] Saved capability update: '{model_id}' -> supports_tools={supports_tools}")
                break
        except Exception as e:
            print(f"[ModelConfig] Error updating dynamic metadata shard {fp}: {e}")
