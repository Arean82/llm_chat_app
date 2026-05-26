# ui/user_login.py
# Native desktop admin login gate controller

from PySide6.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import Qt, QSettings
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QBrush, QPainterPath

from utils.path_utils import get_resource_path
from ui.shared_widgets import set_app_icon
from saas.tenant_db import TenantDatabaseManager
import utils.security_utils as security_utils

def create_eye_icon(visible: bool) -> QIcon:
    from PySide6.QtCore import Qt
    
    # 32x32 high-DPI canvas
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Set the eye vector outlines to a high-fidelity pure white color
    color_hex = "#ffffff"
    pen = QPen(QColor(color_hex), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    
    if visible:
        # 🟢 Premium Open Eye (Bezier Almond Path + Iris + Pupil Catchlight)
        path = QPainterPath()
        path.moveTo(4, 16)
        # Smooth cubic bezier curves for a organic, gorgeous eye shape
        path.cubicTo(10, 7, 22, 7, 28, 16)  # Top eyelid
        path.cubicTo(22, 25, 10, 25, 4, 16) # Bottom eyelid
        painter.drawPath(path)
        
        # Outer iris outline
        painter.drawEllipse(11, 11, 10, 10)
        
        # Solid Pupil
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(13, 13, 6, 6)
        
        # Bright glass catchlight reflection
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(16, 12, 2.5, 2.5)
    else:
        # 🔴 Gorgeous Closed/Sleeping Eye with Delicate downward Eyelashes
        path = QPainterPath()
        path.moveTo(4, 13)
        # Curve representing the closed eyelid dipping down gracefully
        path.cubicTo(10, 22, 22, 22, 28, 13)
        painter.drawPath(path)
        
        # Elegant stylized downward eyelashes
        # Lash 1 (Left-most)
        painter.drawLine(9, 18, 7, 22)
        # Lash 2 (Mid-Left)
        painter.drawLine(13, 20, 11, 25)
        # Lash 3 (Center)
        painter.drawLine(16, 21, 16, 26)
        # Lash 4 (Mid-Right)
        painter.drawLine(19, 20, 21, 25)
        # Lash 5 (Right-most)
        painter.drawLine(23, 18, 25, 22)
        
    painter.end()
    return QIcon(pixmap)

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
        self.setWindowTitle("Quantum Admin Login")
        
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
