# ui/shared_widgets.py
from PySide6.QtWidgets import QTextEdit, QApplication
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextBlockUserData

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
