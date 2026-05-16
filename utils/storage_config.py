# utils/storage_config.py
import sys
import os
from pathlib import Path
from utils.config_loader import JSONSettings

class StorageManager:
    _instance = None
    _initialized = False
    
    def __init__(self):
        self.base_data_path = None
        self.is_portable = False
        self._settings = None
        
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
        return Path.home() / "LLMChatApp"

    def detect_existing_mode(self) -> Path:
        """Determines path based on environment indicators."""
        if not getattr(sys, 'frozen', False):
            self.is_portable = True 
            self.base_data_path = self.get_exe_dir()
            return self.base_data_path

        exe_dir = self.get_exe_dir()
        if (exe_dir / "portable.txt").exists():
            self.is_portable = True
            self.base_data_path = exe_dir
            return self.base_data_path
            
        if not self.check_dir_writable(exe_dir):
            self.is_portable = False
            self.base_data_path = self.get_default_app_data_path()
            return self.base_data_path
            
        settings = self.get_active_settings()
        saved_path = settings.value("storage/data_root", None)
        if saved_path:
            saved_path_obj = Path(saved_path)
            try:
                saved_path_obj.mkdir(parents=True, exist_ok=True)
                self.is_portable = False
                self.base_data_path = saved_path_obj
                return self.base_data_path
            except Exception:
                pass
        return None

    def finalize_setup(self, selected_mode: str, custom_path: Path = None):
        exe_dir = self.get_exe_dir()
        if selected_mode == "PORTABLE":
            (exe_dir / "portable.txt").touch()
            self.base_data_path = exe_dir
            self.is_portable = True
        elif selected_mode == "APPDATA":
            path = self.get_default_app_data_path()
            path.mkdir(parents=True, exist_ok=True)
            settings = self.get_active_settings()
            settings.setValue("storage/data_root", str(path))
            self.base_data_path = path
            self.is_portable = False
        elif selected_mode == "CUSTOM" and custom_path:
            custom_path.mkdir(parents=True, exist_ok=True)
            settings = self.get_active_settings()
            settings.setValue("storage/data_root", str(custom_path))
            self.base_data_path = custom_path
            self.is_portable = False
            
    def get_active_settings(self):
        """Fetch the JSON-based settings manager."""
        if self._settings: return self._settings
        if self.is_portable or (self.get_exe_dir() / "portable.txt").exists():
            config_path = self.get_exe_dir() / "config.json"
        else:
            config_path = self.get_default_app_data_path() / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings = JSONSettings(config_path)
        return self._settings

    def get_storage_root(self) -> Path:
        if self.base_data_path is None:
            res = self.detect_existing_mode()
            if res is None:
                self.base_data_path = self.get_default_app_data_path()
        self.base_data_path.mkdir(parents=True, exist_ok=True)
        return self.base_data_path
