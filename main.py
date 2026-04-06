# main.py
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice

from ui.main_window import MainWindowClass


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Load stylesheet
    stylesheet_path = Path(__file__).parent / "resources" / "styles.qss"
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    
    window = MainWindowClass()
    window.showMaximized()  # <-- ONLY THIS LINE HERE, nothing else
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()