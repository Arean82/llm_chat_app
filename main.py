# main.py
# This is the entry point of the application. It initializes the QApplication, sets up the main window, and starts the event loop.  

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Load stylesheet from ui directory
    from ui.styles import load_stylesheet
    app.setStyleSheet(load_stylesheet())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()