# ui/login_dialog.py
# Overhauled Multi-Provider Login system

import sys
import os
import json
import keyring
from pathlib import Path

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QSettings
from PySide6.QtUiTools import QUiLoader

from utils.path_utils import get_resource_path
from utils.helpers import set_app_icon

class SettingsDialogClass(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Load base UI skeleton
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/login_dialog.ui")
        self.ui = loader.load(str(ui_file))
        
        # Mount UI
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        # Apply standard restrictive OS Window flags and styling hooks
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        set_app_icon(self)
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        
        # 2. Map internal elements
        self.provider_combo = self.ui.findChild(QComboBox, "provider_combo")
        self.instructions_lbl = self.ui.findChild(QLabel, "instructions")
        self.key_input = self.ui.findChild(QLineEdit, "key_input")
        self.save_btn = self.ui.findChild(QPushButton, "save_btn")
        self.cancel_btn = self.ui.findChild(QPushButton, "cancel_btn")
        
        # Allow opening links in instructions natively
        self.instructions_lbl.setTextFormat(Qt.RichText)
        self.instructions_lbl.setOpenExternalLinks(True)

        # 3. Dynamically inject Base URL field behind dynamic UI logic
        self.url_label = QLabel("API Base URL:")
        self.url_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.url_input = QLineEdit()
        self.url_input.setStyleSheet("""
            background-color: #2d2d2d; color: #ffffff;
            border: 1px solid #3c3c3c; border-radius: 5px; padding: 8px;
        """)
        
        # Find main layout to insert visual URL block after instructions
        inner_layout = self.ui.findChild(QVBoxLayout, "dialog_layout")
        if inner_layout:
            # Insert below instructions (at position 3 to clear provider components)
            inner_layout.insertWidget(3, self.url_label)
            inner_layout.insertWidget(4, self.url_input)

        # 4. Load Providers JSON & Bootstrap components
        self.providers = []
        self.load_provider_definitions()
        
        self.setWindowTitle("Settings - LLM Configuration")
        self.setup_connections()
        
        # 5. Hydrate initial user state
        self.load_active_state()
        self.showNormal()

    def load_provider_definitions(self):
        """Loads and parses list of active API providers dynamically."""
        path = get_resource_path("resources/api_providers.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.providers = data.get("providers", [])
        except Exception as e:
            print(f"WARNING: Failed to load providers map: {e}")
            self.providers = [{
                "id": "nvidia", "display_name": "NVIDIA NIM (Default)", 
                "default_url": "https://integrate.api.nvidia.com/v1", "placeholder_key": "nvapi-"
            }]

        # Populate combo box
        self.provider_combo.clear()
        for prov in self.providers:
            self.provider_combo.addItem(prov.get("display_name"), prov.get("id"))

    def setup_connections(self):
        # React on switch
        self.provider_combo.currentIndexChanged.connect(self.on_provider_switched)
        # Actions
        self.save_btn.clicked.connect(self.save_and_test)
        self.cancel_btn.clicked.connect(self.reject)

    def load_active_state(self):
        """Restores existing persistence layer state upon dialog load."""
        settings = QSettings("LLMChatApp", "Settings")
        active_id = settings.value("active_provider_id", "nvidia")
        
        # Find index of previous provider
        idx = self.provider_combo.findData(active_id)
        if idx != -1:
            self.provider_combo.setCurrentIndex(idx)
        else:
            self.provider_combo.setCurrentIndex(0)

        # Force hydration trigger just in case it didn't flip
        self.on_provider_switched(self.provider_combo.currentIndex())

    def on_provider_switched(self, index):
        """Instantly updates context labels and rehydrates input fields on dropdown change."""
        if index < 0 or index >= len(self.providers):
            return
            
        provider = self.providers[index]
        p_id = provider.get("id")
        
        # 1. Setup Visual Context Instructions
        self.instructions_lbl.setText(provider.get("instructions", "Enter credentials below:"))
        self.key_input.setPlaceholderText(provider.get("placeholder_key", "API Key..."))
        
        # 2. Rehydrate URL field for THIS provider
        settings = QSettings("LLMChatApp", "Settings")
        # Unique storage key ensures URLs aren't mixed
        saved_url = settings.value(f"url_{p_id}", provider.get("default_url"))
        self.url_input.setText(saved_url)
        
        # Hide URL field if explicitly designated not required for simplifying view
        should_show_url = provider.get("requires_url", True)
        self.url_label.setVisible(should_show_url)
        self.url_input.setVisible(should_show_url)

        # 3. Retrieve UNIQUE credentials stored in keyring mapped strictly by provider slug
        # Keyring name: LLMChatApp_nvidia_key OR LLMChatApp_google_key
        vault_key = f"api_key_{p_id}"
        
        # Handle legacy migration check ONLY if this is Nvidia and new key is missing
        stored_key = keyring.get_password("LLMChatApp", vault_key)
        
        if not stored_key and p_id == "nvidia":
            # Check for OLD root key from previous app versions
            stored_key = keyring.get_password("LLMChatApp", "api_key")

        self.key_input.setText(stored_key or "")

    def save_and_test(self):
        """Persists localized variables and confirms authentication."""
        idx = self.provider_combo.currentIndex()
        if idx < 0: return
        
        provider = self.providers[idx]
        p_id = provider.get("id")
        
        api_key = self.key_input.text().strip()
        base_url = self.url_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Missing Credential", "Please supply valid API Authentication to continue.")
            return
            
        settings = QSettings("LLMChatApp", "Settings")
        
        # 1. Persist active provider slug globally
        settings.setValue("active_provider_id", p_id)
        
        # 2. Persist specific localized endpoint
        settings.setValue(f"url_{p_id}", base_url)
        # Ensure legacy fallback is maintained for total continuity across current logics
        settings.setValue("base_url", base_url)
        
        # 3. Inject unique API token into system vault for THIS specific provider
        keyring.set_password("LLMChatApp", f"api_key_{p_id}", api_key)
        
        # Backwards compatibility: Write back to main logical handler so LLMClient doesn't break immediately
        keyring.set_password("LLMChatApp", "api_key", api_key)

        self.accept()
        
    def get_active_provider_id(self) -> str:
        return self.provider_combo.currentData()

    def get_api_key(self) -> str:
        return self.key_input.text().strip()

    def get_base_url(self) -> str:
        return self.url_input.text().strip()