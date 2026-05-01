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

# In-memory cache to prevent redundant disk I/O
_models_cache = None
_last_mtime = 0

def _load_models_data():
    """Loads models from JSON with a simple cache based on file modification time."""
    global _models_cache, _last_mtime
    models_file = get_models_path()
    
    if not models_file.exists():
        return []

    try:
        current_mtime = os.path.getmtime(models_file)
        # Only reload if cache is empty OR file has been modified since last load
        if _models_cache is None or current_mtime > _last_mtime:
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _models_cache = data.get("models", [])
                _last_mtime = current_mtime
        return _models_cache
    except Exception as e:
        print(f"Error loading models cache: {e}")
        return []

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
