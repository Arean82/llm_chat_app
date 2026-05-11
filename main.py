# main.py
# This is the main entry point for the LLM Chat App. It initializes the application and shows the main window.  

import sys
import os
from pathlib import Path

import shutil

from utils.path_utils import get_resource_path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice

from ui.main_window import MainWindowClass


def smart_sync(src: Path, dst: Path):
    """Only copies src to dst if dst is missing or src is newer/different."""
    if not src.exists():
        return False
    
    should_copy = False
    if not dst.exists():
        should_copy = True
    else:
        # Compare modification times and sizes
        src_stat = src.stat()
        dst_stat = dst.stat()
        if src_stat.st_mtime > dst_stat.st_mtime or src_stat.st_size != dst_stat.st_size:
            should_copy = True
            
    if should_copy:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    return False

def copy_bundled_resources():
    """
    Handles resource synchronization for the EXE environment.
    - System Files: Updated only if the version in the EXE is newer.
    - User Files: Created only if missing.
    """
    if not getattr(sys, 'frozen', False):
        return
    
    try:
        bundle_dir = Path(sys._MEIPASS)
        exe_dir = Path(sys.executable).parent
        
        # 1. SYSTEM FILES & UI DESIGNER: Smart Sync (ensures updates without full wipe)
        system_files = [
            'resources/styles.qss',
            'resources/app_icon.png',
        ]
        
        for rel_path in system_files:
            smart_sync(bundle_dir / rel_path, exe_dir / rel_path)

        # Sync the entire UI designer folder individually
        bundle_ui = bundle_dir / "ui_designer"
        exe_ui = exe_dir / "ui_designer"
        if bundle_ui.exists():
            for src_file in bundle_ui.rglob("*"):
                if src_file.is_file():
                    rel_path = src_file.relative_to(bundle_ui)
                    smart_sync(src_file, exe_ui / rel_path)

        # 2. USER FILES: Only copy if MISSING (protects user work)
        # Dynamically sync any models_*.json files present in bundle
        bundle_res = bundle_dir / "resources"
        exe_res = exe_dir / "resources"
        
        if bundle_res.exists():
            # Find all model manifests
            for src_file in bundle_res.glob("models_*.json"):
                dst_file = exe_res / src_file.name
                if not dst_file.exists():
                    exe_res.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
            
            # Handle specific fallback files
            legacy_files = ['models.json', 'user_prompts.json']
            for fname in legacy_files:
                src = bundle_res / fname
                dst = exe_res / fname
                if src.exists() and not dst.exists():
                    exe_res.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                
    except Exception as e:
        print(f"Resource sync error: {e}")

def main():
    # Explicitly set the AppUserModelID on Windows so the taskbar icon appears instantly and clusters correctly
    import platform
    if platform.system() == "Windows":
        import ctypes
        try:
            myappid = 'arean82.llmchatapp.v5' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    copy_bundled_resources()
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Load stylesheet - use get_resource_path
    stylesheet_path = get_resource_path("resources/styles.qss")
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
            
    # Apply Global Application Icon (fixes taskbar icon before main window spawns)
    from utils.helpers import set_app_icon
    set_app_icon(app) 
    
    window = MainWindowClass()
    window.showMaximized()  
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()