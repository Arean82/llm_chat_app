# ui/user_login.py
# Native desktop admin login gate controller

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import Qt, QSettings
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QBrush, QPainterPath

from server.utils.path_utils import get_resource_path
from desktop.ui.shared_widgets import set_app_icon
from web.core.tenant_db import TenantDatabaseManager
import server.utils.security_utils as security_utils

def create_eye_icon(visible: bool) -> QIcon:
    if visible:
        return QIcon(str(get_resource_path("resources/eye_open.svg")))
    else:
        return QIcon(str(get_resource_path("resources/eye_closed.svg")))

class UserLoginClass(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Load UI Designer file
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/user_login.ui")
        self.ui = loader.load(str(ui_file))
        
        # Mount UI
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        
        # Lock visual size to match the UI Designer layout specification perfectly
        if self.ui:
            self.setFixedSize(self.ui.size())
        
        # Styling and Window config
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        set_app_icon(self)
        self.setWindowTitle("Synora Admin Login")
        
        # 2. Extract widgets
        self.txt_username = self.ui.findChild(QLineEdit, "txt_username")
        self.txt_password = self.ui.findChild(QLineEdit, "txt_password")
        self.btn_login = self.ui.findChild(QPushButton, "btn_login")
        self.btn_cancel = self.ui.findChild(QPushButton, "btn_cancel")
        
        # 3. Connections
        self.btn_login.clicked.connect(self.handle_login)
        self.btn_cancel.clicked.connect(self.reject)
        
        # Setup Password Visibility Toggle Action (Eye button inside QLineEdit)
        from PySide6.QtGui import QAction
        self.btn_toggle_password = QAction(self)
        self.btn_toggle_password.setIcon(create_eye_icon(visible=False))
        self.btn_toggle_password.setToolTip("Show Password")
        self.txt_password.addAction(self.btn_toggle_password, QLineEdit.TrailingPosition)
        self.btn_toggle_password.triggered.connect(self.toggle_password_visibility)
        
        # Connect enter key on inputs
        self.txt_username.returnPressed.connect(self.handle_login)
        self.txt_password.returnPressed.connect(self.handle_login)
        
        # Hydrate default admin username for convenience
        self.txt_username.setText("admin")
        self.txt_password.setFocus()

    def toggle_password_visibility(self):
        if self.txt_password.echoMode() == QLineEdit.Password:
            self.txt_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_password.setIcon(create_eye_icon(visible=True))
            self.btn_toggle_password.setToolTip("Hide Password")
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_password.setIcon(create_eye_icon(visible=False))
            self.btn_toggle_password.setToolTip("Show Password")

    def handle_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Please enter both Username and Password.")
            return
            
        try:
            db = TenantDatabaseManager()
            user = db.authenticate_by_login(username, password)
            
            if user:
                # Desktop is strictly restricted to SaaS Master Admins
                is_admin = user.get("key_type") == "admin_funded" or user.get("username") == "admin"
                if not is_admin:
                    QMessageBox.critical(
                        self, 
                        "Access Denied", 
                        "Security Warning: Desktop GUI administration tools are strictly gated to the Master Admin.\n\n"
                        "Standard BYOK tenants must access their workspace via the SaaS Web Dashboard."
                    )
                    return
                
                # Zero-trust linkage: cache password inside the session transient memory vault
                security_utils.SESSION_MASTER_PASSWORD = password
                self.accept()
            else:
                QMessageBox.critical(self, "Authentication Failed", "Invalid Master Admin credentials. Please try again.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to local tenant database:\n\n{e}")
