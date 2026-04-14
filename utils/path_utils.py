# utils/path_utils.py
# Utility functions for handling file paths and directories in a cross-platform way.
# This module provides functions to get paths for resources, user data, models, and cache, ensuring compatibility with both development and PyInstaller environments.   

import sys
import os
import shutil
from pathlib import Path

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(__file__).parent.parent
    
    full_path = base_path / relative_path
    
    # Create parent directory if it doesn't exist (for writable paths)
    if relative_path.startswith("resources/"):
        full_path.parent.mkdir(parents=True, exist_ok=True)
    
    return full_path

def get_models_path():
    """Get path for models.json in resources folder"""
    return get_resource_path("resources/models.json")

def get_cache_path():
    """Get path for cache folder in resources"""
    cache_dir = get_resource_path("resources/badge_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir