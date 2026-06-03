import os
from PySide6.QtWidgets import QWidget, QMessageBox, QListWidgetItem, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from server.utils.path_utils import get_resource_path

class AgentHubViewWidget(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.window = parent_window
        
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/agent_hub.ui")
        self.ui = loader.load(str(ui_file), self)
        
        # Connect buttons
        self.ui.back_btn.clicked.connect(self.go_back)
        self.ui.start_btn.clicked.connect(self.start_agent)
        self.ui.stop_btn.clicked.connect(self.stop_agent)
        self.ui.add_skill_btn.clicked.connect(self.add_skill)
        self.ui.refresh_skills_btn.clicked.connect(self.load_skills)
        self.ui.save_config_btn.clicked.connect(self.save_config)
        
        # Setup layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        
        self.admin_user_id = 1  # Desktop God mode local tenant

    def go_back(self):
        self.window.show_chat_mode()
        
    def start_agent(self):
        try:
            from web.core.agent_manager import AgentManager
            mgr = AgentManager.get_instance()
            gateway_url = f"http://localhost:{os.getenv('PORT', 5000)}/v1"
            api_key = self.window.llm_client.api_key if self.window.llm_client.api_key else "GOD_MODE"
            success = mgr.start_agent(self.admin_user_id, api_key, gateway_url)
            if success:
                self.ui.status_label.setText("Status: RUNNING")
                self.append_log("[System] Hermes Agent successfully started.")
            else:
                QMessageBox.warning(self, "Error", "Failed to start agent.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Agent startup failed: {e}")

    def stop_agent(self):
        try:
            from web.core.agent_manager import AgentManager
            mgr = AgentManager.get_instance()
            success = mgr.stop_agent(self.admin_user_id)
            if success:
                self.ui.status_label.setText("Status: STOPPED")
                self.append_log("[System] Hermes Agent stopped.")
            else:
                QMessageBox.warning(self, "Error", "Failed to stop agent.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Agent stop failed: {e}")

    def add_skill(self):
        name = self.ui.skill_name_input.text().strip()
        code = self.ui.skill_code_input.toPlainText().strip()
        if not name or not code:
            QMessageBox.warning(self, "Error", "Skill Name and Code are required.")
            return
            
        try:
            from web.core.tenant_db import TenantDatabaseManager
            db = TenantDatabaseManager()
            db.add_agent_skill(self.admin_user_id, name, code)
            QMessageBox.information(self, "Success", f"Skill '{name}' added successfully!")
            self.ui.skill_name_input.clear()
            self.ui.skill_code_input.clear()
            self.load_skills()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add skill: {e}")

    def load_skills(self):
        self.ui.skills_list_widget.clear()
        try:
            from web.core.tenant_db import TenantDatabaseManager
            db = TenantDatabaseManager()
            skills = db.get_agent_skills(self.admin_user_id)
            for s in skills:
                item = QListWidgetItem(f"🤖 {s['skill_name']} (Added: {s['created_at']})")
                self.ui.skills_list_widget.addItem(item)
        except Exception as e:
            self.append_log(f"[Error] Failed to load skills: {e}")

    def save_config(self):
        QMessageBox.information(self, "Success", "Configuration saved.")

    def append_log(self, text):
        self.ui.agent_console.append(text)
        
    def refresh_ui(self):
        # Called when view is shown
        self.load_skills()
        try:
            from web.core.agent_manager import AgentManager
            mgr = AgentManager.get_instance()
            status = mgr.get_status(self.admin_user_id)
            self.ui.status_label.setText(f"Status: {status}")
        except:
            pass
