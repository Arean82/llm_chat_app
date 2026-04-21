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
    """Copy default resource files from bundle to exe folder on first run"""
    if not getattr(sys, 'frozen', False):
        return
    
    bundle_resources = Path(sys._MEIPASS) / "resources"
    exe_resources = Path(sys.executable).parent / "resources"
    exe_resources.mkdir(parents=True, exist_ok=True)
    
    # Files to copy if missing
    files_to_copy = ['models.json', 'user_prompts.json', 'styles.qss', 'app_icon.png']
    
    for filename in files_to_copy:
        src = bundle_resources / filename
        dst = exe_resources / filename
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    
    # Copy ui_designer .ui files to exe folder (optional, if needed for editing)
    bundle_ui = Path(sys._MEIPASS) / "ui_designer"
    exe_ui = exe_resources.parent / "ui_designer"
    if bundle_ui.exists() and not exe_ui.exists():
        shutil.copytree(bundle_ui, exe_ui)

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