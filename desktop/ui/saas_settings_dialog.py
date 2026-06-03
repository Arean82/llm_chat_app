# ui/saas_settings_dialog.py
"""
SaaS Configuration Settings Controller
Connects visual interface fields directly to config.ini managers.
"""

import os
from PySide6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QInputDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt
from server.utils.path_utils import get_resource_path
from web.core.config_manager import SaaSConfigManager
from desktop.ui.shared_widgets import set_app_icon

class SaaSSettingsDialogClass(QDialog):
    """Interactive controller governing physical SaaS INI adjustments from GUI."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        set_app_icon(self)
        self.config = SaaSConfigManager()
        
        # Dynamically construct layout
        loader = QUiLoader()
        ui_path = get_resource_path("ui_designer/saas_settings.ui")
        self.ui = loader.load(str(ui_path), self)
        
        # Assign loaded layout context directly onto self container
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
            # Carry over the geometry bounds specified in the Qt Designer .ui file and lock resizing
            self.setFixedSize(self.ui.size())
            
        # Ensure window title is set correctly instead of defaulting to process name
        self.setWindowTitle("📡 SaaS Node Configuration")
        
        # Bind interaction connections
        self.ui.btn_save.clicked.connect(self.on_save)
        self.ui.btn_cancel.clicked.connect(self.reject)
        
        if hasattr(self.ui, 'btn_reset_admin'):
            self.ui.btn_reset_admin.clicked.connect(self.on_reset_admin)
            
        # SaaS Control Buttons
        if hasattr(self.ui, 'pushButton'):
            self.ui.pushButton.clicked.connect(self.restart_saas_server)
        if hasattr(self.ui, 'pushButton_2'):
            self.ui.pushButton_2.clicked.connect(self.toggle_saas_server)
        
        # Connect new Tenant Management/Telemetry signals if present
        if hasattr(self.ui, 'btn_refresh_telemetry'):
            self.ui.btn_refresh_telemetry.clicked.connect(self.refresh_telemetry)
        if hasattr(self.ui, 'btn_refresh_tenants'):
            self.ui.btn_refresh_tenants.clicked.connect(self.refresh_tenants)
        if hasattr(self.ui, 'btn_toggle_ban'):
            self.ui.btn_toggle_ban.clicked.connect(self.toggle_ban_status)
        if hasattr(self.ui, 'btn_reset_pass'):
            self.ui.btn_reset_pass.clicked.connect(self.reset_tenant_password)
            
        # Initialize IDE Extensions Tab UI bindings and data (loaded natively from .ui file)
        self.setup_extensions_tab()
            
        # Restore Geometry
        from server.utils.path_utils import get_app_settings
        settings = get_app_settings()
        geom = settings.value("geometry_saas_settings")
        if geom:
            self.restoreGeometry(geom)
            
        # Inject localized warning for reserved Port 5000 conflict safety
        if hasattr(self.ui, 'hint_net'):
            self.ui.hint_net.setText(
                '<html><body>'
                '<p style="color:#888; font-size:11px;"><b>Security Tip:</b> Use 127.0.0.1 for secure local development. Expose to 0.0.0.0 only if you trust clients connected to your Wi-Fi network.</p>'
                '<p style="color:#e81123; font-size:11px;"><b>🚨 NOTICE:</b> Port 5000 is strictly reserved for the local IDE Extension API.</p>'
                '</body></html>'
            )
            
        # Hydrate all values initially
        self.hydrate_ui()

    def closeEvent(self, event):
        # Safely terminate any running AI generation thread before closing to avoid QThread destruction crashes
        if hasattr(self, 'ai_desc_worker') and self.ai_desc_worker and self.ai_desc_worker.isRunning():
            print("[SaaSSettingsDialog] Closing: Terminating running background AI description thread...")
            self.ai_desc_worker.disconnect()
            self.ai_desc_worker.terminate()
            self.ai_desc_worker.wait() # wait for clean thread exit
            
        from server.utils.path_utils import get_app_settings
        settings = get_app_settings()
        settings.setValue("geometry_saas_settings", self.saveGeometry())
        super().closeEvent(event)

    def hydrate_ui(self):
        """Hydrates inputs using live data retrieved from config.ini memory."""
        # Network Block
        
        host_str = self.config.get_str("NETWORK", "host", "127.0.0.1")
        if host_str == "0.0.0.0":
            self.ui.cbo_host.setCurrentIndex(1)
        else:
            self.ui.cbo_host.setCurrentIndex(0)
            
        self.ui.spn_port.setValue(self.config.get_int("NETWORK", "port", 8080))
        # Populate local access URL if present
        if hasattr(self.ui, 'lbl_address'):
            url = self.config.get_str("NETWORK", "local_access_url", "")
            if url:
                self.ui.lbl_address.setText(f"Local Access URL: {url}")
            else:
                self.ui.lbl_address.setText("Local Access URL: N/A")
        
        # Security Block
        self.ui.chk_signup.setChecked(self.config.get_bool("SECURITY", "public_signup", True))
        
        # SMTP Block
        smtp_active = self.config.get_bool("SMTP_RELAY", "enabled", False)
        self.ui.grp_smtp.setChecked(smtp_active)
        self.ui.txt_smtp_host.setText(self.config.get_str("SMTP_RELAY", "host", "smtp.gmail.com"))
        self.ui.spn_smtp_port.setValue(self.config.get_int("SMTP_RELAY", "port", 587))
        self.ui.txt_smtp_user.setText(self.config.get_str("SMTP_RELAY", "user", ""))
        self.ui.txt_smtp_pass.setText(self.config.get_str("SMTP_RELAY", "password", ""))
        
        # Reliability & Rates Block
        if hasattr(self.ui, 'spn_rpm'):
            self.ui.spn_rpm.setValue(self.config.get_int("RELIABILITY", "rpm", 60))
        if hasattr(self.ui, 'chk_failover_enable'):
            self.ui.chk_failover_enable.setChecked(self.config.get_bool("RELIABILITY", "failover_enable", True))
        if hasattr(self.ui, 'txt_failover_seq'):
            self.ui.txt_failover_seq.setText(self.config.get_str("RELIABILITY", "failover_seq", "google,openai,ollama"))
            
        if hasattr(self.ui, 'btn_refresh_telemetry'):
            self.refresh_telemetry()
        if hasattr(self.ui, 'btn_refresh_tenants'):
            self.refresh_tenants()
            
        # Hook up user's new Server Status label
        if hasattr(self.ui, 'lbl_status'):
            parent = self.parent()
            is_running = False
            if parent and hasattr(parent, 'saas_server') and parent.saas_server:
                is_running = parent.saas_server.running
                
            if is_running:
                self.ui.lbl_status.setText("<span style='color:green; font-weight:bold;'>🟢 RUNNING</span> (Online)")
                if hasattr(self.ui, 'pushButton'): 
                    self.ui.pushButton.setEnabled(True)
                    self.ui.pushButton.setText("RESTART SaaS Node")
                    self.ui.pushButton.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 5px;")
                if hasattr(self.ui, 'pushButton_2'): 
                    self.ui.pushButton_2.setText("STOP SaaS Node")
                    self.ui.pushButton_2.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 5px;")
            else:
                self.ui.lbl_status.setText("<span style='color:red; font-weight:bold;'>🔴 OFFLINE</span> (Stopped)")
                if hasattr(self.ui, 'pushButton'): 
                    self.ui.pushButton.setEnabled(False)
                    self.ui.pushButton.setStyleSheet("background-color: #64748b; color: white; font-weight: bold; padding: 5px;")
                if hasattr(self.ui, 'pushButton_2'): 
                    self.ui.pushButton_2.setText("START SaaS Node")
                    self.ui.pushButton_2.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; padding: 5px;")

    def toggle_saas_server(self):
        parent = self.parent()
        if parent and hasattr(parent, 'saas_server'):
            if parent.saas_server.running:
                self.config.set_val("NETWORK", "enabled", False)
                parent.saas_server.stop()
            else:
                self.config.set_val("NETWORK", "enabled", True)
                parent.saas_server.host = "0.0.0.0" if self.ui.cbo_host.currentIndex() == 1 else "127.0.0.1"
                parent.saas_server.port = self.ui.spn_port.value()
                parent.saas_server.start_server()
            self.config.save()
        self.hydrate_ui()

    def restart_saas_server(self):
        parent = self.parent()
        if parent and hasattr(parent, 'saas_server') and parent.saas_server.running:
            parent.saas_server.stop()
            self.config.set_val("NETWORK", "enabled", True)
            parent.saas_server.host = "0.0.0.0" if self.ui.cbo_host.currentIndex() == 1 else "127.0.0.1"
            parent.saas_server.port = self.ui.spn_port.value()
            parent.saas_server.start_server()
            self.config.save()
        self.hydrate_ui()

    def on_reset_admin(self):
        """Triggers the secure reset sequence for the SaaS Master Admin account."""
        reply = QMessageBox.question(
            self,
            "Reset Master Admin",
            "Are you sure you want to forcibly reset the SaaS Admin credentials to their default values?\n\nThis will reset the login password to 'admin' and the API Passport back to 'admin_master_passport'.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from web.core.tenant_db import TenantDatabaseManager
                db = TenantDatabaseManager()
                db.reset_admin_account()
                
                QMessageBox.information(
                    self,
                    "Reset Successful",
                    "The Master Admin credentials have been reset.\n\nUsername: admin\nPassword: admin\nAPI Passport: admin_master_passport"
                )
            except Exception as e:
                QMessageBox.critical(self, "Reset Failed", f"An error occurred while resetting the admin account:\n\n{e}")

    def on_save(self):
        """Validates user selections and commits changes back to physical flatfile."""
        # Retrieve network targets
        enabled = self.config.get_bool("NETWORK", "enabled", True)
        host_index = self.ui.cbo_host.currentIndex()
        host_val = "0.0.0.0" if host_index == 1 else "127.0.0.1"
        port_val = self.ui.spn_port.value()
        
        # Basic validation
        if enabled and not port_val:
            QMessageBox.warning(self, "Config Alert", "Port cannot be blank.")
            return
            
        # Prevent hijacking of localized extension channel
        if enabled and port_val == 5000:
            QMessageBox.warning(
                self, 
                "Reserved Port Conflict", 
                "Port 5000 is strictly reserved for the local IDE Extension API.\n\nPlease select a different listener port for the SaaS Cloud Node (e.g. 8000)."
            )
            return
            
        # Sync cache memory
        self.config.set_val("NETWORK", "enabled", enabled)
        self.config.set_val("NETWORK", "host", host_val)
        self.config.set_val("NETWORK", "port", port_val)
        
        self.config.set_val("SECURITY", "public_signup", self.ui.chk_signup.isChecked())
        
        self.config.set_val("SMTP_RELAY", "enabled", self.ui.grp_smtp.isChecked())
        self.config.set_val("SMTP_RELAY", "host", self.ui.txt_smtp_host.text().strip())
        self.config.set_val("SMTP_RELAY", "port", self.ui.spn_smtp_port.value())
        self.config.set_val("SMTP_RELAY", "user", self.ui.txt_smtp_user.text().strip())
        self.config.set_val("SMTP_RELAY", "password", self.ui.txt_smtp_pass.text().strip())
        
        # Save & Validate Reliability Parameters
        if hasattr(self.ui, 'spn_rpm'):
            rpm_val = self.ui.spn_rpm.value()
            if rpm_val <= 0:
                QMessageBox.warning(self, "Validation Error", "Requests Per Minute (RPM) Limit must be a positive integer.")
                return
            self.config.set_val("RELIABILITY", "rpm", rpm_val)
            
        if hasattr(self.ui, 'chk_failover_enable'):
            self.config.set_val("RELIABILITY", "failover_enable", self.ui.chk_failover_enable.isChecked())
            
        if hasattr(self.ui, 'txt_failover_seq'):
            failover_seq_val = self.ui.txt_failover_seq.text().strip()
            if not failover_seq_val:
                QMessageBox.warning(self, "Validation Error", "Failover Sequence cannot be empty.")
                return
            providers = [p.strip().lower() for p in failover_seq_val.split(",") if p.strip()]
            if not providers:
                QMessageBox.warning(self, "Validation Error", "Failover Sequence must contain at least one valid provider.")
                return
            self.config.set_val("RELIABILITY", "failover_seq", ",".join(providers))
        
        # Save IDE Extensions configurations
        if hasattr(self, 'extensions_cache'):
            # Save the currently selected extension row's values to cache before writing
            row = self.ext_table.currentRow()
            if row >= 0 and row < len(self.extensions_cache):
                self.extensions_cache[row]["is_visible"] = self.chk_ext_visible.isChecked()
                self.extensions_cache[row]["name"] = self.txt_ext_title.text().strip()
                self.extensions_cache[row]["description"] = self.txt_ext_desc.toPlainText().strip()

            from server.utils.path_utils import get_resource_path
            import json, os
            config_path = get_resource_path(os.path.join("extension", "extensions_config.json"))
            
            # Re-group into target extensions config
            for ext in self.extensions_cache:
                fn = ext["filename"]
                if fn not in self.ext_config_data:
                    self.ext_config_data[fn] = {}
                self.ext_config_data[fn]["is_visible"] = ext["is_visible"]
                self.ext_config_data[fn]["name"] = ext["name"]
                self.ext_config_data[fn]["description"] = ext["description"]
                
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.ext_config_data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[Extensions Config] Save failed: {e}")

        # Hardware commit
        self.config.save()
        self.accept()
        
    def refresh_telemetry(self):
        from web.core.tenant_db import TenantDatabaseManager
        db = TenantDatabaseManager()
        usage = db.get_global_usage().get("aggregate", {})
        prompt = usage.get("total_prompt") or 0
        comp = usage.get("total_completion") or 0
        self.ui.lbl_global_prompt.setText(f"Total Prompt Tokens: {prompt:,}")
        self.ui.lbl_global_completion.setText(f"Total Completion Tokens: {comp:,}")
        
    def refresh_tenants(self):
        from web.core.tenant_db import TenantDatabaseManager
        db = TenantDatabaseManager()
        tenants = db.get_all_tenants()
        self.ui.table_tenants.setRowCount(len(tenants))
        for row, t in enumerate(tenants):
            self.ui.table_tenants.setItem(row, 0, QTableWidgetItem(str(t.get("id", ""))))
            self.ui.table_tenants.setItem(row, 1, QTableWidgetItem(str(t.get("username", ""))))
            self.ui.table_tenants.setItem(row, 2, QTableWidgetItem(str(t.get("email", ""))))
            
            status_item = QTableWidgetItem(str(t.get("status", "active")).upper())
            if t.get("status") == "banned":
                status_item.setForeground(Qt.red)
            else:
                status_item.setForeground(Qt.darkGreen)
            self.ui.table_tenants.setItem(row, 3, status_item)
            self.ui.table_tenants.setItem(row, 4, QTableWidgetItem(f"{t.get('total_tokens', 0):,}"))
            
    def toggle_ban_status(self):
        row = self.ui.table_tenants.currentRow()
        if row < 0: return
        user_id = int(self.ui.table_tenants.item(row, 0).text())
        username = self.ui.table_tenants.item(row, 1).text()
        current_status = self.ui.table_tenants.item(row, 3).text().lower()
        
        if username == 'admin':
            QMessageBox.warning(self, "Action Denied", "Cannot ban the master admin account.")
            return
            
        new_status = "active" if current_status == "banned" else "banned"
        from web.core.tenant_db import TenantDatabaseManager
        db = TenantDatabaseManager()
        db.update_user_status(user_id, new_status)
        self.refresh_tenants()
        
    def reset_tenant_password(self):
        row = self.ui.table_tenants.currentRow()
        if row < 0: return
        user_id = int(self.ui.table_tenants.item(row, 0).text())
        username = self.ui.table_tenants.item(row, 1).text()
        
        new_pass, ok = QInputDialog.getText(self, "Reset Password", f"Enter new password for {username}:")
        if ok and new_pass.strip():
            from web.core.tenant_db import TenantDatabaseManager
            db = TenantDatabaseManager()
            success, msg = db.update_user_profile(user_id, password_raw=new_pass.strip())
            if success:
                QMessageBox.information(self, "Success", f"Password for {username} has been reset.")
            else:
                QMessageBox.critical(self, "Error", msg)

    def setup_extensions_tab(self):
        """Prepares bindings and table behaviors for UI-loaded IDE Extension components."""
        from PySide6.QtWidgets import QHeaderView, QAbstractItemView

        # Map UI components directly from the loaded UI schema
        self.ext_table = self.ui.ext_table
        self.editor_frame = self.ui.editor_frame
        self.chk_ext_visible = self.ui.chk_ext_visible
        self.txt_ext_title = self.ui.txt_ext_title
        self.btn_ext_ai = self.ui.btn_ext_ai
        self.txt_ext_desc = self.ui.txt_ext_desc

        # Configure table behavior
        self.ext_table.setColumnCount(3)
        self.ext_table.setHorizontalHeaderLabels(["Filename", "Size", "Status"])
        self.ext_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ext_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ext_table.verticalHeader().setVisible(False)
        self.ext_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ext_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.ext_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        self.ext_table.itemSelectionChanged.connect(self.on_extension_selected)
        self.btn_ext_ai.clicked.connect(self.on_generate_ai_desc)

        # Load extension files dynamically
        self.load_extensions_data()

    def load_extensions_data(self):
        """Crawls local extensions and populates the table."""
        from PySide6.QtWidgets import QTableWidgetItem
        from server.utils.path_utils import get_resource_path
        import json, os, time, re

        self.ext_table.setRowCount(0)
        self.extensions_cache = []

        ext_dir = get_resource_path("extension")
        config_path = get_resource_path(os.path.join("extension", "extensions_config.json"))

        # Load extensions config file
        self.ext_config_data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.ext_config_data = json.load(f)
            except Exception:
                pass

        if not os.path.exists(ext_dir):
            return

        row = 0
        for file in os.listdir(ext_dir):
            if file.endswith('.vsix') or file.endswith('.zip'):
                file_path = os.path.join(ext_dir, file)
                size_bytes = os.path.getsize(file_path)
                
                # Size calculation
                if size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                config_item = self.ext_config_data.get(file, {})
                is_visible = config_item.get("is_visible", False)
                description = config_item.get("description", "No description available.")
                name = config_item.get("name", file.split('-')[0].replace('_', ' ').title())

                item_meta = {
                    "filename": file,
                    "name": name,
                    "is_visible": is_visible,
                    "description": description,
                    "file_size": size_str
                }

                self.extensions_cache.append(item_meta)

                self.ext_table.insertRow(row)
                self.ext_table.setItem(row, 0, QTableWidgetItem(file))
                self.ext_table.setItem(row, 1, QTableWidgetItem(size_str))
                self.ext_table.setItem(row, 2, QTableWidgetItem("Visible" if is_visible else "Private"))
                row += 1

        if row > 0:
            self.ext_table.selectRow(0)

    def on_extension_selected(self):
        """Hydrates the editor form fields with the selected extension's values."""
        row = self.ext_table.currentRow()
        if row < 0 or row >= len(self.extensions_cache):
            self.editor_frame.setEnabled(False)
            return

        self.editor_frame.setEnabled(True)
        ext = self.extensions_cache[row]
        self.chk_ext_visible.setChecked(ext["is_visible"])
        self.txt_ext_title.setText(ext["name"])
        self.txt_ext_desc.setPlainText(ext["description"])

    def on_generate_ai_desc(self):
        """Asynchronously drafts a professional plugin README utilizing the active system LLM."""
        row = self.ext_table.currentRow()
        if row < 0 or row >= len(self.extensions_cache):
            return

        ext = self.extensions_cache[row]
        
        self.btn_ext_ai.setText("Writing...")
        self.btn_ext_ai.setEnabled(False)

        # Quick worker QThread connection to query LLM Client natively
        from server.logic.llm_client import LLMClient
        from PySide6.QtCore import QThread, Signal

        class DynamicDescWorker(QThread):
            finished = Signal(str, str)
            error = Signal(str)

            def __init__(self, filename, parent_dialog, model_id=None):
                super().__init__(None) # Decoupled parent
                self.filename = filename
                self.parent_dialog = parent_dialog
                self.model_id = model_id

            def run(self):
                print("[DynamicDescWorker] Background QThread run() started...")
                try:
                    llm_client = LLMClient()
                    # Hook active provider configurations
                    from server.utils.path_utils import get_app_settings
                    from server.utils.security_utils import decrypt_data, SESSION_MASTER_PASSWORD
                    import keyring
                    
                    active_p = get_app_settings().value("active_provider_id", "nvidia")
                    print(f"[DynamicDescWorker] Resolved active provider: {active_p}")
                    
                    api_key = keyring.get_password("LLMChatApp", f"api_key_{active_p}") or keyring.get_password("LLMChatApp", "api_key")
                    base_url = get_app_settings().value(f"url_{active_p}") or get_app_settings().value("base_url", "https://integrate.api.nvidia.com/v1")
                    print(f"[DynamicDescWorker] Loaded keyring key: {'FOUND' if api_key else 'MISSING'}, base_url: {base_url}")
                    
                    if not api_key:
                        print("[DynamicDescWorker] Error: API key missing.")
                        self.error.emit("Ecosystem API Key is missing. Set your provider key first.")
                        return

                    # Zero-Trust local decrypt cycle
                    print(f"[DynamicDescWorker] Decrypting keyring API key using session password...")
                    api_key = decrypt_data(api_key, SESSION_MASTER_PASSWORD)
                    print(f"[DynamicDescWorker] Decrypted key length: {len(api_key) if api_key else 0}")

                    # Dynamic Multi-Provider Routing Setup
                    if str(active_p).lower() == "google":
                        llm_client.set_google_api_key(api_key)
                        print("[DynamicDescWorker] Configured Google client.")
                    else:
                        llm_client.set_api_key(api_key)
                        llm_client.set_base_url(base_url)
                        print("[DynamicDescWorker] Configured OpenAI client.")

                    # Enforce live selected model from parent/chat directly with zero hardcoded fallbacks
                    model_id = self.model_id
                    if not model_id:
                        from server.utils.path_utils import get_app_settings
                        model_id = get_app_settings().value("current_model_id")
                    
                    print(f"[DynamicDescWorker] Resolved model ID for generation: {model_id}")
                    if not model_id:
                        print("[DynamicDescWorker] Error: No model selected.")
                        raise ValueError(
                            "No active model is currently selected in your chat window.\n\n"
                            "Please select an active provider model (e.g. Gemini, NVIDIA NIM) in the main chat view "
                            "before generating plugin documentation."
                        )
                    
                    llm_client.set_model(model_id)

                    platform = "vscode" if self.filename.endswith('.vsix') else "jetbrains"
                    prompt = (
                        f"Write a highly professional, beautifully formatted, concise README-style Markdown description "
                        f"for an IDE Extension plugin. The file name is '{self.filename}' and it is for the '{platform}' ecosystem.\n\n"
                        f"Provide a brief overview of features (like inline autocomplete, model parameters editing, and workspace syncing), "
                        f"step-by-step instructions on how to install it, and connection instructions "
                        f"(explaining how it connects to the local Universal API server on Port 5000).\n\n"
                        f"Keep it under 300 words. Do not use generic placeholders. Focus on premium glassmorphic UI synergy and security."
                    )

                    print(f"[DynamicDescWorker] Sending completion generation request to LLM client ({model_id})...")
                    full_text = llm_client._run_completion_internal(
                        "You are an expert technical writer.",
                        prompt,
                        1024,
                        0.3
                    )
                    print("[DynamicDescWorker] Completion request successful! Response received.")

                    self.finished.emit(self.filename, full_text.strip())
                except Exception as e:
                    print(f"[DynamicDescWorker] Thread run encountered exception: {e}")
                    import traceback
                    traceback.print_exc()
                    self.error.emit(str(e))

        # Retrieve active model ID selected in the user's active session/chat
        model_id = None
        if self.parent() and hasattr(self.parent(), "llm_client") and self.parent().llm_client:
            model_id = self.parent().llm_client.current_model

        # Store thread globally to avoid instant garbage collection
        self.ai_desc_worker = DynamicDescWorker(ext["filename"], self, model_id=model_id)
        self.ai_desc_worker.finished.connect(self._on_ai_desc_complete)
        self.ai_desc_worker.error.connect(self._on_ai_desc_error)
        self.ai_desc_worker.start()

    def _on_ai_desc_complete(self, filename, text):
        self.btn_ext_ai.setText("🧠 AI Generate")
        self.btn_ext_ai.setEnabled(True)
        self.txt_ext_desc.setPlainText(text)
        
        # Save to local table cache
        row = self.ext_table.currentRow()
        if row >= 0 and row < len(self.extensions_cache):
            self.extensions_cache[row]["description"] = text

    def _on_ai_desc_error(self, err_msg):
        self.btn_ext_ai.setText("🧠 AI Generate")
        self.btn_ext_ai.setEnabled(True)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "AI Draft Failed", f"Could not generate description:\n\n{err_msg}")
