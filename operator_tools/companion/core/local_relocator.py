import os
import shutil
import logging
from pathlib import Path

from server.utils.storage_config import StorageManager
from server.utils.path_utils import get_app_settings

logger = logging.getLogger(__name__)

class LocalRelocatorCore:
    """
    Decoupled headless logic for moving local storage directories.
    Returns status tuples: (success: bool, message: str)
    """
    def __init__(self):
        self.storage_mgr = StorageManager.get_instance()
        
    def get_current_root(self) -> Path:
        return self.storage_mgr.get_storage_root()
        
    def calculate_storage_size(self) -> str:
        """Calculate disk footprint of relevant sub-folders."""
        total_size = 0
        targets = ['conversations', 'resources', 'cache', 'vector_db']
        current_root = self.get_current_root()
        
        try:
            for folder in targets:
                folder_path = current_root / folder
                if folder_path.exists():
                    for entry in os.scandir(folder_path):
                        if entry.is_file():
                            total_size += entry.stat().st_size
                        elif entry.is_dir():
                            for sub in os.scandir(entry.path):
                                if sub.is_file():
                                    total_size += sub.stat().st_size
            
            mb = total_size / (1024 * 1024)
            return f"Local Footprint: {mb:.2f} MB used across history and metadata."
        except Exception as e:
            logger.error(f"Failed to calculate storage size: {e}")
            return "Footprint assessment unavailable."

    def execute_migration(self, mode: str, target_path: Path) -> tuple[bool, str]:
        """
        Executes the file migration in a completely headless manner.
        """
        current_root = self.get_current_root()
        
        if target_path.resolve() == current_root.resolve():
            return False, "Destination matches current location. Abandoning migration."
            
        if not self.storage_mgr.check_dir_writable(target_path):
            return False, f"Permission Denied. Target {target_path} is write-protected."
            
        try:
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Include 'vector_db' ensuring user RAG indexes and semantic recall are cloned securely
            payloads = ['conversations', 'resources', 'cache', 'vector_db']
            for p in payloads:
                src = current_root / p
                dst = target_path / p
                if src.exists() and src.is_dir():
                     if dst.exists():
                         shutil.rmtree(dst)
                     shutil.copytree(src, dst)
            
            old_exe_dir = self.storage_mgr.get_exe_dir()
            if self.storage_mgr.is_portable and mode != "PORTABLE":
                portable_marker = old_exe_dir / "portable.txt"
                if portable_marker.exists():
                    try:
                        portable_marker.unlink()
                    except Exception: pass
            
            settings = get_app_settings()
            if mode == "PORTABLE":
                settings.remove("storage/data_root")
            
            self.storage_mgr.finalize_setup(mode, target_path)
            
            return True, f"Migration Complete. System data fully cloned to {target_path}."

        except Exception as e:
            logger.exception("Migration Failure")
            return False, f"Handoff failed: {str(e)}"
