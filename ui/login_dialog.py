# ui/login_dialog.py
# Overhauled Multi-Provider Login system

import sys
import os
import json
import time
import keyring
from pathlib import Path

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QSettings
from PySide6.QtUiTools import QUiLoader

from utils.path_utils import get_resource_path, get_app_settings
from ui.shared_widgets import set_app_icon
from utils.storage_config import StorageManager
from ui.custom_provider_dialog import CustomProviderDialogClass

class LoginDialogClass(QDialog):
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
        
        # Standard window setup
        
        # 2. Map internal elements from UI
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
        
        # Allow opening links in instructions natively
        
        # Allow opening links in instructions natively
        self.instructions_lbl.setTextFormat(Qt.RichText)
        self.instructions_lbl.setOpenExternalLinks(True)

        # 3. Setup container storage
        self.groups = []
        self.all_providers = []
        self.filtered_providers = []
        self.load_provider_definitions()
        
        self.setWindowTitle("Settings - Expanded AI Configuration")
        self.setup_connections()
        
        # 5. Hydrate initial user state
        self.load_active_state()
        self.showNormal()

    def load_provider_definitions(self):
        """Loads and parses complex hierarchical list of active API providers inclusive of dynamic user add-ons."""
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

        # DYNAMIC MIGRATION: Load user-added local endpoints securely from storage pool
        try:
            storage = StorageManager.get_instance().get_storage_root()
            custom_path = storage / "custom_providers.json"
            if custom_path.exists():
                with open(custom_path, "r", encoding="utf-8") as f:
                    c_data = json.load(f)
                    # Merge verified custom items back to live pool
                    self.all_providers.extend(c_data.get("providers", []))
        except: pass

        # Populate Groups combo box
        self.group_combo.clear()
        for g in self.groups:
            self.group_combo.addItem(g.get("name"), g.get("id"))

    def setup_connections(self):
        # Primary trigger: Change ecosystem -> Filters available service list
        self.group_combo.currentIndexChanged.connect(self.on_group_switched)
        
        # Secondary trigger: Change specific service -> Updates specific form context
        self.provider_combo.currentIndexChanged.connect(self.on_provider_switched)
        
        # Actions
        self.save_btn.clicked.connect(self.save_and_test)
        self.cancel_btn.clicked.connect(self.reject)

    def on_group_switched(self, index):
        """Filters list of sub-providers whenever the Architecture Group shifts."""
        if index < 0 or index >= self.group_combo.count():
            return
        
        group_id = self.group_combo.currentData()
        
        # Block signals while repopulating provider combo to avoid intermediate glitches
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        
        
        self.filtered_providers = [p for p in self.all_providers if p.get("group") == group_id]
        
        for prov in self.filtered_providers:
            self.provider_combo.addItem(prov.get("display_name"), prov.get("id"))
            
        # Dynamic Addition Prompt: Only append the 'Add Custom' capability to generic OpenAI endpoints
        if group_id == "openai":
             self.provider_combo.addItem("➕ Add Custom Endpoint...", "__add_new_custom__")
            
        self.provider_combo.blockSignals(False)
        
        # Automatically trigger hydration of first sub-element
        self.on_provider_switched(0)

    def load_active_state(self):
        """Intelligently identifies historical group mappings to restore full cascade state."""
        settings = get_app_settings()
        active_id = settings.value("active_provider_id", "nvidia")
        
        # 1. Locate actual provider details to discover its root group
        matched_prov = next((p for p in self.all_providers if p["id"] == active_id), None)
        if not matched_prov:
            # Fallback safely
            self.group_combo.setCurrentIndex(0)
            return
            
        # 2. Restore appropriate Ecosystem Group combo index
        grp_idx = self.group_combo.findData(matched_prov.get("group"))
        if grp_idx != -1:
            self.group_combo.setCurrentIndex(grp_idx)
            
        # NOTE: Modifying group_combo above triggers `on_group_switched` synchronously,
        # which has filled `self.filtered_providers` and `self.provider_combo` by now.
        
        # 3. Target the precise provider sub-element
        sub_idx = self.provider_combo.findData(active_id)
        if sub_idx != -1:
            self.provider_combo.setCurrentIndex(sub_idx)
        
        # Complete final field hydration
        self.on_provider_switched(self.provider_combo.currentIndex())

    def on_provider_switched(self, index):
        """Instantly updates context labels and rehydrates input fields on dropdown change."""
        if index < 0 or index >= self.provider_combo.count():
            return
            
        selected_id = self.provider_combo.currentData()
        
        # Detect specialized triggering token for spawning extension dialogs
        if selected_id == "__add_new_custom__":
            self._handle_add_custom_provider()
            return
            
        # Safe lookup provider definition from our isolated sub-registry
        provider = next((p for p in self.filtered_providers if p.get("id") == selected_id), None)
        if not provider:
            return
            
        p_id = provider.get("id")
        
        # 1. Setup Visual Context & Pricing Tag
        raw_instructions = provider.get("instructions", "Enter credentials below:")
        pricing = provider.get("pricing", "")
        price_html = f"<p style='color:#00E676; margin-top:5px;'><b>💰 Pricing:</b> {pricing}</p>" if pricing else ""
        
        self.instructions_lbl.setText(f"{raw_instructions}{price_html}")
        self.key_input.setPlaceholderText(provider.get("placeholder_key", "API Key..."))
        
        # 2. Smart Key Visibility Enforcement (Support for Ollama/Zero-Key local mode)
        requires_key = provider.get("requires_key", True)
        self.key_label.setVisible(requires_key)
        self.key_input.setVisible(requires_key)
        self.url_label.setVisible(requires_key) # Show URL if it's not a local provider
        
        # 3. Rehydrate URL field for THIS provider
        settings = get_app_settings()
        saved_url = settings.value(f"url_{p_id}", provider.get("default_url"))
        self.url_input.setText(saved_url)
        
        should_show_url = provider.get("requires_url", True)
        self.url_label.setVisible(should_show_url)
        self.url_input.setVisible(should_show_url)

        # 4. Retrieve Vault credentials only if a key makes sense
        if requires_key:
            vault_key = f"api_key_{p_id}"
            stored_key = keyring.get_password("LLMChatApp", vault_key)
            
            # Handle legacy migration check
            if not stored_key and p_id == "nvidia":
                stored_key = keyring.get_password("LLMChatApp", "api_key")
            self.key_input.setText(stored_key or "")
        else:
            self.key_input.setText("LOCAL_ACCESS_NO_KEY") # Non-empty bypass for backward logics

    def save_and_test(self):
        """Persists localized variables, observing adaptive validation heuristics."""
        idx = self.provider_combo.currentIndex()
        if idx < 0: return
        
        provider = self.filtered_providers[idx]
        p_id = provider.get("id")
        requires_key = provider.get("requires_key", True)
        
        api_key = self.key_input.text().strip()
        base_url = self.url_input.text().strip()

        # Conditional validation check
        if requires_key and not api_key:
            QMessageBox.warning(self, "Missing Credential", f"Please supply an API Token for {provider.get('display_name')}.")
            return
            
        settings = get_app_settings()
        
        # 1. Persist active provider slug globally
        settings.setValue("active_provider_id", p_id)
        
        # 2. Persist specific localized endpoint
        settings.setValue(f"url_{p_id}", base_url)
        # Ensure legacy fallback is maintained for compatibility with existing systems
        settings.setValue("base_url", base_url)
        
        # 3. Inject token into OS vault ONLY if strictly required, else strip to preserve hygiene
        if requires_key:
            keyring.set_password("LLMChatApp", f"api_key_{p_id}", api_key)
            keyring.set_password("LLMChatApp", "api_key", api_key)
        else:
            # Clear any legacy clutter if switching to local provider
            try:
                keyring.delete_password("LLMChatApp", f"api_key_{p_id}")
            except: pass

        self.accept()

    def _handle_add_custom_provider(self):
        """Spawns clean dialog, captures result, writes to writable disk storage, and refreshes UI."""
        dialog = CustomProviderDialogClass(self)
        if dialog.exec():
            new_payload = dialog.get_provider_payload()
            if not new_payload: return
            
            # 1. Persist directly to disk immediately
            storage = StorageManager.get_instance().get_storage_root()
            custom_path = storage / "custom_providers.json"
            
            existing_list = []
            if custom_path.exists():
                try:
                    with open(custom_path, "r") as f:
                        c_data = json.load(f)
                        existing_list = c_data.get("providers", [])
                except: pass
            
            # Avoid duplicates
            if any(p["id"] == new_payload["id"] for p in existing_list):
                 new_payload["id"] += f"_{int(time.time())}" # simple collision avoidance

            existing_list.append(new_payload)
            
            try:
                with open(custom_path, "w", encoding="utf-8") as f:
                    json.dump({"providers": existing_list}, f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Storage Error", f"Failed to save custom data: {e}")
                return
            
            # 1.5 UNIVERSAL DISCOVERY INJECTION (Audit ID 024)
            # Proactively scan endpoint for supported model IDs seamlessly upon creation.
            try:
                from PySide6.QtWidgets import QApplication
                from PySide6.QtCore import Qt
                from logic.llm_client import LLMClient
                from logic.model_io import save_all_models, load_all_models
                
                QApplication.setOverrideCursor(Qt.WaitCursor)
                temp_client = LLMClient()
                # Try with minimal security (works for 90% of local dev servers like LM Studio/Ollama)
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
                 print(f"Background automatic model harvest bypassed (Endpoint might require explicit auth): {scan_ex}")
            finally:
                 QApplication.restoreOverrideCursor()

            # 2. Hot Reload state entirely to render instantly
            self.load_provider_definitions()
            # Force current group select trigger to re-run the filter
            self.on_group_switched(self.group_combo.currentIndex())
            
            # 3. Automatically select the newly created item
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
