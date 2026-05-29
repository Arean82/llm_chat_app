# workers/connection_worker.py
from PySide6.QtCore import QThread, Signal
import socket

class ConnectionWorker(QThread):
    """
    Background worker that checks for internet connectivity 
    without blocking the main GUI thread.
    """
    status_changed = Signal(bool)

    def __init__(self, host="8.8.8.8", port=53, timeout=2, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.timeout = timeout
        self._running = True

    def run(self):
        while not self.isInterruptionRequested() and self._running:
            connected = self.check_connection()
            self.status_changed.emit(connected)
            
            # Granular sleep to allow instant interruption
            # Total wait: 10s if connected, 3s if disconnected
            wait_time = 10000 if connected else 3000
            elapsed = 0
            while elapsed < wait_time and not self.isInterruptionRequested() and self._running:
                self.msleep(100)
                elapsed += 100

    def check_connection(self):
        try:
            socket.create_connection((self.host, self.port), self.timeout)
            return True
        except OSError:
            return False

    def stop(self):
        self._running = False
