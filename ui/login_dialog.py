# ui/login_dialog.py
# Login dialog for LLM Chat App

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtUiTools import QUiLoader


class SettingsDialogClass(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load UI from .ui file
        loader = QUiLoader()
        ui_file = Path(__file__).parent.parent / "ui_designer" / "login_dialog.ui"
        
        # Load the UI
        self.ui = loader.load(str(ui_file))
        
        # Set the loaded UI as the main layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        # Get references to UI elements
        self.key_input = self.ui.findChild(QLineEdit, "key_input")
        self.save_btn = self.ui.findChild(QPushButton, "save_btn")
        self.cancel_btn = self.ui.findChild(QPushButton, "cancel_btn")
        
        self.setWindowTitle("Settings - NVIDIA NIM API")
        
        self.setup_connections()
        
    def setup_connections(self):
        self.save_btn.clicked.connect(self.save_and_test)
        self.cancel_btn.clicked.connect(self.reject)
        
    def save_and_test(self):
        api_key = self.key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter your NVIDIA NIM API key.")
            return
            
        if not api_key.startswith("nvapi-"):
            QMessageBox.warning(self, "Invalid Format", "API key should start with 'nvapi-'")
            return
            
        self.accept()
        
    def get_api_key(self) -> str:
        return self.key_input.text().strip()
        