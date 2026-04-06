# ui/styles.py
from pathlib import Path


def load_stylesheet() -> str:
    """Load and return the stylesheet"""
    stylesheet_path = Path(__file__).parent / "styles.qss"
    
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Default stylesheet if file doesn't exist
    return """
    /* Main Window */
    QMainWindow {
        background-color: #252526;
    }
    
    /* Sidebar */
    #sidebar {
        background-color: #1e1e1e;
        border-right: 1px solid #3c3c3c;
    }
    
    /* Chat Area */
    #chat-area {
        background-color: #252526;
    }
    
    /* Chat Display */
    #chat-display {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border: 1px solid #3c3c3c;
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Messages */
    .message {
        margin: 10px 0;
    }
    
    .user-message {
        text-align: right;
    }
    
    .assistant-message {
        text-align: left;
    }
    
    .message-bubble {
        display: inline-block;
        padding: 8px 12px;
        border-radius: 12px;
        max-width: 80%;
    }
    
    .user-message .message-bubble {
        background-color: #0078d4;
        color: white;
    }
    
    .assistant-message .message-bubble {
        background-color: #2d2d2d;
        color: #d4d4d4;
    }
    
    .system-message {
        text-align: center;
        background-color: #3c3c3c;
        color: #ffd700;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 12px;
        margin: 10px auto;
        display: inline-block;
        width: auto;
    }
    
    .typing-indicator {
        margin: 10px 0;
    }
    
    /* Code Blocks */
    .code-block {
        background-color: #1e1e1e;
        border-left: 3px solid #0078d4;
        padding: 10px;
        border-radius: 5px;
        overflow-x: auto;
        font-family: Consolas, monospace;
        margin: 10px 0;
    }
    
    .inline-code {
        background-color: #3c3c3c;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: Consolas, monospace;
    }
    
    /* List Widget */
    QListWidget {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border: 1px solid #3c3c3c;
        border-radius: 5px;
        padding: 5px;
    }
    
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #3c3c3c;
    }
    
    QListWidget::item:selected {
        background-color: #0078d4;
    }
    
    QListWidget::item:hover {
        background-color: #2d2d2d;
    }
    
    /* Current Model Label */
    #current-model {
        background-color: #2d2d2d;
        padding: 8px;
        border-radius: 5px;
        margin-top: 10px;
    }
    
    /* Status Label */
    #status {
        padding: 5px;
        margin-top: 10px;
    }
    
    #status[connected="true"] {
        color: #4caf50;
    }
    
    #status[connected="false"] {
        color: #f44336;
    }
    
    /* Buttons */
    QPushButton {
        background-color: #0078d4;
        border: none;
        border-radius: 5px;
        padding: 8px;
        color: white;
        font-weight: bold;
    }
    
    QPushButton:hover {
        background-color: #106ebe;
    }
    
    QPushButton:pressed {
        background-color: #005a9e;
    }
    
    QPushButton:disabled {
        background-color: #3c3c3c;
    }
    
    #send-btn {
        background-color: #0078d4;
    }
    
    /* Input Field */
    #input-field {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #3c3c3c;
        border-radius: 5px;
        padding: 8px;
    }
    
    #input-field:focus {
        border: 1px solid #0078d4;
    }
    
    /* Settings Dialog */
    #instructions {
        background-color: #2d2d2d;
        padding: 10px;
        border-radius: 5px;
    }
    
    #key-label {
        font-weight: bold;
        margin-top: 10px;
    }
    
    #key-input {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #3c3c3c;
        border-radius: 5px;
        padding: 8px;
    }
    
    /* Scrollbar */
    QScrollBar:vertical {
        background-color: #1e1e1e;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #0078d4;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #106ebe;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    /* Menu Bar */
    QMenuBar {
        background-color: #1e1e1e;
        color: #d4d4d4;
    }
    
    QMenuBar::item:selected {
        background-color: #0078d4;
    }
    
    QMenu {
        background-color: #1e1e1e;
        color: #d4d4d4;
        border: 1px solid #3c3c3c;
    }
    
    QMenu::item:selected {
        background-color: #0078d4;
    }
    """