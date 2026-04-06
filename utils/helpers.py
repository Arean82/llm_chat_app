# utils/helpers.py
from datetime import datetime


def format_timestamp() -> str:
    """Return formatted timestamp for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    
def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."