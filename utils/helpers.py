# utils/helpers.py
import json
from pathlib import Path
from datetime import datetime
from .path_utils import get_resource_path

def format_timestamp() -> str:
    """Return formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
    
def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def get_active_system_instructions() -> str:
    """Retrieves user-selected system prompts from the user_prompts.json catalog."""
    library = []
    file_path = get_resource_path("resources/user_prompts.json")
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                library = json.load(f)
        except Exception:
            pass
            
    active = [f"- {i.get('text', '')}" for i in library if i.get('checked', False) and i.get('text')]
    if active:
        return "Instructions:\n" + "\n".join(active)
    return ""
