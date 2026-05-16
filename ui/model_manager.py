# ui/model_manager.py
# This file defines the ModelManagerDialog class, which provides a UI for managing LLM models. It allows users to add, edit, and delete models that are stored in models.json. The dialog displays a table of existing models with their ID, name, description, and whether they are free or    not. Users can select a model to edit or delete, or add a new model using the ModelEditDialog. Changes are saved back to models.json and the active model selection is updated in QSettings if necessary.  
# The dialog also includes buttons to fetch free and paid models directly from NVIDIA's API, which will merge with existing models while preserving user-added descriptions. The UI is designed to be clean and user-friendly, with support for both light and dark themes. 

import json
import keyring
from PySide6.QtWidgets import (
    QApplication, QDialog, QInputDialog, QMessageBox, QHeaderView, QAbstractItemView, QProgressDialog
)
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor
from PySide6.QtUiTools import QUiLoader

from ui.model_edit_dialog import ModelEditDialog
from utils.path_utils import get_resource_path, get_app_settings
from utils.helpers import set_app_icon
from utils.constants import OPENAI_BASE_URL

class ModelManagerDialog(QDialog):
    """Main dialog for viewing and managing models."""
    _fetch_in_progress = False  # Class-level lock
    _fetch_instance = None       # Track running fetch

    def __init__(self, theme="dark", parent=None, theme_manager=None):
        super().__init__(parent)
        self.theme_manager = theme_manager

        set_app_icon(self) 
        
        # Check if fetch is already running BEFORE initializing UI
        if ModelManagerDialog._fetch_in_progress:
            QMessageBox.warning(
                parent,
                "Fetch in Progress",
                "Model fetch is already running in the background.\n\n"
                "Please wait for it to complete or check the 'Log' menu for updates."
            )
            # Use a timer to reject after the constructor finishes to avoid side effects
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self.reject)
            return

        self.theme = theme
        self.models = []
        self._started_fetch = False # Instance level flag

        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/model_manager.ui")

        # BLANK WINDOW FIX: pass self as parent
        self.ui = loader.load(str(ui_file), self)
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())

        self.setMinimumSize(850, 550)
        self.resize(850, 550)

        # Widget references
        self.header_label = self.findChild(object, "headerLabel")
        self.count_label = self.findChild(object, "countLabel")
        self.info_label = self.findChild(object, "infoLabel")
        self.tabWidget = self.findChild(object, "tabWidget")
        #self.table = self.findChild(object, "table")
        self.add_btn = self.findChild(object, "add_btn")
        self.edit_btn = self.findChild(object, "edit_btn")
        self.delete_btn = self.findChild(object, "delete_btn")
        self.close_btn = self.findChild(object, "close_btn")
        self.refresh_btn = self.findChild(object, "refresh_btn")
        self.fetch_free_btn = self.findChild(object, "fetch_free_btn")
        self.fetch_paid_btn = self.findChild(object, "fetch_paid_btn")
        self.generate_desc_btn = self.findChild(object, "generate_desc_btn")

        #self.setup_table()
        self.setup_connections()
        self.load_models()
        self.populate_table()
        self.apply_theme()

    def populate_table(self):
        """Dynamically create tabs for each developer"""
        from collections import defaultdict
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

        # Group models by developer
        models_by_developer = defaultdict(list)

        for model in self.models:
            developer = model.get('developer', 'Other')
            if not developer:
                developer = 'Other'
            models_by_developer[developer].append(model)

        # Clear existing tabs
        self.tabWidget.clear()

        # Create a tab for each developer
        for developer, models in sorted(models_by_developer.items()):
            # Create container widget
            tab_widget = QWidget()
            layout = QVBoxLayout(tab_widget)

            # Create table with 3 columns (removed Model ID)
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Display Name", "Description", "Free"])
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)

            # Set column widths
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

            # Populate rows
            table.setRowCount(len(models))
            for row, model in enumerate(models):
                # Column 0: Display Name
                table.setItem(row, 0, QTableWidgetItem(model.get("name", "")))

                # Column 1: Description
                table.setItem(row, 1, QTableWidgetItem(model.get("description", "")))

                # Column 2: Free/Paid (Simple Text)
                is_free = model.get("free", True)
                free_text = "✅ Free" if is_free else "💰 Paid"
                free_item = QTableWidgetItem(free_text)
                free_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                free_item.setForeground(QColor("#4caf50") if is_free else QColor("#ff9800"))
                table.setItem(row, 2, free_item)

            table.resizeRowsToContents()

            # Store models for this tab
            table.setProperty("developer", developer)
            table.setProperty("models", models)

            # Connect selection signal
            table.itemSelectionChanged.connect(lambda t=table: self.on_table_selection_changed(t))

            layout.addWidget(table)

            # Add tab with count
            self.tabWidget.addTab(tab_widget, f"{developer} ({len(models)})")

        self.update_count_label()

    def on_table_selection_changed(self, table):
        """Store reference to currently selected table and model"""
        self.current_table = table
        self.current_developer = table.property("developer")
        self.current_models = table.property("models")

        # Get selected row
        current_row = table.currentRow()
        if current_row >= 0 and self.current_models:
            self.current_selected_model = self.current_models[current_row]
            print(f"Selected: {self.current_selected_model.get('name')}")  # Debug
        else:
            self.current_selected_model = None

    def get_selected_row_index(self):
        """Get selected row from current active table"""
        if hasattr(self, 'current_table') and self.current_table:
            row = self.current_table.currentRow()
            return row if row >= 0 else None
        return None

    def get_selected_model(self):
        """Get the currently selected model"""
        if hasattr(self, 'current_selected_model') and self.current_selected_model:
            return self.current_selected_model
        return None

    def setup_table(self):
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)

    def setup_connections(self):
        self.add_btn.clicked.connect(self.add_model)
        self.edit_btn.clicked.connect(self.edit_model)
        self.delete_btn.clicked.connect(self.delete_model)
        self.refresh_btn.clicked.connect(self.refresh_models)
        self.close_btn.clicked.connect(self.accept)
        #self.table.doubleClicked.connect(self.edit_model)

        self.fetch_free_btn.clicked.connect(self.fetch_free_models_from_nvidia)
        self.fetch_paid_btn.clicked.connect(self.fetch_paid_models_from_nvidia)
        self.generate_desc_btn.clicked.connect(self.generate_descriptions) 

    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                }
                QLabel {
                    color: #e0e0e0;
                }
                #headerLabel {
                    font-size: 18px;
                    font-weight: bold;
                    color: #ffffff;
                }
                #countLabel {
                    font-size: 13px;
                    color: #888888;
                    background-color: #1e1e1e;
                    padding: 4px 12px;
                    border-radius: 12px;
                }
                #infoLabel {
                    color: #888888;
                    font-size: 12px;
                }
                QTableWidget {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    gridline-color: #3c3c3c;
                    border: 1px solid #3c3c3c;
                    border-radius: 8px;
                    font-size: 13px;
                    selection-background-color: #0078d4;
                    selection-color: white;
                }
                QTableWidget::item {
                    padding: 8px 12px;
                }
                QTableWidget::item:alternate {
                    background-color: #252526;
                }
                QHeaderView::section {
                    background-color: #333333;
                    color: #ffffff;
                    padding: 12px 10px;
                    border: none;
                    border-bottom: 2px solid #0078d4;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #0078d4;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #106ebe; }
            """)
            self.delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #b71c1c; }
            """)
            self.close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 30px;
                    color: #e0e0e0;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #4c4c4c; }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                }
                #headerLabel {
                    font-size: 18px;
                    font-weight: bold;
                    color: #000000;
                }
                #countLabel {
                    font-size: 13px;
                    color: #666666;
                    background-color: #f0f0f0;
                    padding: 4px 12px;
                    border-radius: 12px;
                }
                #infoLabel {
                    color: #888888;
                    font-size: 12px;
                }
                QTableWidget {
                    background-color: #ffffff;
                    color: #333333;
                    gridline-color: #e0e0e0;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    font-size: 13px;
                    selection-background-color: #0078d4;
                    selection-color: white;
                }
                QTableWidget::item {
                    padding: 8px 12px;
                }
                QTableWidget::item:alternate {
                    background-color: #f9f9f9;
                }
                QHeaderView::section {
                    background-color: #f5f5f5;
                    color: #333333;
                    padding: 12px 10px;
                    border: none;
                    border-bottom: 2px solid #0078d4;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton {
                    background-color: #0078d4;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #106ebe; }
            """)
            self.delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d32f2f;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #b71c1c; }
            """)
            self.close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 30px;
                    color: #333333;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #d0d0d0; }
            """)
  
    def get_models_file_path(self):
        from utils.path_utils import get_models_path
        return get_models_path()

    def load_models(self):
        """Strict isolation: Only load models belonging to the active provider."""
        from logic.model_io import load_all_models
        active_p = get_app_settings().value("active_provider_id", "nvidia")
        
        # Load all but immediately filter to the active ecosystem only
        all_m = load_all_models()
        self.models = [m for m in all_m if m.get('provider', 'nvidia') == active_p]
        
        # Update Header to reflect active ecosystem
        if hasattr(self, 'header_label') and self.header_label:
            self.header_label.setText(f"Manage {active_p.upper()} Ecosystem Models")

    def save_models(self):
        """Saves current state. Only touches the active provider's segments."""
        from logic.model_io import load_all_models, save_all_models
        active_p = get_app_settings().value("active_provider_id", "nvidia")
        
        # To avoid wiping other ecosystems, we load everything else first
        all_other_models = [m for m in load_all_models() if m.get('provider', 'nvidia') != active_p]
        
        # Merge our modified active list with the untouched others
        full_sync_list = all_other_models + self.models
        save_all_models(full_sync_list)

    def update_count_label(self):
        self.count_label.setText(f"{len(self.models)} model(s)")

    def add_model(self):
        dialog = ModelEditDialog(theme=self.theme, parent=self)
        if dialog.exec():
            new_model = dialog.get_model_data()

            for existing in self.models:
                if existing["id"] == new_model["id"]:
                    QMessageBox.warning(
                        self, "Duplicate ID",
                        f"A model with ID '{new_model['id']}' already exists."
                    )
                    return

            self.models.append(new_model)
            self.save_models()
            #self.populate_table()
            #self.table.selectRow(len(self.models) - 1)
            #self.table.scrollToBottom()

    def edit_model(self):
        """Edit the currently selected model"""
        selected_model = self.get_selected_model()
        if selected_model is None:
            QMessageBox.information(self, "No Selection", "Please select a model to edit.")
            return

        print(f"Editing model: {selected_model.get('name')}")  # Debug

        dialog = ModelEditDialog(model_data=selected_model, theme=self.theme, parent=self)

        if dialog.exec():
            updated_model = dialog.get_model_data()

            # Update in self.models
            for i, model in enumerate(self.models):
                if model["id"] == selected_model["id"]:
                    self.models[i] = updated_model
                    break
                
            self.save_models()
            self.populate_table()  # Refresh display

    def delete_model(self):
        row = self.get_selected_row_index()
        if row is None:
            QMessageBox.information(self, "No Selection", "Please select a model to delete.")
            return

        model_name = self.models[row].get("name", self.models[row].get("id", "Unknown"))
        model_id = self.models[row].get("id", "")

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{model_name}'?\n\n"
            f"Model ID: {model_id}\n\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.models[row]
            self.save_models()
            self.populate_table()

    def refresh_models(self):
        self.load_models()
        self.populate_table()

    def fetch_free_models_from_nvidia(self):
        """Fetch models in background - closes dialog after confirmation"""

        # Check if fetch is already running
        if ModelManagerDialog._fetch_in_progress:
            QMessageBox.warning(self, "Fetch Already Running", "Model fetch is already in progress.")
            return

        from logic.llm_client import LLMClient
        from workers.model_fetch_worker import ModelFetchWorker

        settings = get_app_settings()
        active_p = settings.value("active_provider_id", "nvidia")
        api_key = keyring.get_password("LLMChatApp", f"api_key_{active_p}") or keyring.get_password("LLMChatApp", "api_key")
        base_url = settings.value(f"url_{active_p}") or settings.value("base_url", OPENAI_BASE_URL)

        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please set your API key first.")
            return

        # Show confirmation
        reply = QMessageBox.question(
            self,
            "Background Model Fetch",
            f"This will test models and generate descriptions.\n\n"
            f"⏱️ Estimated time: 2-3 minutes\n"
            f"🔄 Process runs in background\n"
            f"📋 Check 'Log' menu for real-time updates\n\n"
            f"Model Manager will close after you confirm.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Set locks
        ModelManagerDialog._fetch_in_progress = True
        self._started_fetch = True

        # Get logger instance
        from workers.update_logger import get_logger
        logger = get_logger()
        logger.add_log("Starting model fetch from NVIDIA API", "INFO")

        # Create and start worker
        self.fetch_worker = ModelFetchWorker(api_key, base_url=base_url)
        self.fetch_worker.progress.connect(self._on_fetch_progress)
        self.fetch_worker.finished.connect(self._on_fetch_finished)
        self.fetch_worker.error.connect(self._on_fetch_error)

        self.fetch_worker.start()

        # CLOSE THE DIALOG
        self.accept()  # This closes Model Manager


    def _on_fetch_progress(self, current, total, model_name, status):
        """Update progress - log to console and logger"""
        from workers.update_logger import get_logger
        logger = get_logger()
        logger.add_log(f"[{current}/{total}] {model_name}: {status}", "INFO")
        print(f"[{current}/{total}] {model_name}: {status}")
    
    def _on_fetch_finished(self, working_models):
        """Save results and refresh"""
        from logic.model_io import save_all_models
        # Re-save ONLY fetched provider list back to their relevant segments securely
        save_all_models(working_models)
        
        # Reload and refresh
        self.load_models()
        self.populate_table()
        
        QMessageBox.information(
            self,
            "Fetch Complete",
            f"✅ Found {len(working_models)} working chat models.\n\n"
            f"Deprecated/non-chat models have been removed from your list."
        )
        
        # Release lock and restore UI
        self._reset_fetch_state()

    def _on_fetch_error(self, error_msg):
        """Handle fetch error with user-friendly messages"""
        from workers.update_logger import get_logger
        logger = get_logger()
        logger.add_log(f"Fetch error: {error_msg}", "ERROR")
        
        error_lower = error_msg.lower()
        
        if "410" in error_msg or "gone" in error_lower:
            friendly_msg = "Some models have reached their end of life (EOL) and are no longer available.\n\nThese models will be automatically removed from your list.\n\nRun 'Fetch Free Models' again to clean up."
        elif "400" in error_msg or "bad request" in error_lower:
            friendly_msg = "Some models are not chat-compatible (embedding, vision-only, etc.) and have been skipped.\n\nThis is normal. Only chat models will appear in your list."
        elif "401" in error_msg or "unauthorized" in error_lower or "invalid" in error_lower:
            friendly_msg = "Invalid or expired API key.\n\nPlease check your NVIDIA API key and try again."
        elif "403" in error_msg or "forbidden" in error_lower:
            friendly_msg = "Access denied. Your API key may not have permission for this operation."
        elif "404" in error_msg or "not found" in error_lower:
            friendly_msg = "Model not found. It may have been removed.\n\nRun 'Fetch Free Models' to update your list."
        elif "408" in error_msg or "timeout" in error_lower:
            friendly_msg = "Request timed out.\n\nPlease check your internet connection and try again."
        elif "429" in error_msg or "rate limit" in error_lower or "too many" in error_lower:
            friendly_msg = "Rate limit exceeded (40 requests per minute).\n\nPlease wait a moment before trying again."
        elif "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg:
            friendly_msg = "NVIDIA service is temporarily unavailable.\n\nPlease try again later."
        elif "connection" in error_lower or "network" in error_lower:
            friendly_msg = "Network connection error.\n\nPlease check your internet connection."
        else:
            friendly_msg = f"Failed to fetch models: {error_msg}\n\nCheck the Log menu for details."
        
        QMessageBox.critical(
            None,
            "Fetch Failed",
            friendly_msg
        )
        
        self._reset_fetch_state()
        
    def _cancel_fetch(self):
        """Cancel background fetch"""
        if hasattr(self, 'fetch_worker') and self.fetch_worker.isRunning():
            self.fetch_worker.requestInterruption()
            self.progress_dialog.setLabelText("Cancelling... Please wait...")
            # Connect to finished signal to reset after worker actually stops
            self.fetch_worker.finished.connect(self._on_cancel_complete)    

    def _on_cancel_complete(self):
        """Reset state after cancel"""
        self._reset_fetch_state()
        self.progress_dialog.close()
    
    def _reset_fetch_state(self):
        """Reset locks and buttons"""
        ModelManagerDialog._fetch_in_progress = False
        ModelManagerDialog._fetch_instance = None
        self._started_fetch = False
        
        self._set_buttons_enabled(True)
        self.fetch_free_btn.setText("🆓 Fetch Free Models")
    
    def closeEvent(self, event):
        """Handle window close during fetch - only trap if THIS instance started it"""
        if self._started_fetch and ModelManagerDialog._fetch_in_progress:
            reply = QMessageBox.question(
                self,
                "Fetch in Progress",
                "Model fetch is still running in background.\n\n"
                "Closing this window will NOT cancel the fetch.\n"
                "The fetch will continue and save results.\n\n"
                "Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()
    
    def fetch_paid_models_from_nvidia(self):
        """Fetch paid models and MERGE with existing free models"""
        from logic.llm_client import LLMClient
        from workers.update_logger import get_logger
        
        settings = get_app_settings()
        active_p = settings.value("active_provider_id", "nvidia")
        api_key = keyring.get_password("LLMChatApp", f"api_key_{active_p}") or keyring.get_password("LLMChatApp", "api_key")
        base_url = settings.value(f"url_{active_p}") or settings.value("base_url", OPENAI_BASE_URL)
        
        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please set your NVIDIA API key first.")
            return
        
        # Show confirmation
        reply = QMessageBox.question(
            self,
            "Fetch Paid Models",
            f"This will fetch paid models accessible with your API key.\n\n"
            f"Paid models will be ADDED to your existing free models.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        ModelManagerDialog._fetch_in_progress = True
        self.accept()  # Close dialog
        
        logger = get_logger()
        logger.add_log("Starting paid models fetch...", "INFO")
        
        # Create and start worker for paid models
        from workers.paid_model_fetch_worker import PaidModelFetchWorker
        self.paid_fetch_worker = PaidModelFetchWorker(api_key, base_url=base_url)
        self.paid_fetch_worker.progress.connect(self._on_paid_fetch_progress)
        self.paid_fetch_worker.finished.connect(self._on_paid_fetch_finished)
        self.paid_fetch_worker.error.connect(self._on_paid_fetch_error)
        self.paid_fetch_worker.start() 

    def _filter_paid_models(self, all_models: list) -> list:
        """
        Filter paid models from the list.
        Since NVIDIA API doesn't mark free/paid, we use heuristics:
        - Models with certain providers are free
        - Others are considered paid (may require subscription)
        """
        # Known free providers (always free on NVIDIA free tier)
        free_providers = ['meta', 'google', 'microsoft', 'mistralai', 'deepseek-ai', 'z-ai']
        
        # Keywords that indicate free tier models
        free_keywords = ['free', 'nano', 'lite', 'small', 'gemma', 'llama']
        
        # Keywords that indicate paid models
        paid_keywords = ['ultra', 'pro', 'plus', 'max', 'premium', 'enterprise']
        
        paid_models = []
        
        for model in all_models:
            model_id = model['id'].lower()
            provider = model_id.split('/')[0] if '/' in model_id else ''
            
            # Check if it's likely free
            is_likely_free = (
                provider in free_providers or
                any(keyword in model_id for keyword in free_keywords)
            )
            
            # Check if it's explicitly marked as paid
            is_explicitly_paid = any(keyword in model_id for keyword in paid_keywords)
            
            # If not likely free OR explicitly paid, consider it paid
            if not is_likely_free or is_explicitly_paid:
                model['free'] = False
                paid_models.append(model)
        
        print(f"Filtered {len(paid_models)} paid models from {len(all_models)} total")
        return paid_models
    
    def fetch_all_models_from_nvidia(self):
        """
        NEW: Fetch ALL models (free + paid) in one go.
        Add this as a third button if you want.
        """
        from logic.llm_client import LLMClient
        
        settings = get_app_settings()
        active_p = settings.value("active_provider_id", "nvidia")
        api_key = keyring.get_password("LLMChatApp", f"api_key_{active_p}") or keyring.get_password("LLMChatApp", "api_key")
        # Setup base_url if needed by model handlers internally
        base_url = settings.value(f"url_{active_p}") or settings.value("base_url", OPENAI_BASE_URL)
        
        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please set your NVIDIA API key first.")
            return
        
        self.setCursor(Qt.CursorShape.WaitCursor)
        
        try:
            client = LLMClient()
            client.set_api_key(api_key)
            result = client.fetch_nvidia_catalog_models()
            
            # Mark which are likely paid vs free
            for model in result["all"]:
                model['free'] = self._is_likely_free_model(model['id'])
            
            # Save all models
            merged_models = self._merge_models_with_api(result["all"])
            self._save_models_to_file(merged_models)
            
            self.load_models()
            self.populate_table()
            
            free_count = sum(1 for m in result["all"] if self._is_likely_free_model(m['id']))
            paid_count = len(result["all"]) - free_count
            
            QMessageBox.information(
                self,
                "Success",
                f"✅ Fetched {len(result['all'])} total models:\n"
                f"   🆓 Free: {free_count}\n"
                f"   💎 Paid: {paid_count}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch models: {str(e)}")
        finally:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    
    def _is_likely_free_model(self, model_id: str) -> bool:
        """Helper to determine if a model is likely free"""
        free_providers = ['meta', 'google', 'microsoft', 'mistralai']
        free_keywords = ['free', 'nano', 'lite', 'small', 'gemma', 'llama']
        
        model_id_lower = model_id.lower()
        provider = model_id_lower.split('/')[0] if '/' in model_id_lower else ''
        
        return (
            provider in free_providers or
            any(keyword in model_id_lower for keyword in free_keywords)
        )
            
    def _set_buttons_enabled(self, enabled: bool):
        """Enable/disable all action buttons"""
        self.add_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)
        self.fetch_free_btn.setEnabled(enabled)
        self.fetch_paid_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        # Don't disable close button

    def _merge_models_with_api(self, api_models: list) -> list:
        """
        Merge API-fetched models with existing models.json data.
        Preserves existing descriptions while updating IDs and names.
        REMOVES models that no longer exist in the API.
        """
        # Load existing models
        models_file = self.get_models_file_path()
        existing_models = []    

        if models_file.exists():
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_models = data.get("models", [])    

        # Create lookup dict for existing models by ID
        existing_lookup = {m["id"]: m for m in existing_models}

        # Create set of API model IDs
        api_model_ids = {m["id"] for m in api_models}   

        # Track removed models
        removed_models = []
        for existing_id in existing_lookup.keys():
            if existing_id not in api_model_ids:
                removed_models.append(existing_id)  

        # Merge: API models override IDs/names, but preserve descriptions from existing
        merged = []
        for api_model in api_models:
            model_id = api_model["id"]  

            if model_id in existing_lookup:
                # Preserve existing description if available
                api_model["description"] = existing_lookup[model_id].get("description", "")
                api_model["free"] = existing_lookup[model_id].get("free", True) 

            merged.append(api_model)    

        # Log removed models
        if removed_models:
            print(f"Removing {len(removed_models)} deprecated models:")
            for removed in removed_models[:10]:  # Show first 10
                print(f"  - {removed}")
            if len(removed_models) > 10:
                print(f"  ... and {len(removed_models) - 10} more") 

        return merged   

    def _save_models_to_file(self, models: list):
        """OVERWRITE models.json with clean filtered models only"""
        models_file = self.get_models_file_path()
        data = {"models": models}

        with open(models_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"✅ Saved {len(models)} models to {models_file}")

    def generate_descriptions(self):
        """Generate descriptions for models using a selected model"""
        from workers.update_logger import get_logger
        from PySide6.QtWidgets import QInputDialog

        # Find models without descriptions
        models_to_update = []
        for model in self.models:
            desc = model.get('description', '')
            if not desc or len(desc) < 10 or desc == "No description available":
                models_to_update.append(model)

        if not models_to_update:
            QMessageBox.information(self, "No Models", "All models already have descriptions.")
            return

        # Get list of models that can be used for generation (chat models)
        available_generators = [m for m in self.models if m.get('free', True)]
        generator_names = [m.get('name', m['id']) for m in available_generators]

        # Select model to use for generation
        selected_name, ok = QInputDialog.getItem(
            self,
            "Select Generator Model",
            f"Choose a model to generate descriptions for {len(models_to_update)} models:",
            generator_names,
            0,
            False
        )

        if not ok or not selected_name:
            return

        # Find selected model
        selected_model = next((m for m in available_generators if m.get('name', m['id']) == selected_name), None)
        if not selected_model:
            return

        # Get API key
        settings = get_app_settings()
        api_key = settings.value("api_key", "")

        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please set your API key first.")
            return

        # Close dialog and run in background
        ModelManagerDialog._fetch_in_progress = True
        self.accept()

        # Start worker
        from workers.description_generator import DescriptionGeneratorWorker
        self.generator_worker = DescriptionGeneratorWorker(api_key, selected_model['id'], models_to_update)
        self.generator_worker.progress.connect(self._on_generation_progress)
        self.generator_worker.finished.connect(self._on_generation_finished)
        self.generator_worker.error.connect(self._on_generation_error)
        self.generator_worker.start()

    def _on_generation_progress(self, current, total, model_name, status):
        from workers.update_logger import get_logger
        logger = get_logger()
        logger.add_log(f"[{current}/{total}] {model_name}: {status}", "INFO")

    def _on_generation_finished(self):
        from workers.update_logger import get_logger
        logger = get_logger()
        logger.add_log("Description generation complete!", "SUCCESS")
        ModelManagerDialog._fetch_in_progress = False

    def _on_generation_error(self, error_msg):
        from workers.update_logger import get_logger
        logger = get_logger()
        logger.add_log(f"Generation error: {error_msg}", "ERROR")
        ModelManagerDialog._fetch_in_progress = False

