# ui/shared_widgets.py
from PySide6.QtWidgets import QTextEdit, QApplication
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextBlockUserData, QIcon

class MessageData(QTextBlockUserData):
    def __init__(self, text):
        super().__init__()
        self.text = text

class ChatDisplay(QTextEdit):
    # Signal emitted when special markdown actions (like run_code or copy_code) are clicked
    link_activated = Signal(str, str) # (action_type, base64_data)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        cursor = self.cursorForPosition(event.pos())
        cf = cursor.charFormat()
        
        if cf.isAnchor():
            href = cf.anchorHref()
            
            # 1. New Dynamic Hook Architecture (handles run_code:... copy_code:...)
            if ":" in href:
                try:
                    parts = href.split(":", 1)
                    action = parts[0]
                    payload = parts[1]
                    self.link_activated.emit(action, payload)
                    return
                except: pass
                
            # 2. Legacy Logic Fallback for original standalone copy tag
            if href == "copy":
                block = cursor.block()
                data = block.userData()
                if not data: 
                    pb = block.previous()
                    if pb.isValid(): data = pb.userData()
                if data and hasattr(data, 'text'):
                    QApplication.clipboard().setText(data.text)

def set_app_icon(window):
    """Applies the app icon to any window passed to it."""
    from server.utils.path_utils import get_resource_path
    import platform
    
    print(f"[Icon Loader] set_app_icon called for: {window}")
    
    icon_name = "app_icon.ico" if platform.system() == "Windows" else "app_icon.png"
    icon_path = get_resource_path(f"resources/{icon_name}")
    print(f"[Icon Loader] Target icon path: {icon_path} (exists: {icon_path.exists()})")
    
    icon = None
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        print(f"[Icon Loader] Loaded QIcon from {icon_name}. isNull: {icon.isNull()}")
        
    # Fallback to PNG if ICO doesn't exist or is null
    if not icon or icon.isNull():
        png_path = get_resource_path("resources/app_icon.png")
        print(f"[Icon Loader] ICO failed or null. Trying fallback PNG: {png_path} (exists: {png_path.exists()})")
        if png_path.exists():
            icon = QIcon(str(png_path))
            print(f"[Icon Loader] Loaded fallback PNG. isNull: {icon.isNull()}")
            if icon.isNull():
                print(f"[Icon Loader] Warning: PNG icon is null: {png_path}")
        else:
            print(f"[Icon Loader] Warning: PNG icon does not exist: {png_path}")
            
    if icon and not icon.isNull():
        window.setWindowIcon(icon)
        print(f"[Icon Loader] Successfully called setWindowIcon on {window}")
    else:
        print("[Icon Loader] Error: Failed to set any valid application icon.")

