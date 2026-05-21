# utils/logger.py
import sys
import logging
from pathlib import Path
from utils.storage_config import StorageManager

class PrintLogger:
    """Redirects print statements to the central logger if debug prints are enabled."""
    def __init__(self, logger, original_stdout):
        self.logger = logger
        self.original_stdout = original_stdout

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.debug(line.strip())
        self.original_stdout.write(buf)

    def flush(self):
        self.original_stdout.flush()

class AppLogger:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AppLogger()
        return cls._instance

    def __init__(self):
        self.logger = logging.getLogger("QuantumApp")
        self.logger.propagate = False
        self.formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.console_handler)
        
        self.file_handler = None
        self._original_stdout = sys.stdout
        self._hooked = False
        
        self.reconfigure()

    def reconfigure(self):
        settings = StorageManager.get_instance().get_active_settings()
        enable_log = str(settings.value("logging/enable_log", "false")).lower() == "true"
        enable_debug = str(settings.value("logging/enable_debug", "false")).lower() == "true"
        
        level = logging.DEBUG if enable_debug else logging.INFO
        self.logger.setLevel(level)
        self.console_handler.setLevel(level)
        
        # Handle file writing
        if enable_log:
            if not self.file_handler:
                storage_root = StorageManager.get_instance().get_storage_root()
                log_dir = storage_root / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / "app.log"
                
                self.file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
                self.file_handler.setFormatter(self.formatter)
                self.logger.addHandler(self.file_handler)
            self.file_handler.setLevel(level)
        else:
            if self.file_handler:
                self.logger.removeHandler(self.file_handler)
                self.file_handler.close()
                self.file_handler = None
                
        # Hook global stdout for debug prints
        if enable_debug and enable_log and not self._hooked:
            sys.stdout = PrintLogger(self.logger, self._original_stdout)
            self._hooked = True
        elif not (enable_debug and enable_log) and self._hooked:
            sys.stdout = self._original_stdout
            self._hooked = False

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)
        
    def debug(self, msg):
        self.logger.debug(msg)

    def warning(self, msg):
        self.logger.warning(msg)
