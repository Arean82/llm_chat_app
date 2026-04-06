# ui/settings_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - NVIDIA NIM API")
        self.setMinimumWidth(500)
        self.api_key = ""
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Enter your NVIDIA NIM API Key\n\n"
            "How to get a free API key:\n"
            "1. Go to https://build.nvidia.com\n"
            "2. Sign up for a free developer account\n"
            "3. Go to Settings → API Keys\n"
            "4. Click 'Generate API Key'\n"
            "5. Copy your key (starts with nvapi-)\n\n"
            "Free tier: 40 requests per minute, unlimited tokens"
        )
        instructions.setWordWrap(True)
        instructions.setObjectName("instructions")
        layout.addWidget(instructions)
        
        # API Key input
        key_label = QLabel("API Key:")
        key_label.setObjectName("key-label")
        layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("nvapi-xxxxxxxxxxxxxxxx")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setObjectName("key-input")
        layout.addWidget(self.key_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save & Test")
        self.save_btn.clicked.connect(self.save_and_test)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
    def save_and_test(self):
        """Save API key and test connection"""
        api_key = self.key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Missing API Key", "Please enter your NVIDIA NIM API key.")
            return
            
        if not api_key.startswith("nvapi-"):
            QMessageBox.warning(self, "Invalid Format", "API key should start with 'nvapi-'")
            return
            
        self.api_key = api_key
        self.accept()
        
    def get_api_key(self) -> str:
        """Return the saved API key"""
        return self.api_key