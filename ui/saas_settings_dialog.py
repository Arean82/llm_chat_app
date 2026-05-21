# ui/saas_settings_dialog.py
"""
SaaS Configuration Settings Controller
Connects visual interface fields directly to config.ini managers.
"""

import os
from PySide6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QInputDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt
from utils.path_utils import get_resource_path
from saas.config_manager import SaaSConfigManager

class SaaSSettingsDialogClass(QDialog):
    """Interactive controller governing physical SaaS INI adjustments from GUI."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = SaaSConfigManager()
        
        # Dynamically construct layout
        loader = QUiLoader()
        ui_path = get_resource_path("ui_designer/saas_settings.ui")
        self.ui = loader.load(str(ui_path), self)
        
        # Assign loaded layout context directly onto self container
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
        
        # Bind interaction connections
        self.ui.btn_save.clicked.connect(self.on_save)
        self.ui.btn_cancel.clicked.connect(self.reject)
        
        if hasattr(self.ui, 'btn_reset_admin'):
            self.ui.btn_reset_admin.clicked.connect(self.on_reset_admin)
        
        # Setup dynamic interactive disabling
        self.ui.chk_enabled.toggled.connect(self.on_enable_toggled)
        
        # Connect new Tenant Management/Telemetry signals if present
        if hasattr(self.ui, 'btn_refresh_telemetry'):
            self.ui.btn_refresh_telemetry.clicked.connect(self.refresh_telemetry)
        if hasattr(self.ui, 'btn_refresh_tenants'):
            self.ui.btn_refresh_tenants.clicked.connect(self.refresh_tenants)
        if hasattr(self.ui, 'btn_toggle_ban'):
            self.ui.btn_toggle_ban.clicked.connect(self.toggle_ban_status)
        if hasattr(self.ui, 'btn_reset_pass'):
            self.ui.btn_reset_pass.clicked.connect(self.reset_tenant_password)
        
        self.hydrate_ui()
        self.on_enable_toggled(self.ui.chk_enabled.isChecked())
        
        # Inject localized warning for reserved Port 5000 conflict safety
        if hasattr(self.ui, 'hint_net'):
            self.ui.hint_net.setText(
                '<html><body>'
                '<p style="color:#888; font-size:11px;"><b>Security Tip:</b> Use 127.0.0.1 for secure local development. Expose to 0.0.0.0 only if you trust clients connected to your Wi-Fi network.</p>'
                '<p style="color:#e81123; font-size:11px;"><b>🚨 NOTICE:</b> Port 5000 is strictly reserved for the local IDE Extension API.</p>'
                '</body></html>'
            )

    def hydrate_ui(self):
        """Hydrates inputs using live data retrieved from config.ini memory."""
        # Network Block
        self.ui.chk_enabled.setChecked(self.config.get_bool("NETWORK", "enabled", True))
        
        host_str = self.config.get_str("NETWORK", "host", "127.0.0.1")
        if host_str == "0.0.0.0":
            self.ui.cbo_host.setCurrentIndex(1)
        else:
            self.ui.cbo_host.setCurrentIndex(0)
            
        self.ui.spn_port.setValue(self.config.get_int("NETWORK", "port", 8000))
        
        # Security Block
        self.ui.chk_signup.setChecked(self.config.get_bool("SECURITY", "public_signup", True))
        
        # SMTP Block
        smtp_active = self.config.get_bool("SMTP_RELAY", "enabled", False)
        self.ui.grp_smtp.setChecked(smtp_active)
        self.ui.txt_smtp_host.setText(self.config.get_str("SMTP_RELAY", "host", "smtp.gmail.com"))
        self.ui.spn_smtp_port.setValue(self.config.get_int("SMTP_RELAY", "port", 587))
        self.ui.txt_smtp_user.setText(self.config.get_str("SMTP_RELAY", "user", ""))
        self.ui.txt_smtp_pass.setText(self.config.get_str("SMTP_RELAY", "password", ""))
        
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
            else:
                self.ui.lbl_status.setText("<span style='color:red; font-weight:bold;'>🔴 OFFLINE</span> (Stopped)")

    def on_enable_toggled(self, is_active: bool):
        """Interactively enables/disables child widgets based on master toggle."""
        self.ui.cbo_host.setEnabled(is_active)
        self.ui.spn_port.setEnabled(is_active)
        self.ui.tabWidget.setTabEnabled(1, is_active) # Disable security configurations
        self.ui.tabWidget.setTabEnabled(2, is_active) # Disable admin reset if server is offline

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
                from saas.tenant_db import TenantDatabaseManager
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
        enabled = self.ui.chk_enabled.isChecked()
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
        
        # Hardware commit
        self.config.save()
        self.accept()
        
    def refresh_telemetry(self):
        from saas.tenant_db import TenantDatabaseManager
        db = TenantDatabaseManager()
        usage = db.get_global_usage().get("aggregate", {})
        prompt = usage.get("total_prompt") or 0
        comp = usage.get("total_completion") or 0
        self.ui.lbl_global_prompt.setText(f"Total Prompt Tokens: {prompt:,}")
        self.ui.lbl_global_completion.setText(f"Total Completion Tokens: {comp:,}")
        
    def refresh_tenants(self):
        from saas.tenant_db import TenantDatabaseManager
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
        from saas.tenant_db import TenantDatabaseManager
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
            from saas.tenant_db import TenantDatabaseManager
            db = TenantDatabaseManager()
            success, msg = db.update_user_profile(user_id, password_raw=new_pass.strip())
            if success:
                QMessageBox.information(self, "Success", f"Password for {username} has been reset.")
            else:
                QMessageBox.critical(self, "Error", msg)
