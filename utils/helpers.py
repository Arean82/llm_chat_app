# utils/helpers.py
# This file contains helper functions used throughout the LLM Chat App.

import json
from pathlib import Path
from datetime import datetime
from PySide6.QtGui import QIcon
from .path_utils import get_resource_path

def format_timestamp() -> str:
    """Return formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    
def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def set_app_icon(window):
    """
    Applies the app icon to any window (Main or Popup) passed to it.
    Call this in __init__ of all your dialogs.
    """
    icon_path = get_resource_path("resources/app_icon.png")
    # Convert to string because QIcon does not accept Path objects
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    # If icon doesn't exist, skip silently (no error)

def get_active_system_instructions() -> str:
    """
    Retrieves user-selected system prompts dynamically from the user_prompts.json catalog.
    Ensures consistent 'de facto' personas are synchronized across all UI pipelines.
    """
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
