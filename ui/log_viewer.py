# ui/log_viewer.py
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from utils.path_utils import get_resource_path
from workers.update_logger import get_logger

class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/log_viewer.ui")
        self.ui = loader.load(str(ui_file), self)
        
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
        
        self.setWindowTitle("Update Log")
        self.setMinimumSize(900, 650)
        
        # Get logger instance
        self.logger = get_logger()
        
        # Store all logs for filtering
        self.all_logs = []
        
        # Connect buttons
        self.ui.clearBtn.clicked.connect(self.clear_log)
        self.ui.closeBtn.clicked.connect(self.accept)
        self.ui.CloseBtn.clicked.connect(self.accept)
        
        # Connect filter buttons
        self.ui.successBtn.clicked.connect(self.apply_filter)
        self.ui.infoBtn.clicked.connect(self.apply_filter)
        self.ui.warningBtn.clicked.connect(self.apply_filter)
        self.ui.errorBtn.clicked.connect(self.apply_filter)
        self.ui.debugBtn.clicked.connect(self.apply_filter)
        
        # Load existing logs
        self.load_logs()
        
        # Connect for new logs
        self.logger.new_log.connect(self.on_new_log)
    
    def load_logs(self):
        """Load existing logs from file"""
        self.all_logs = []
        log_file = self.logger.log_file
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.all_logs.append(line)
        self.apply_filter()
    
    def on_new_log(self, log_entry: str):
        """Add new log entry"""
        self.all_logs.append(log_entry)
        self.apply_filter()
    
    def apply_filter(self):
        """Filter logs based on selected levels"""
        self.ui.textBrowser.clear()
        
        # Get which levels are selected
        show_success = self.ui.successBtn.isChecked()
        show_info = self.ui.infoBtn.isChecked()
        show_warning = self.ui.warningBtn.isChecked()
        show_error = self.ui.errorBtn.isChecked()
        show_debug = self.ui.debugBtn.isChecked()
        
        # Color mapping
        colors = {
            "SUCCESS": "#2196F3",
            "INFO": "#4CAF50",
            "WARNING": "#FFC107",
            "ERROR": "#F44336",
            "DEBUG": "#9C27B0",
            "SYSTEM": "#888888"
        }
        
        for log in self.all_logs:
            # Determine log level
            level = "INFO"
            if "SUCCESS" in log:
                level = "SUCCESS"
            elif "WARNING" in log:
                level = "WARNING"
            elif "ERROR" in log:
                level = "ERROR"
            elif "DEBUG" in log:
                level = "DEBUG"
            elif "SUCCESS" in log:
                level = "SUCCESS"
            elif "SYSTEM" in log:
                level = "SYSTEM"
            
            # Check if this level should be shown
            show = False
            if level == "SUCCESS" and show_success:
                show = True
            elif level == "INFO" and show_info:
                show = True
            elif level == "WARNING" and show_warning:
                show = True
            elif level == "ERROR" and show_error:
                show = True
            elif level == "DEBUG" and show_debug:
                show = True
            elif level == "SUCCESS" and show_info:  # SUCCESS shown with INFO
                show = True
            elif level == "SYSTEM" and show_info:   # SYSTEM shown with INFO
                show = True
            
            if show:
                color = colors.get(level, "#FFFFFF")
                colored_log = f'<span style="color: {color};">{log}</span>'
                self.ui.textBrowser.append(colored_log)
        
        # Auto-scroll to bottom
        scrollbar = self.ui.textBrowser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Clear all logs"""
        reply = QMessageBox.question(
            self,
            "Clear Log",
            "Are you sure you want to clear all logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.clear()
            self.all_logs = []
            self.ui.textBrowser.clear()