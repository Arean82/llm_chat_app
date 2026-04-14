# workers/update_logger.py
from PySide6.QtCore import QObject, Signal
from datetime import datetime
from pathlib import Path

class UpdateLogger(QObject):
    new_log = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.log_file = Path.home() / "LLMChatApp" / "update_log.txt"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.logs = []
        
    def add_log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.logs.append(log_entry)
        self.new_log.emit(log_entry)
        
        # Also write to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
    
    def get_logs(self):
        return self.logs
    
    def clear(self):
        self.logs = []
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("")
        self.add_log("Log cleared", "SYSTEM")

# Singleton instance
_logger_instance = None

def get_logger():
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = UpdateLogger()
    return _logger_instance