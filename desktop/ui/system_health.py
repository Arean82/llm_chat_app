# ui/system_health.py
"""
System Health & Telemetry Standalone Observability Dialog.
Monitors execution thread pool, transparent failover statuses,
and Dead Letter Queue fault states in real time.
"""

from PySide6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem, QHeaderView
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QTimer, Qt
from server.utils.path_utils import get_resource_path
from server.logic.queue.job_queue import JobQueueEngine
from server.logic.services import ServiceRegistry
from desktop.ui.shared_widgets import set_app_icon

class SystemHealthDialog(QDialog):
    """
    Standalone diagnostic popup.
    Features green/red LED connection indicators, background thread execution lists,
    and visual fault-recovery controls for the Dead Letter Queue.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        set_app_icon(self)
        
        # Load visual layout
        loader = QUiLoader()
        ui_path = get_resource_path("ui_designer/system_health.ui")
        self.ui = loader.load(str(ui_path), self)
        
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
            self.setFixedSize(self.ui.size())
            
        self.setWindowTitle("📊 System Health & Telemetry Monitor")
        
        # Bind action interactions
        self.ui.btn_close.clicked.connect(self.reject)
        self.ui.btn_retry_task.clicked.connect(self.retry_selected_dlq_job)
        
        # Configure Table Headers layout scaling
        self.ui.table_active_threads.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.table_dlq_tasks.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Hydrate initial layout
        self.ui.lbl_failover_banner.hide()
        self.refresh_diagnostics()
        
        # Connect thread-safe real-time update timer
        self.timer = QTimer(self)
        self.timer.setInterval(2000)  # Pulse updates every 2 seconds
        self.timer.timeout.connect(self.refresh_diagnostics)
        self.timer.start()

    def refresh_diagnostics(self):
        """Updates LEDs and tables with real-time data."""
        # 1. Update Core Connection Status LEDs
        try:
            telemetry = ServiceRegistry.get("telemetry")
            if telemetry:
                health = telemetry.run_health_checks()
                
                def set_led_style(widget, healthy):
                    color = "#10b981" if healthy else "#ef4444"  # Modern green/red
                    widget.setStyleSheet(f"background-color: {color}; border-radius: 8px; min-width: 16px; min-height: 16px; max-width: 16px; max-height: 16px;")
                
                set_led_style(self.ui.lbl_led_storage, health.get("storage") == "HEALTHY")
                set_led_style(self.ui.lbl_led_vector, health.get("vector_db") == "HEALTHY")
                set_led_style(self.ui.lbl_led_cache, health.get("cache") == "HEALTHY")
                set_led_style(self.ui.lbl_led_queue, health.get("queue") == "HEALTHY")
                set_led_style(self.ui.lbl_led_llm, health.get("llm") == "HEALTHY")
                
            # 2. Transparent failover banner warning evaluation
            circuit_breaker = ServiceRegistry.get("circuit_breaker")
            if circuit_breaker:
                if circuit_breaker.state == "OPEN":
                    self.ui.lbl_failover_banner.show()
                else:
                    self.ui.lbl_failover_banner.hide()
        except Exception as e:
            print(f"[Telemetry UI] Error updating health state: {e}")

        # 3. Ingest active worker processing pools
        try:
            queue_engine = JobQueueEngine()
            status = queue_engine.get_queue_status()
            active_list = status.get("processing_jobs", []) + status.get("queued_jobs", [])
            
            self.ui.table_active_threads.setRowCount(len(active_list))
            for row, job in enumerate(active_list):
                self.ui.table_active_threads.setItem(row, 0, QTableWidgetItem(f"WorkerThread-{row+1}"))
                self.ui.table_active_threads.setItem(row, 1, QTableWidgetItem(str(job.get("job_id", ""))))
                self.ui.table_active_threads.setItem(row, 2, QTableWidgetItem(f"Ingest: {job.get('task_type', '')}"))
                self.ui.table_active_threads.setItem(row, 3, QTableWidgetItem(str(job.get("status", "")).upper()))
        except Exception as e:
            print(f"[Telemetry UI] Error updating active threads table: {e}")

        # 4. Ingest Dead Letter Queue table entries
        try:
            queue_engine = JobQueueEngine()
            dlq_entries = queue_engine.get_dlq_entries()
            
            self.ui.table_dlq_tasks.setRowCount(len(dlq_entries))
            for row, entry in enumerate(dlq_entries):
                self.ui.table_dlq_tasks.setItem(row, 0, QTableWidgetItem(str(entry.get("job_id", ""))))
                self.ui.table_dlq_tasks.setItem(row, 1, QTableWidgetItem(str(entry.get("task_type", ""))))
                self.ui.table_dlq_tasks.setItem(row, 2, QTableWidgetItem(str(entry.get("error", ""))))
                self.ui.table_dlq_tasks.setItem(row, 3, QTableWidgetItem(str(entry.get("timestamp", ""))))
        except Exception as e:
            print(f"[Telemetry UI] Error updating DLQ table: {e}")

    def retry_selected_dlq_job(self):
        """Pulls selected job out of Dead Letter Queue and places it back in worker pool."""
        row = self.ui.table_dlq_tasks.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Retry Error", "Please select a failed job from the Dead Letter Queue table first.")
            return
            
        job_id = self.ui.table_dlq_tasks.item(row, 0).text()
        try:
            queue_engine = JobQueueEngine()
            new_job_id = queue_engine.retry_dlq_job(job_id)
            QMessageBox.information(
                self, "Retry Dispatched",
                f"Job '{job_id}' has been removed from DLQ and resubmitted successfully.\n\nNew Background Job ID: {new_job_id}"
            )
            # Rehydrate layout instantly
            self.refresh_diagnostics()
        except Exception as e:
            QMessageBox.critical(self, "Retry Failed", f"An error occurred while retrying the job:\n\n{e}")

    def closeEvent(self, event):
        """Clean up live telemetry polling routine before destruction."""
        self.timer.stop()
        super().closeEvent(event)
