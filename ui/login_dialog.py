# ui/login_dialog.py
# Login dialog for LLM Chat App

import sys
import os
from pathlib import Path

from utils.path_utils import get_resource_path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtUiTools import QUiLoader


class SettingsDialogClass(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load UI from .ui file
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/login_dialog.ui")
        
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
        
        # --- ADDED: Base URL Field ---
        from PySide6.QtCore import QSettings
        settings = QSettings("LLMChatApp", "Settings")
        saved_url = settings.value("base_url", "https://integrate.api.nvidia.com/v1")
        saved_key = settings.value("api_key", "")

        self.url_label = QLabel("API Base URL:")
        self.url_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.url_input = QLineEdit()
        self.url_input.setText(saved_url)
        self.url_input.setPlaceholderText("https://integrate.api.nvidia.com/v1")
        self.url_input.setStyleSheet("""
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3c3c3c;
            border-radius: 5px;
            padding: 8px;
        """)

        # Insert into the layout (after instructions, before key_label)
        layout = self.ui.findChild(QVBoxLayout, "dialog_layout")
        if layout:
            # Index 1 is after instructions label
            layout.insertWidget(1, self.url_label)
            layout.insertWidget(2, self.url_input)

        if saved_key:
            self.key_input.setText(saved_key)

        self.setWindowTitle("Settings - LLM Configuration")
        
        self.setup_connections()
        
    def setup_connections(self):
        self.save_btn.clicked.connect(self.save_and_test)
        self.cancel_btn.clicked.connect(self.reject)
        
    def save_and_test(self):
        api_key = self.key_input.text().strip()
        base_url = self.url_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter your API key.")
            return
            
        if not base_url:
            QMessageBox.warning(self, "Missing Base URL", "Please enter the API base URL.")
            return

        # Optional: Warn if it's NVIDIA but key doesn't match, 
        # but don't hard block for other providers.
        if "nvidia.com" in base_url and not api_key.startswith("nvapi-"):
            reply = QMessageBox.question(
                self, "Unexpected Format", 
                "NVIDIA NIM keys usually start with 'nvapi-'. Proceed anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            
        from PySide6.QtCore import QSettings
        settings = QSettings("LLMChatApp", "Settings")
        settings.setValue("api_key", api_key)
        settings.setValue("base_url", base_url)

        self.accept()
        
    def get_api_key(self) -> str:
        return self.key_input.text().strip()

    def get_base_url(self) -> str:
        return self.url_input.text().strip()
        