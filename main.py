# main.py
# This is the main entry point for the LLM Chat App. It initializes the application and shows the main window.  

import sys
import os
from pathlib import Path

from utils.path_utils import get_resource_path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice

from ui.main_window import MainWindowClass

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Load stylesheet
    #stylesheet_path = Path(__file__).parent / "resources" / "styles.qss"
    stylesheet_path = get_resource_path("resources/styles.qss")
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    
    window = MainWindowClass()
    #window.show()
    window.showMaximized()  
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()