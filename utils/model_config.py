# utils/model_config.py

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

def get_context_limit(model_id: str) -> int:
    """Get character limit for specific model."""
    if not model_id:
        return 512_000
        
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
    else:
        return 512_000  # Safe default
    


