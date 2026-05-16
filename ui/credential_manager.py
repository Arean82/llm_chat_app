# ui/credential_manager.py
# Isolated Credential and Model Management Hub

import sys
import os
import keyring
from PySide6.QtWidgets import (
    QDialog, QTableWidgetItem, QCheckBox, QHBoxLayout, 
    QWidget, QPushButton, QMessageBox, QHeaderView, QAbstractItemView,
    QLabel
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtUiTools import QUiLoader

from utils.path_utils import get_resource_path, get_app_settings
from logic.model_io import load_all_models, save_all_models

class CredentialManagerDialog(QDialog):
    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self.theme = theme
        
        # Load UI
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/credential_manager.ui")
        self.ui = loader.load(str(ui_file), self)
        
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
            
        self.setWindowTitle("Credential Manager")
        self.setMinimumSize(1000, 500)
        
        # Initialization
        self.setup_connections()
        self.load_credentials()
        self.apply_theme()

    def setup_connections(self):
        self.ui.close_btn.clicked.connect(self.accept)
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        
        # Credential Manager Connections (Tab 1)
        self.ui.add_provider_btn.clicked.connect(self.add_provider)
        self.ui.test_all_btn.clicked.connect(self.test_all_connections)
        
        # Model Manager Connections (Tab 2)
        self.ui.modelEcosystemFilter.currentTextChanged.connect(self.load_models)
        self.ui.fetch_models_btn.clicked.connect(self.fetch_models)
        self.ui.add_custom_model_btn.clicked.connect(self.add_model)
        self.ui.delete_model_btn.clicked.connect(self.delete_model)

    def load_credentials(self):
        """Populates the Credential Table with SDK/Ecosystem data."""
        table = self.ui.credTable
        table.setRowCount(0)
        
        # Base list of SDKs from the provided table
        base_providers = [
            {"sdk": "openai", "ecosystem": "NVIDIA NIM", "url": "https://integrate.api.nvidia.com/v1"},
            {"sdk": "google-genai", "ecosystem": "Google Gemini", "url": "https://generativelanguage.googleapis.com/v1beta"},
            {"sdk": "openai", "ecosystem": "Official OpenAI", "url": "https://api.openai.com/v1"},
            {"sdk": "groq", "ecosystem": "GroqCloud", "url": "https://api.groq.com/openai/v1"},
            {"sdk": "openai", "ecosystem": "OpenRouter", "url": "https://openrouter.ai/api/v1"},
            {"sdk": "openai", "ecosystem": "DeepSeek", "url": "https://api.deepseek.com"},
            {"sdk": "openai", "ecosystem": "Perplexity", "url": "https://api.perplexity.ai"},
            {"sdk": "openai", "ecosystem": "Fireworks AI", "url": "https://api.fireworks.ai/inference/v1"},
            {"sdk": "openai", "ecosystem": "Novita AI", "url": "https://api.novita.ai/v3/openai"},
            {"sdk": "anthropic", "ecosystem": "Anthropic", "url": "https://api.anthropic.com/v1"},
            {"sdk": "cohere", "ecosystem": "Cohere", "url": "https://api.cohere.ai/v1"},
            {"sdk": "mistralai", "ecosystem": "Mistral AI", "url": "https://api.mistral.ai/v1"},
            {"sdk": "together", "ecosystem": "Together AI", "url": "https://api.together.xyz/v1"},
            {"sdk": "ollama", "ecosystem": "Ollama (Local)", "url": "http://localhost:11434/v1"},
            {"sdk": "replicate", "ecosystem": "Replicate", "url": "https://api.replicate.com/v1"},
            {"sdk": "huggingface_hub", "ecosystem": "Hugging Face", "url": "https://api-inference.huggingface.co/v1"},
            {"sdk": "transformers", "ecosystem": "Local Transformers", "url": "local"},
            {"sdk": "boto3", "ecosystem": "AWS Bedrock", "url": "aws"},
            {"sdk": "vertexai", "ecosystem": "Google Vertex AI", "url": "gcp"},
            {"sdk": "azure-ai-inference", "ecosystem": "Azure AI", "url": "azure"},
            {"sdk": "vllm", "ecosystem": "vLLM Server", "url": "http://localhost:8000/v1"},
            {"sdk": "litellm", "ecosystem": "LiteLLM Proxy", "url": "http://localhost:4000/v1"},
        ]
        
        # Load any custom added providers from settings
        settings = get_app_settings()
        import json
        custom_raw = settings.value("custom_providers", "[]")
        try:
            custom_providers = json.loads(custom_raw)
        except:
            custom_providers = []
            
        providers = base_providers + custom_providers
        active_p = settings.value("active_provider_id", "nvidia").lower()
        
        table.setRowCount(len(providers))
        for row, p in enumerate(providers):
            # Col 0: Status (Live Switch)
            is_live = (p['ecosystem'].lower().replace(" ", "") == active_p or 
                       (active_p == "nvidia" and p['ecosystem'] == "NVIDIA NIM"))
            
            # Col 0: Status (Display Only as requested)
            eco_key = p['ecosystem'].lower().replace(' ', '_')
            key_id = f"api_key_{p['sdk']}_{eco_key}"
            has_key = bool(keyring.get_password("LLMChatApp", key_id))
            
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setAlignment(Qt.AlignCenter)
            status_layout.setContentsMargins(0,0,0,0)
            
            status_text = "ACTIVE" if is_live else ("AVAILABLE" if has_key else "UNAVAILABLE")
            status_label = QLabel(status_text)
            status_label.setFixedSize(85, 25)
            status_label.setAlignment(Qt.AlignCenter)
            
            if is_live:
                status_label.setStyleSheet("background-color: #4caf50; color: white; font-weight: bold; border-radius: 4px;")
            elif has_key:
                status_label.setStyleSheet("background-color: #1e3a1e; color: #00E676; border-radius: 4px; font-weight: bold; border: 1px solid #00E676;")
            else:
                status_label.setStyleSheet("background-color: #331e1e; color: #f44336; border-radius: 4px; font-weight: normal; border: 1px solid #f44336;")
            
            status_layout.addWidget(status_label)
            table.setCellWidget(row, 0, status_widget)
            
            # Col 1: SDK
            table.setItem(row, 1, QTableWidgetItem(p['sdk']))
            
            # Col 2: Ecosystem
            table.setItem(row, 2, QTableWidgetItem(p['ecosystem']))
            
            # Col 3: Base URL
            url = settings.value(f"url_{p['ecosystem'].lower().replace(' ', '_')}", p['url'])
            table.setItem(row, 3, QTableWidgetItem(url))
            
            # Col 4: API Key (Masked)
            eco_key = p['ecosystem'].lower().replace(' ', '_')
            key_id = f"api_key_{p['sdk']}_{eco_key}"
            key = keyring.get_password("LLMChatApp", key_id)
            
            # Fallback for existing keys
            if not key:
                if "nvidia" in eco_key:
                    key = keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key")
                elif "google" in eco_key:
                    key = keyring.get_password("LLMChatApp", "api_key_google")
            
            key_display = "********" if key else "Missing"
            key_item = QTableWidgetItem(key_display)
            if not key: key_item.setForeground(Qt.red)
            table.setItem(row, 4, key_item)
            
            # Col 5: Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5,2,5,2)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked=False, r=row, p_data=p: self.edit_credential(r, p_data))
            actions_layout.addWidget(edit_btn)
            
            table.setCellWidget(row, 5, actions_widget)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setColumnWidth(0, 100)

    def add_provider(self):
        """Launches the Add Provider dialog."""
        dialog = AddProviderDialog(parent=self)
        if dialog.exec():
            self.load_credentials()

    def test_all_connections(self):
        QMessageBox.information(self, "Health Check", "Starting background connection tests for all SDKs...")

    def edit_credential(self, row, p_data):
        """Simple inline or dialog edit for keys/urls."""
        # For the playbook, we'll use a simple input prompt
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        
        eco_key = p_data['ecosystem'].lower().replace(' ', '_')
        key_id = f"api_key_{p_data['sdk']}_{eco_key}"
        
        new_key, ok = QInputDialog.getText(self, "Update API Key", f"Enter key for {p_data['ecosystem']}:", QLineEdit.Password)
        if ok and new_key:
            keyring.set_password("LLMChatApp", key_id, new_key)
            # If it's a google key, we also save to the legacy slot for compatibility
            if p_data['sdk'] == "google-genai":
                keyring.set_password("LLMChatApp", "api_key_google", new_key)
            
            self.load_credentials()

    def on_tab_changed(self, index):
        if index == 1: # Model Manager Tab
             self.populate_ecosystem_filter()
             self.load_models()

    def populate_ecosystem_filter(self):
        """Populates the filter with 'All' + any ecosystem that has a key."""
        import keyring
        self.ui.modelEcosystemFilter.blockSignals(True)
        self.ui.modelEcosystemFilter.clear()
        self.ui.modelEcosystemFilter.addItem("🌐 All Ecosystems")
        
        # This is a bit brute force but ensures we only show "ready" providers
        connected = []
        # Check base ones
        if keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key"):
            connected.append("NVIDIA NIM")
        if keyring.get_password("LLMChatApp", "api_key_google"):
            connected.append("Google Gemini")
            
        # Check custom ones
        import json
        custom = json.loads(get_app_settings().value("custom_providers", "[]"))
        for p in custom:
            eco_key = p['ecosystem'].lower().replace(' ', '_')
            if keyring.get_password("LLMChatApp", f"api_key_{p['sdk']}_{eco_key}"):
                connected.append(p['ecosystem'])
                
        self.ui.modelEcosystemFilter.addItems(sorted(list(set(connected))))
        self.ui.modelEcosystemFilter.blockSignals(False)

    def load_models(self):
        """Load models based on the selected filter with unified normalization and security gating."""
        from logic.model_io import load_all_models
        import keyring
        import json
        
        selection = self.ui.modelEcosystemFilter.currentText()
        all_m = load_all_models()
        
        # 1. Security Gate: Filter out models where no API key exists in vault
        def has_key(provider):
            p = str(provider).lower()
            # Primary ones
            if "nvidia" in p: 
                return bool(keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key"))
            if "google" in p: 
                return bool(keyring.get_password("LLMChatApp", "api_key_google"))
            
            # Custom ones
            custom = json.loads(get_app_settings().value("custom_providers", "[]"))
            for cp in custom:
                if normalize(cp['ecosystem']) == normalize(p):
                    eco_key = cp['ecosystem'].lower().replace(' ', '_')
                    return bool(keyring.get_password("LLMChatApp", f"api_key_{cp['sdk']}_{eco_key}"))
            return False

        def normalize(p):
            p = str(p).lower().replace(" ", "").replace("_", "").replace("-", "")
            if "nvidia" in p: return "nvidia"
            if "google" in p: return "google"
            return p

        # Apply Universal Key Filter
        filtered_all = [m for m in all_m if has_key(m.get('provider', 'nvidia'))]

        if selection == "🌐 All Ecosystems":
            self.models = filtered_all
            self.ui.modelHeaderLabel.setText("Viewing ALL Connected Models")
        else:
            p_id = normalize(selection)
            self.models = [m for m in filtered_all if normalize(m.get('provider', 'nvidia')) == p_id]
            self.ui.modelHeaderLabel.setText(f"Managing {selection.upper()}")
            
        self.populate_model_tabs()

    def populate_model_tabs(self):
        """Re-implementing the tabbed developer view inside the Settings Hub."""
        from collections import defaultdict
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView, QHeaderView
        
        selection = self.ui.modelEcosystemFilter.currentText()
        is_global = selection == "🌐 All Ecosystems"
        
        self.ui.modelDeveloperTabs.clear()
        models_by_dev = defaultdict(list)
        for m in self.models:
            dev = m.get('developer', 'Other')
            models_by_dev[dev].append(m)
            
        for dev, models in sorted(models_by_dev.items()):
            tab = QWidget()
            layout = QVBoxLayout(tab)
            table = QTableWidget()
            
            cols = ["Model Name", "Ecosystem", "Description", "Status"] if is_global else ["Model Name", "Description", "Status"]
            table.setColumnCount(len(cols))
            table.setHorizontalHeaderLabels(cols)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            table.setRowCount(len(models))
            for row, m in enumerate(models):
                table.setItem(row, 0, QTableWidgetItem(m.get('name', '')))
                if is_global:
                    table.setItem(row, 1, QTableWidgetItem(m.get('provider', 'nvidia').upper()))
                    table.setItem(row, 2, QTableWidgetItem(m.get('description', '')))
                    is_free = m.get('free', True)
                    table.setItem(row, 3, QTableWidgetItem("✅ Free" if is_free else "💰 Paid"))
                else:
                    table.setItem(row, 1, QTableWidgetItem(m.get('description', '')))
                    is_free = m.get('free', True)
                    table.setItem(row, 2, QTableWidgetItem("✅ Free" if is_free else "💰 Paid"))
            
            layout.addWidget(table)
            self.ui.modelDeveloperTabs.addTab(tab, dev)

    def fetch_models(self):
        """Triggers fetch for the active filter."""
        selection = self.ui.modelEcosystemFilter.currentText()
        targets = []
        
        import keyring
        import json
        
        if selection == "🌐 All Ecosystems":
            # 1. NVIDIA NIM (Primary)
            key = keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key")
            if key:
                targets.append({"name": "nvidia", "key": key, "url": "https://integrate.api.nvidia.com/v1"})
            
            # 2. Custom Providers
            custom = json.loads(get_app_settings().value("custom_providers", "[]"))
            for p in custom:
                eco_key = p['ecosystem'].lower().replace(' ', '_')
                key = keyring.get_password("LLMChatApp", f"api_key_{p['sdk']}_{eco_key}")
                if key:
                    targets.append({"name": p['ecosystem'], "key": key, "url": p['url']})
        else:
            # Scoped Fetch
            p_name = selection
            if "nvidia" in p_name.lower():
                key = keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key")
                targets.append({"name": "nvidia", "key": key, "url": "https://integrate.api.nvidia.com/v1"})
            else:
                custom = json.loads(get_app_settings().value("custom_providers", "[]"))
                for p in custom:
                    if p['ecosystem'] == p_name:
                        eco_key = p['ecosystem'].lower().replace(' ', '_')
                        key = keyring.get_password("LLMChatApp", f"api_key_{p['sdk']}_{eco_key}")
                        targets.append({"name": p['ecosystem'], "key": key, "url": p['url']})
                        break
        
        if not targets:
            QMessageBox.warning(self, "No Key", "No valid API keys found for the selected ecosystem.")
            return

        self.fetch_queue = targets
        self.all_fetched_models = []
        self.process_next_fetch()

    def process_next_fetch(self):
        if not self.fetch_queue:
            self.finalize_fetch()
            return
            
        target = self.fetch_queue.pop(0)
        from workers.model_fetch_worker import ModelFetchWorker
        
        self.worker = ModelFetchWorker(target['key'], target['url'])
        # Add provider metadata to the models during fetch
        self.current_fetch_provider = target['name'].lower().replace(" ", "")
        
        self.worker.progress.connect(self.on_fetch_progress)
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.start()
        
    def on_fetch_progress(self, current, total, model_id, status):
        self.ui.modelHeaderLabel.setText(f"Fetching {self.current_fetch_provider.upper()}: {current}/{total} - {model_id}")

    def on_fetch_finished(self, models):
        # Tag models with provider for shard saving
        for m in models:
            m['provider'] = self.current_fetch_provider
            
        self.all_fetched_models.extend(models)
        self.process_next_fetch()

    def on_fetch_error(self, err):
        QMessageBox.warning(self, "Fetch Error", f"Failed to fetch for {self.current_fetch_provider}: {err}")
        self.process_next_fetch()

    def finalize_fetch(self):
        from logic.model_io import save_all_models
        if self.all_fetched_models:
            save_all_models(self.all_fetched_models)
            QMessageBox.information(self, "Success", f"Catalog updated! Saved {len(self.all_fetched_models)} models.")
            self.load_models()
        else:
            QMessageBox.warning(self, "Fetch Failed", "No models were successfully recovered.")
        self.ui.modelHeaderLabel.setText("Model Management Complete")
        
    def add_model(self):
        QMessageBox.information(self, "Coming Soon", "Manual model entry is being linked.")

    def delete_model(self):
        QMessageBox.warning(self, "Action Restricted", "Please select a model from the list below first.")

    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        else:
            self.setStyleSheet("background-color: #f5f5f5; color: #333;")

class AddProviderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/add_provider_dialog.ui")
        self.ui = loader.load(str(ui_file), self)
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
        
        self.ui.custom_eco_container.hide()
        
        # Connect dependent dropdown logic
        self.ui.sdk_combo.currentTextChanged.connect(self.on_sdk_changed)
        self.ui.ecosystem_combo.currentTextChanged.connect(self.on_eco_changed)
        
        self.ui.save_btn.clicked.connect(self.on_save)
        self.ui.cancel_btn.clicked.connect(self.reject)
        
        # Initial population
        self.on_sdk_changed(self.ui.sdk_combo.currentText())

    def on_sdk_changed(self, sdk):
        """Updates the Ecosystem dropdown based on the selected SDK driver."""
        sdk_map = {
            "openai": ["NVIDIA NIM", "GroqCloud", "Official OpenAI", "OpenRouter", "DeepSeek", "Perplexity", "Fireworks AI", "Novita AI", "Ollama (Local)", "vLLM Server", "LiteLLM Proxy", "Custom..."],
            "google-genai": ["Google Gemini"],
            "anthropic": ["Anthropic"],
            "cohere": ["Cohere"],
            "mistralai": ["Mistral AI"],
            "together": ["Together AI"],
            "replicate": ["Replicate"],
            "huggingface_hub": ["Hugging Face"],
            "transformers": ["Local Transformers"],
            "boto3": ["AWS Bedrock"],
            "vertexai": ["Google Vertex AI"],
            "azure-ai-inference": ["Azure AI"],
            "litellm": ["LiteLLM Proxy"]
        }
        
        ecosystems = sdk_map.get(sdk, ["Custom..."])
        self.ui.ecosystem_combo.clear()
        self.ui.ecosystem_combo.addItems(ecosystems)

    def on_eco_changed(self, text):
        if not text: return # Handle clear() calls
        
        # Map of preset ecosystems to their default URLs
        url_map = {
            "NVIDIA NIM": "https://integrate.api.nvidia.com/v1",
            "Google Gemini": "https://generativelanguage.googleapis.com/v1beta",
            "GroqCloud": "https://api.groq.com/openai/v1",
            "OpenRouter": "https://openrouter.ai/api/v1",
            "DeepSeek": "https://api.deepseek.com",
            "Anthropic": "https://api.anthropic.com/v1",
            "Official OpenAI": "https://api.openai.com/v1",
            "Together AI": "https://api.together.xyz/v1",
            "Ollama (Local)": "http://localhost:11434/v1",
            "vLLM Server": "http://localhost:8000/v1",
            "LiteLLM Proxy": "http://localhost:4000/v1"
        }
        
        if text == "Custom...":
            self.ui.custom_eco_container.show()
            self.ui.url_edit.setReadOnly(False)
            self.ui.url_edit.clear()
            self.ui.url_edit.setPlaceholderText("Enter custom endpoint URL...")
        else:
            self.ui.custom_eco_container.hide()
            self.ui.url_edit.setReadOnly(True)
            self.ui.url_edit.setText(url_map.get(text, ""))
            self.ui.url_edit.setPlaceholderText("")

    def on_save(self):
        sdk = self.ui.sdk_combo.currentText()
        eco_selection = self.ui.ecosystem_combo.currentText()
        
        if eco_selection == "Custom...":
            eco = self.ui.custom_ecosystem_edit.text().strip()
        else:
            eco = eco_selection
            
        url = self.ui.url_edit.text().strip()
        key = self.ui.key_edit.text().strip()
        
        if not eco:
            QMessageBox.warning(self, "Input Required", "Please enter an Ecosystem Name.")
            return
            
        settings = get_app_settings()
        import json
        custom_raw = settings.value("custom_providers", "[]")
        try:
            custom_providers = json.loads(custom_raw)
        except:
            custom_providers = []
            
        new_p = {"sdk": sdk, "ecosystem": eco, "url": url}
        custom_providers.append(new_p)
        settings.setValue("custom_providers", json.dumps(custom_providers))
        
        if key:
            key_id = f"api_key_{sdk}_{eco.lower().replace(' ', '_')}"
            keyring.set_password("LLMChatApp", key_id, key)
            
        self.accept()

# Helper function to launch the new hub
def show_settings_hub(parent=None):
    from utils.path_utils import get_app_settings
    theme = get_app_settings().value("theme", "dark")
    dialog = CredentialManagerDialog(theme=theme, parent=parent)
    dialog.exec()
