# utils/path_utils.py
# This file contains utility functions for handling file paths in the LLM Chat App. 
# It includes a function to get the absolute path to resources, which works both 
# in development and when the app is packaged with PyInstaller.   

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
    """Get the WRITABLE AppData directory for user data."""
    app_data_dir = Path(os.getenv('APPDATA')) / "LLMChatApp"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir

def get_models_path():
    """Get WRITABLE path for models.json.
    On first run, copies the default from _internal to AppData."""
    target_file = get_app_data_dir() / "models.json"
    bundled_file = get_resource_path("resources/models.json")
    
    # If the user file doesn't exist yet, copy the master from the exe
    if not target_file.exists() and bundled_file.exists():
        shutil.copy2(bundled_file, target_file)
        
    return target_file

def get_cache_path():
    """Get WRITABLE path for the badge cache folder."""
    cache_dir = get_app_data_dir() / "badge_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir