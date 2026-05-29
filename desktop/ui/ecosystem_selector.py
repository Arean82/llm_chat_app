# ui/ecosystem_selector.py
# Ecosystem Selector dialog for hot-swapping AI providers cleanly

import sys
import os
import json
import time
import keyring
from pathlib import Path

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QSettings
from PySide6.QtUiTools import QUiLoader

from server.utils.path_utils import get_resource_path, get_app_settings
from desktop.ui.shared_widgets import set_app_icon
from server.utils.storage_config import StorageManager
from desktop.ui.custom_provider_dialog import CustomProviderDialogClass
from server.utils.security_utils import encrypt_data, decrypt_data
import server.utils.security_utils as security_utils

class EcosystemSelectorClass(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Load base UI layout
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/ecosystem_selector.ui")
        self.ui = loader.load(str(ui_file))
        
        # Mount UI
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        # Window attributes
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        set_app_icon(self)
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        
        # 2. Extract widgets
        self.group_label = self.ui.findChild(QLabel, "group_label")
        self.group_combo = self.ui.findChild(QComboBox, "group_combo")
        
        self.provider_label = self.ui.findChild(QLabel, "provider_label")
        self.provider_combo = self.ui.findChild(QComboBox, "provider_combo")
        
        self.instructions_lbl = self.ui.findChild(QLabel, "instructions")
        self.url_label = self.ui.findChild(QLabel, "url_label")
        self.url_input = self.ui.findChild(QLineEdit, "url_input")
        
        self.key_label = self.ui.findChild(QLabel, "key_label")
        self.key_input = self.ui.findChild(QLineEdit, "key_input")
        
        self.save_btn = self.ui.findChild(QPushButton, "save_btn")
        self.cancel_btn = self.ui.findChild(QPushButton, "cancel_btn")
        
        # Allow links in instruction text
        self.instructions_lbl.setTextFormat(Qt.RichText)
        self.instructions_lbl.setOpenExternalLinks(True)

        # 3. Setup container storage
        self.groups = []
        self.all_providers = []
        self.filtered_providers = []
        self.load_provider_definitions()
        
        self.setWindowTitle("Settings - Ecosystem Configuration")
        self.setup_connections()
        
        # 5. Hydrate state
        self.load_active_state()
        self.showNormal()

    def load_provider_definitions(self):
        """Loads providers registry dynamically, merging custom user add-ons."""
        path = get_resource_path("resources/api_providers.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.groups = data.get("groups", [])
                self.all_providers = data.get("providers", [])
        except Exception as e:
            print(f"WARNING: Failed to load providers map: {e}")
            self.groups = [{"id": "openai", "name": "Core Providers"}]
            self.all_providers = [{
                "id": "openai", "group": "openai", "display_name": "Official OpenAI", 
                "default_url": "https://api.openai.com/v1", "placeholder_key": "sk-"
            }]

        try:
            storage = StorageManager.get_instance().get_storage_root()
            custom_path = storage / "custom_providers.json"
            if custom_path.exists():
                with open(custom_path, "r", encoding="utf-8") as f:
                    c_data = json.load(f)
                    self.all_providers.extend(c_data.get("providers", []))
        except: pass

        self.group_combo.clear()
        for g in self.groups:
            self.group_combo.addItem(g.get("name"), g.get("id"))

    def setup_connections(self):
        self.group_combo.currentIndexChanged.connect(self.on_group_switched)
        self.provider_combo.currentIndexChanged.connect(self.on_provider_switched)
        self.save_btn.clicked.connect(self.save_and_test)
        self.cancel_btn.clicked.connect(self.reject)

    def on_group_switched(self, index):
        if index < 0 or index >= self.group_combo.count():
            return
        
        group_id = self.group_combo.currentData()
        
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        
        self.filtered_providers = [p for p in self.all_providers if p.get("group") == group_id]
        
        for prov in self.filtered_providers:
            self.provider_combo.addItem(prov.get("display_name"), prov.get("id"))
            
        if group_id == "openai":
             self.provider_combo.addItem("➕ Add Custom Endpoint...", "__add_new_custom__")
            
        self.provider_combo.blockSignals(False)
        self.on_provider_switched(0)

    def load_active_state(self):
        settings = get_app_settings()
        active_id = settings.value("active_provider_id", "nvidia")
        
        matched_prov = next((p for p in self.all_providers if p["id"] == active_id), None)
        if not matched_prov:
            self.group_combo.setCurrentIndex(0)
            return
            
        grp_idx = self.group_combo.findData(matched_prov.get("group"))
        if grp_idx != -1:
            self.group_combo.setCurrentIndex(grp_idx)
            
        self.on_group_switched(self.group_combo.currentIndex())
        
        sub_idx = self.provider_combo.findData(active_id)
        if sub_idx != -1:
            self.provider_combo.setCurrentIndex(sub_idx)
        
        self.on_provider_switched(self.provider_combo.currentIndex())

    def on_provider_switched(self, index):
        if index < 0 or index >= self.provider_combo.count():
            return
            
        selected_id = self.provider_combo.currentData()
        
        if selected_id == "__add_new_custom__":
            self._handle_add_custom_provider()
            return
            
        provider = next((p for p in self.filtered_providers if p.get("id") == selected_id), None)
        if not provider:
            return
            
        p_id = provider.get("id")
        
        raw_instructions = provider.get("instructions", "Enter credentials below:")
        pricing = provider.get("pricing", "")
        price_html = f"<p style='color:#00E676; margin-top:5px;'><b>💰 Pricing:</b> {pricing}</p>" if pricing else ""
        
        self.instructions_lbl.setText(f"{raw_instructions}{price_html}")
        self.key_input.setPlaceholderText(provider.get("placeholder_key", "API Key..."))
        
        requires_key = provider.get("requires_key", True)
        self.key_label.setVisible(requires_key)
        self.key_input.setVisible(requires_key)
        self.url_label.setVisible(requires_key)
        
        settings = get_app_settings()
        saved_url = settings.value(f"url_{p_id}", provider.get("default_url"))
        self.url_input.setText(saved_url)
        
        should_show_url = provider.get("requires_url", True)
        self.url_label.setVisible(should_show_url)
        self.url_input.setVisible(should_show_url)

        if requires_key:
            vault_key = f"api_key_{p_id}"
            stored_key = keyring.get_password("LLMChatApp", vault_key)
            
            if not stored_key and p_id == "nvidia":
                stored_key = keyring.get_password("LLMChatApp", "api_key")
            
            # Transparently decrypt key from vault link using session master key
            if stored_key:
                stored_key = decrypt_data(stored_key, security_utils.SESSION_MASTER_PASSWORD)
                
            self.key_input.setText(stored_key or "")
        else:
            self.key_input.setText("LOCAL_ACCESS_NO_KEY")

    def save_and_test(self):
        idx = self.provider_combo.currentIndex()
        if idx < 0: return
        
        provider = self.filtered_providers[idx]
        p_id = provider.get("id")
        requires_key = provider.get("requires_key", True)
        
        api_key = self.key_input.text().strip()
        base_url = self.url_input.text().strip()

        if requires_key and not api_key:
            QMessageBox.warning(self, "Missing Credential", f"Please supply an API Token for {provider.get('display_name')}.")
            return
            
        settings = get_app_settings()
        settings.setValue("active_provider_id", p_id)
        settings.setValue(f"url_{p_id}", base_url)
        settings.setValue("base_url", base_url)
        settings.sync()
        
        if requires_key:
            # Transparently encrypt key using session master password before saving to keyring
            enc_key = encrypt_data(api_key, security_utils.SESSION_MASTER_PASSWORD)
            
            keyring.set_password("LLMChatApp", f"api_key_{p_id}", enc_key)
            keyring.set_password("LLMChatApp", "api_key", enc_key)
            
            sdk = provider.get("sdk", "openai")
            eco_name = provider.get("display_name", p_id)
            eco_key = eco_name.lower().replace(' ', '_')
            modern_key_id = f"api_key_{sdk}_{eco_key}"
            keyring.set_password("LLMChatApp", modern_key_id, enc_key)
        else:
            try:
                keyring.delete_password("LLMChatApp", f"api_key_{p_id}")
            except: pass

        self.accept()

    def _handle_add_custom_provider(self):
        dialog = CustomProviderDialogClass(self)
        if dialog.exec():
            new_payload = dialog.get_provider_payload()
            if not new_payload: return
            
            storage = StorageManager.get_instance().get_storage_root()
            custom_path = storage / "custom_providers.json"
            
            existing_list = []
            if custom_path.exists():
                try:
                    with open(custom_path, "r") as f:
                        c_data = json.load(f)
                        existing_list = c_data.get("providers", [])
                except: pass
            
            if any(p["id"] == new_payload["id"] for p in existing_list):
                 new_payload["id"] += f"_{int(time.time())}"

            existing_list.append(new_payload)
            
            try:
                with open(custom_path, "w", encoding="utf-8") as f:
                    json.dump({"providers": existing_list}, f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Storage Error", f"Failed to save custom data: {e}")
                return
            
            try:
                from PySide6.QtWidgets import QApplication
                from PySide6.QtCore import Qt
                from server.logic.llm_client import LLMClient
                from server.logic.model_io import save_all_models, load_all_models
                
                QApplication.setOverrideCursor(Qt.WaitCursor)
                temp_client = LLMClient()
                custom_models = temp_client.fetch_custom_openai_models(
                    base_url=new_payload.get("default_url"),
                    api_key="", 
                    provider_id=new_payload["id"]
                )
                
                if custom_models:
                    current_all = load_all_models()
                    ex_ids = {m.get("id") for m in current_all}
                    to_add = [m for m in custom_models if m.get("id") not in ex_ids]
                    if to_add:
                         current_all.extend(to_add)
                         save_all_models(current_all)
                         
            except Exception as scan_ex:
                 print(f"Background automatic model harvest bypassed: {scan_ex}")
            finally:
                 QApplication.restoreOverrideCursor()

            self.load_provider_definitions()
            self.on_group_switched(self.group_combo.currentIndex())
            
            new_idx = self.provider_combo.findData(new_payload["id"])
            if new_idx != -1:
                self.provider_combo.setCurrentIndex(new_idx)

    def get_active_provider_id(self) -> str:
        return self.provider_combo.currentData()

    def get_api_key(self) -> str:
        return self.key_input.text().strip()

    def get_google_api_key(self) -> str:
        if self.get_active_provider_id() == "google":
            return self.key_input.text().strip()
        return ""

    def get_base_url(self) -> str:
        return self.url_input.text().strip()
