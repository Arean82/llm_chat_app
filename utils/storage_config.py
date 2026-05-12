# utils/storage_config.py
# Updated with logic for persistent storage and UI

import sys
import os
from pathlib import Path
from PySide6.QtCore import QSettings

class StorageManager:
    _instance = None
    _initialized = False
    
    def __init__(self):
        self.base_data_path = None
        self.is_portable = False
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = StorageManager()
        return cls._instance

    def get_exe_dir(self) -> Path:
        """Returns the folder containing the current running file or executable."""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent.resolve()

    def check_dir_writable(self, directory: Path) -> bool:
        """Reliably tests if a directory has system write permissions."""
        test_file = directory / ".permission_test"
        try:
            test_file.touch()
            test_file.unlink()
            return True
        except (PermissionError, OSError):
            return False

    def get_default_app_data_path(self) -> Path:
        """Returns the standard cross-platform user data path (~/LLMChatApp)."""
        # Using user's home directory was your original choice, which is safer cross-platform.
        # We keep it as Home/LLMChatApp for consistency.
        return Path.home() / "LLMChatApp"

    def detect_existing_mode(self) -> Path:
        """
        Checks existing environment indicators to automatically determine path.
        Returns Path if automatically decided, otherwise returns None to prompt UI.
        """
        # 1. CASE: Development Mode
        if not getattr(sys, 'frozen', False):
            self.is_portable = True # Treat Dev root as portable folder
            self.base_data_path = self.get_exe_dir()
            return self.base_data_path

        exe_dir = self.get_exe_dir()
        
        # 2. CASE: The "Portable" Marker File exists in root
        if (exe_dir / "portable.txt").exists():
            self.is_portable = True
            self.base_data_path = exe_dir
            return self.base_data_path
            
        # 3. CASE: Test if running from Read-Only directory (e.g. Program Files)
        if not self.check_dir_writable(exe_dir):
            # FORCED to use AppData (No UI required, silently resolves)
            self.is_portable = False
            self.base_data_path = self.get_default_app_data_path()
            return self.base_data_path
            
        # 4. CASE: Check system Registry/Settings for a custom path
        settings = QSettings("LLMChatApp", "Settings")
        saved_path = settings.value("storage/data_root", None)
        if saved_path:
            saved_path_obj = Path(saved_path)
            # Validate that path actually exists or is creatable
            try:
                saved_path_obj.mkdir(parents=True, exist_ok=True)
                self.is_portable = False
                self.base_data_path = saved_path_obj
                return self.base_data_path
            except Exception:
                pass # If directory is unreachable (e.g., USB unplugged), fall through to UI

        # 5. CASE: No decision yet. Return None to trigger first run dialog.
        return None

    def finalize_setup(self, selected_mode: str, custom_path: Path = None):
        """Saves the final decision from UI and sets global path config."""
        exe_dir = self.get_exe_dir()

        if selected_mode == "PORTABLE":
            # Create portable marker
            (exe_dir / "portable.txt").touch()
            self.base_data_path = exe_dir
            self.is_portable = True
            
        elif selected_mode == "APPDATA":
            path = self.get_default_app_data_path()
            path.mkdir(parents=True, exist_ok=True)
            
            settings = QSettings("LLMChatApp", "Settings")
            settings.setValue("storage/data_root", str(path))
            self.base_data_path = path
            self.is_portable = False
            
        elif selected_mode == "CUSTOM" and custom_path:
            custom_path.mkdir(parents=True, exist_ok=True)
            
            settings = QSettings("LLMChatApp", "Settings")
            settings.setValue("storage/data_root", str(custom_path))
            self.base_data_path = custom_path
            self.is_portable = False
            
    def get_active_settings(self):
        """
        Central function to fetch correct QSettings object.
        If in Portable mode, switches to use an INI file directly in the app folder.
        """
        if not self.base_data_path:
            # Fallback safety check
            self.detect_existing_mode()

        if self.is_portable:
            ini_path = self.get_exe_dir() / "resources" / "settings.ini"
            ini_path.parent.mkdir(parents=True, exist_ok=True)
            return QSettings(str(ini_path), QSettings.IniFormat)
        else:
            return QSettings("LLMChatApp", "Settings")

    def get_storage_root(self) -> Path:
        """Returns final calculated data directory, creates it if missing."""
        if self.base_data_path is None:
            # Force emergency detect just in case
            res = self.detect_existing_mode()
            if res is None:
                # Absolute final fallback is always AppData to prevent crash
                self.base_data_path = self.get_default_app_data_path()
                
        self.base_data_path.mkdir(parents=True, exist_ok=True)
        return self.base_data_path
