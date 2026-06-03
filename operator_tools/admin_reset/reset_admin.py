# operator_tools/reset_admin.py
# Universal Master Password Reset Sequence for SaaS, Desktop GUI, and CLI Headless Gates
# Designed to run securely as a standalone binary (reset_admin.exe) and compatible with system services.

import sys
import os

# Absolute service-friendly pathing resolution
if getattr(sys, 'frozen', False):
    root_dir = os.path.dirname(sys.executable)
else:
    # operator_tools/admin_reset/reset_admin.py is located under project_root/operator_tools/admin_reset/
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, root_dir)

from web.core.tenant_db import TenantDatabaseManager
import argparse
from core.headless_reset import run_headless_reset

# ═══════════════════════════════════════════════════════════════════
#  GUI MODE — PySide6 XML Loader
# ═══════════════════════════════════════════════════════════════════
def run_gui_reset():
    from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QPushButton, QTextEdit, QMessageBox
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtCore import QFile
    from PySide6.QtGui import QIcon

    class ResetAdminController:
        def __init__(self):
            # Resolve UI file path supporting both source and PyInstaller environments
            if getattr(sys, 'frozen', False):
                base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            else:
                base_path = os.path.dirname(__file__)
                
            ui_file_path = os.path.join(base_path, "ui_assets", "reset_admin.ui")
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QFile.ReadOnly):
                raise FileNotFoundError(f"Cannot open UI file: {ui_file_path}")
                
            loader = QUiLoader()
            self.dialog = loader.load(ui_file, None)
            ui_file.close()

            self.btn_reset = self.dialog.findChild(QPushButton, "btn_reset")
            self.btn_close = self.dialog.findChild(QPushButton, "btn_close")
            self.log_output = self.dialog.findChild(QTextEdit, "log_output")

            from PySide6.QtWidgets import QRadioButton, QLineEdit
            self.radio_custom = self.dialog.findChild(QRadioButton, "radio_custom")
            self.custom_pass = self.dialog.findChild(QLineEdit, "custom_pass")
            if self.radio_custom and self.custom_pass:
                self.radio_custom.toggled.connect(self.custom_pass.setEnabled)

            self.btn_reset.clicked.connect(self.on_reset)
            self.btn_close.clicked.connect(self.dialog.close)
            
            self.log_output.append("Waiting for execution command...")
            self._apply_theme()

        def _apply_theme(self):
            self.dialog.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #0d1117, stop:0.5 #161b22, stop:1 #0d1117);
                    color: #c9d1d9;
                }
                * {
                    font-family: "Segoe UI", "Inter", "Roboto", "Helvetica Neue", Arial, sans-serif;
                    font-size: 10pt;
                }
                QMainWindow {
                    background-color: #0d1117;
                }
                QLabel { color: #c9d1d9; }
                QLabel#subtitle { color: #8b949e; font-style: italic; }
                QTextEdit {
                    background-color: #010409;
                    color: #58a6ff;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 8px;
                    font-family: "Consolas", "Courier New", monospace;
                }
                QPushButton {
                    background-color: #238636;
                    color: white;
                    border: 1px solid rgba(240, 246, 252, 0.1);
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2ea043; }
                QPushButton:pressed { background-color: #238636; }
                QPushButton:disabled { background-color: #21262d; color: #484f58; border: 1px solid #30363d; }
                QLineEdit {
                    background-color: #0d1117;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    padding: 6px;
                    color: #c9d1d9;
                }
                QLineEdit:focus { border: 1px solid #58a6ff; }
                QProgressBar {
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    text-align: center;
                    background-color: #010409;
                    color: #c9d1d9;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #238636, stop: 1 #2ea043);
                    border-radius: 5px;
                }
                QPushButton#btn_reset {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d73a49, stop:1 #cb2431);
                    color: #ffffff;
                    border: 1px solid #cb2431;
                    border-radius: 8px;
                }
                QPushButton#btn_reset:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #cb2431, stop:1 #b31d28);
                }
                QPushButton#btn_close {
                    background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 8px;
                }
                QPushButton#btn_close:hover { background-color: #30363d; border: 1px solid #484f58; }
            """)

        def on_reset(self):
            from PySide6.QtWidgets import QRadioButton, QLineEdit
            import string
            import random

            radio_default = self.dialog.findChild(QRadioButton, "radio_default")
            radio_random = self.dialog.findChild(QRadioButton, "radio_random")
            radio_custom = self.dialog.findChild(QRadioButton, "radio_custom")
            line_edit = self.dialog.findChild(QLineEdit, "custom_pass")

            if radio_random and radio_random.isChecked():
                new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            elif radio_custom and radio_custom.isChecked():
                new_password = line_edit.text()
                if not new_password:
                    QMessageBox.critical(self.dialog, "Error", "Custom password cannot be empty.")
                    return
            else:
                new_password = "admin"

            reply = QMessageBox.question(self.dialog, "Confirm Global Reset", "Are you sure you want to reset the Master Admin Credentials?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.log_output.append("\n▶ Initiating universal master reset sequence...")
                try:
                    db = TenantDatabaseManager()
                    db.reset_admin_account(new_password)
                    self.log_output.append("✅ Successfully synchronized Master Credentials!")
                    self.log_output.append(f"  Username: admin\n  Password: {new_password}\n  API Key: admin_master_passport")
                    QMessageBox.information(self.dialog, "Success", "Master admin account reset to specified password.")
                except Exception as e:
                    self.log_output.append(f"❌ Failed: {str(e)}")
                    QMessageBox.critical(self.dialog, "Error", f"Reset failed:\n{e}")

    app = QApplication(sys.argv)
    app.setApplicationName("Reset Admin")
    icon_path = os.path.join(root_dir, "resources", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    controller = ResetAdminController()
    controller.dialog.show()
    return app.exec()

# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Universal Master Password Reset Sequence")
    parser.add_argument("--headless", "--cli", action="store_true", help="Run in CLI mode without GUI.")
    parser.add_argument("--random-password", action="store_true", help="Generate a random password.")
    parser.add_argument("--custom-password", type=str, help="Set a custom password.")
    args = parser.parse_args()

    if args.headless:
        sys.exit(run_headless_reset(random_pass=args.random_password, custom_pass=args.custom_password))
    else:
        sys.exit(run_gui_reset())

if __name__ == "__main__":
    main()
