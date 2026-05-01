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


def copy_bundled_resources():
    """
    Handles resource synchronization for the EXE environment.
    - System Files (Styles, UI): Always updated to match the EXE version.
    - User Files (Prompts, Models): Only created if missing to protect user data.
    """
    if not getattr(sys, 'frozen', False):
        return
    
    try:
        bundle_dir = Path(sys._MEIPASS)
        exe_dir = Path(sys.executable).parent
        
        # 1. Ensure directories exist
        (exe_dir / "resources").mkdir(parents=True, exist_ok=True)
        (exe_dir / "ui_designer").mkdir(parents=True, exist_ok=True)

        # 2. SYSTEM FILES: Always Overwrite (ensures design updates)
        system_files = [
            ('resources/styles.qss', 'resources/styles.qss'),
            ('resources/app_icon.png', 'resources/app_icon.png'),
        ]
        
        for rel_src, rel_dst in system_files:
            src = bundle_dir / rel_src
            dst = exe_dir / rel_dst
            if src.exists():
                shutil.copy2(src, dst)

        # 3. UI DESIGNER: Always Overwrite the whole folder
        bundle_ui = bundle_dir / "ui_designer"
        exe_ui = exe_dir / "ui_designer"
        if bundle_ui.exists():
            # Remove old UI folder to ensure a clean sync
            if exe_ui.exists():
                shutil.rmtree(exe_ui)
            shutil.copytree(bundle_ui, exe_ui)

        # 4. USER FILES: Only copy if MISSING (protects user work)
        user_files = [
            ('resources/models.json', 'resources/models.json'),
            ('resources/user_prompts.json', 'resources/user_prompts.json'),
        ]
        
        for rel_src, rel_dst in user_files:
            src = bundle_dir / rel_src
            dst = exe_dir / rel_dst
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                
    except Exception as e:
        print(f"Resource sync error: {e}")

def main():
    copy_bundled_resources()
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Load stylesheet - use get_resource_path
    stylesheet_path = get_resource_path("resources/styles.qss")
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    
    window = MainWindowClass()
    window.showMaximized()  
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()