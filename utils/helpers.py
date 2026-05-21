# utils/helpers.py
import re
import json
from pathlib import Path
from datetime import datetime
from .path_utils import get_resource_path

def strip_markdown(text: str) -> str:
    """
    Converts markdown-formatted text to clean plain text.
    Strips bold (**text**), italic (*text*), code (`text`),
    headings (#), bullet points, and numbered lists.
    Used for displaying model descriptions in PySide6 widgets
    that don't render markdown natively.
    """
    if not text:
        return ""
    # Strip bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Strip italic: *text* or _text_ (but not inside words like file_name)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    # Strip inline code: `text`
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Strip heading markers: ### Heading -> Heading
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Strip bullet list markers: * item or - item -> item
    text = re.sub(r'^\s*[\*\-]\s+', '', text, flags=re.MULTILINE)
    # Strip numbered list markers: 1. item -> item
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Collapse multiple newlines into a single space for table cells
    text = re.sub(r'\n{2,}', ' ', text)
    # Replace single newlines with space
    text = text.replace('\n', ' ')
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

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
