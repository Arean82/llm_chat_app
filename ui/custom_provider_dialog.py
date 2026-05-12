# ui/custom_provider_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QCheckBox, QMessageBox, QLabel
from PySide6.QtCore import Qt, QSettings
from PySide6.QtUiTools import QUiLoader
from utils.path_utils import get_resource_path
from utils.helpers import set_app_icon

class CustomProviderDialogClass(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/custom_provider_dialog.ui")
        self.ui = loader.load(str(ui_file))
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        set_app_icon(self)
        self.setWindowTitle("Configure Custom Host")
        
        # Recover current style profile
        settings = QSettings("LLMChatApp", "Settings")
        self.theme = settings.value("theme", "light")
        
        # Element Mapping
        self.name_input = self.ui.findChild(QLineEdit, "name_input")
        self.url_input = self.ui.findChild(QLineEdit, "url_input")
        self.requires_key_chk = self.ui.findChild(QCheckBox, "requires_key_chk")
        self.save_btn = self.ui.findChild(QPushButton, "save_btn")
        self.cancel_btn = self.ui.findChild(QPushButton, "cancel_btn")
        
        self.save_btn.clicked.connect(self.validate_and_submit)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.apply_theme()
        
        self.result_data = None

    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                QDialog { background-color: #2d2d2d; color: #e0e0e0; }
                QLabel, QCheckBox { color: #e0e0e0; }
                QLineEdit {
                    background-color: #1e1e1e; color: #ffffff;
                    border: 1px solid #3c3c3c; border-radius: 5px; padding: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #ffffff; color: #333333; }
                QLabel, QCheckBox { color: #333333; }
                QLineEdit {
                    background-color: #ffffff; color: #333333;
                    border: 1px solid #cccccc; border-radius: 5px; padding: 6px;
                }
                #cancel_btn { background-color: #e0e0e0; color: #333333; }
            """)

    def validate_and_submit(self):
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Input Error", "Please specify a label/name for this provider.")
            return
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(self, "Input Error", "Provide valid full endpoint (e.g., http://192.168.x.x:1234/v1).")
            return
            
        # Generate slugified ID safely
        import re
        clean_id = "custom_" + re.sub(r'[^a-z0-9]', '_', name.lower())
        
        self.result_data = {
            "id": clean_id,
            "group": "openai", # standard fallback for dynamic expansion
            "display_name": f"👤 {name} (Custom)",
            "pricing": "🛠️ User-Hosted Custom Endpoint",
            "default_url": url,
            "placeholder_key": "Enter token if required",
            "instructions": f"<b>Connect to Custom Host</b><br><br>Accessing local/private endpoint: {url}",
            "requires_url": True,
            "requires_key": self.requires_key_chk.isChecked(),
            "is_custom": True
        }
        self.accept()

    def get_provider_payload(self):
        return self.result_data
