# ui/log_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from workers.update_logger import get_logger

class LogDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Log")
        self.setMinimumSize(600, 400)
        self.setModal(False)
        
        layout = QVBoxLayout(self)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        button_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        close_btn = QPushButton("Close")
        
        clear_btn.clicked.connect(self.clear_log)
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        # Connect logger
        self.logger = get_logger()
        self.logger.new_log.connect(self.append_log)
        
        # Load existing logs
        for log in self.logger.get_logs():
            self.log_text.append(log)
    
    def append_log(self, log_entry: str):
        self.log_text.append(log_entry)
        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def clear_log(self):
        self.logger.clear()
        self.log_text.clear()