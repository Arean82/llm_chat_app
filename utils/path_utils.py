# utils/path_utils.py

import sys
import os
import shutil
from pathlib import Path
from utils.storage_config import StorageManager

def get_resource_path(relative_path):
    """
    Retrieves the absolute path for a given resource.
    - If it's internal/read-only (.ui files), handles internal extraction.
    - If it's editable/writable (models, styles, logs), directs it to the global Data Root.
    """
    manager = StorageManager.get_instance()
    
    if getattr(sys, 'frozen', False):
        # READ-ONLY SYSTEM FILES: Load directly from compiled bundle memory
        if relative_path.startswith("ui_designer/"):
            base_path = Path(sys._MEIPASS)
        else:
            # WRITABLE USER FILES: Dynamically resolved to AppData, Portable, or Custom
            base_path = manager.get_storage_root()
    else:
        # Development Mode: Use project root
        base_path = manager.get_exe_dir()
    
    full_path = base_path / relative_path
    
    # Automatically create subdirectories if referencing writable resource tracks
    if relative_path.startswith("resources/"):
         full_path.parent.mkdir(parents=True, exist_ok=True)
         
    return full_path

def get_models_path():
    """Get path for models.json in global resources folder."""
    return get_resource_path("resources/models.json")

def get_models_directory_path():
    """Resolves the dedicated subfolder for ecosystem model fragmentation data."""
    d = get_resource_path("resources/model_json")
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
    return d

def get_cache_path():
    """Get path for cache folder in global resources."""
    cache_dir = get_resource_path("resources/badge_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_app_settings():
    """Global helper proxy to get the correctly scoped QSettings object (Registry or INI)."""
    return StorageManager.get_instance().get_active_settings()
