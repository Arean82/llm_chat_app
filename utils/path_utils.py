# utils/path_utils.py
# Utility functions for handling file paths and directories in a cross-platform way.
# This module provides functions to get paths for resources, user data, models, and cache, ensuring compatibility with both development and PyInstaller environments.   

import sys
import os
import shutil
from pathlib import Path

def get_resource_path(relative_path):
    """Get absolute path to READ-ONLY resource, works for dev and for PyInstaller"""
    try:
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).parent.parent
    return base_path / relative_path

def get_app_data_dir():
    """Get the WRITABLE AppData directory for user data (Cross-Platform)."""
    if sys.platform == "win32":
        base = Path(os.getenv('APPDATA'))
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux: ~/.local/share/ (respects XDG standard)
        base = Path(os.getenv('XDG_DATA_HOME', Path.home() / ".local" / "share"))
    
    app_data_dir = base / "LLMChatApp"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir

def get_models_path():
    """Get WRITABLE path for models.json."""
    target_file = get_app_data_dir() / "models.json"
    bundled_file = get_resource_path("resources/models.json")
    
    if not target_file.exists() and bundled_file.exists():
        shutil.copy2(bundled_file, target_file)
        
    return target_file

def get_cache_path():
    """Get WRITABLE path for the badge cache folder."""
    cache_dir = get_app_data_dir() / "badge_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir