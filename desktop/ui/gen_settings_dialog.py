# ui/gen_settings_dialog.py
import os
import uuid
from PySide6.QtWidgets import QDialog, QVBoxLayout, QDoubleSpinBox, QSpinBox, QComboBox, QLabel, QPushButton, QCheckBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QSettings, Qt
from PySide6.QtGui import QIcon

from server.utils.path_utils import get_resource_path, get_app_settings
from desktop.ui.shared_widgets import set_app_icon

class GenSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Generation Parameters")
        self.setMinimumWidth(480)
        
        # Ensure appropriate taskbar handling for user convenience
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        set_app_icon(self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal) # Freeze main window until this closes
        self.showNormal() # Crucial safety check to ensure visual surfacing
        
        # --- APPLY VISUAL THEME STYLES ---
        settings = get_app_settings()
        is_dark = settings.value("theme", "light") == "dark"
        if is_dark:
            self.setStyleSheet("""
                QDialog { background-color: #252526; color: #ffffff; }
                QLabel { color: #ffffff; }
                QDoubleSpinBox, QSpinBox, QComboBox { 
                    background-color: #2d2d2d; 
                    color: #ffffff; 
                    border: 1px solid #3c3c3c; 
                    border-radius: 5px; 
                    padding: 5px; 
                }
                QDoubleSpinBox:disabled, QSpinBox:disabled {
                    background-color: #1e1e1e; 
                    color: #777777; 
                    border: 1px solid #252526;
                }
                QAbstractItemView {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    selection-background-color: #0078d4;
                }
                QTabWidget::pane {
                    border: 1px solid #3c3c3c;
                    border-radius: 6px;
                    background-color: #1e1e1e;
                    padding: 10px;
                }
                QTabBar::tab {
                    background: #2d2d2d;
                    color: #aaaaaa;
                    padding: 8px 16px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    margin-right: 2px;
                    border: 1px solid #3c3c3c;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background: #1e1e1e;
                    color: #ffffff;
                    font-weight: bold;
                    border-bottom: 2px solid #0078d4;
                }
                QTabBar::tab:hover {
                    background: #252526;
                    color: #ffffff;
                }
                QPushButton#cancel_btn { 
                    background-color: #3c3c3c; 
                    color: white; 
                    border: none; 
                    padding: 6px; 
                    border-radius: 4px; 
                }
                QPushButton#cancel_btn:hover { background-color: #4c4c4c; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #ffffff; color: #333333; }
                QDoubleSpinBox, QSpinBox, QComboBox { 
                    background-color: #f5f5f5; 
                    border: 1px solid #cccccc; 
                    border-radius: 5px; 
                    padding: 5px; 
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    background-color: #fafafa;
                    padding: 10px;
                }
                QTabBar::tab {
                    background: #e1e1e1;
                    color: #666666;
                    padding: 8px 16px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    margin-right: 2px;
                    border: 1px solid #cccccc;
                    border-bottom: none;
                }
                QTabBar::tab:selected {
                    background: #fafafa;
                    color: #0078d4;
                    font-weight: bold;
                    border-bottom: 2px solid #0078d4;
                }
                QTabBar::tab:hover {
                    background: #f0f0f0;
                    color: #333333;
                }
                QPushButton#cancel_btn { 
                    background-color: #e1e1e1; 
                    border: 1px solid #cccccc; 
                    padding: 6px; 
                    border-radius: 4px; 
                }
            """)
        
        # Load from XML UI using the established, reliable loading pattern
        loader = QUiLoader()
        ui_file_path = get_resource_path("ui_designer/gen_settings.ui")
        
        # Load the UI container passing self as parent to attach properly
        self.ui = loader.load(str(ui_file_path), self)
        
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
            
        self.setMinimumSize(500, 480)
        self.resize(500, 480)
        
        # Bind references
        self.preset_combo = self.findChild(QComboBox, "preset_combo")
        self.temp_input = self.findChild(QDoubleSpinBox, "temp_input")
        self.tokens_input = self.findChild(QSpinBox, "tokens_input")
        self.temp_desc = self.findChild(QLabel, "temp_desc")
        self.token_desc = self.findChild(QLabel, "token_desc")
        self.save_btn = self.findChild(QPushButton, "save_btn")
        self.cancel_btn = self.findChild(QPushButton, "cancel_btn")
        
        # Logging Bindings
        self.log_enable_cb = self.findChild(QCheckBox, "log_enable_cb")
        self.debug_enable_cb = self.findChild(QCheckBox, "debug_enable_cb")
        
        # Signal bindings
        if self.temp_input:
            self.temp_input.valueChanged.connect(self.update_temp_explanation)
        if self.tokens_input:
            self.tokens_input.valueChanged.connect(self.update_tokens_explanation)
        if self.preset_combo:
            self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        if self.save_btn:
            self.save_btn.clicked.connect(self.save_and_close)
        if self.cancel_btn:
            self.cancel_btn.clicked.connect(self.reject)
        
        self.setup_rerank_ui(is_dark)
        self.setup_api_credentials_ui()
        self.setup_redis_ui(is_dark)
        self.load_current_settings()
        
    def setup_api_credentials_ui(self):
        from PySide6.QtWidgets import QTextEdit, QPushButton
        self.api_key_display = self.findChild(QTextEdit, "api_key_display")
        self.toggle_api_btn = self.findChild(QPushButton, "toggle_api_btn")
        self.regen_key_btn = self.findChild(QPushButton, "regen_key_btn")
        
        if not (self.api_key_display and self.toggle_api_btn and self.regen_key_btn):
            return
            
        settings = get_app_settings()
        
        # Load state
        self.api_enabled = str(settings.value("api_enabled", "true")).lower() == "true"
        current_key = settings.value("local_api_auth_key", "")
        if not current_key:
            current_key = f"llm-local-auth-{uuid.uuid4().hex[:10]}"
            settings.setValue("local_api_auth_key", current_key)
            settings.sync()
            
        self.api_key_display.setText(current_key)
        self.update_api_buttons_ui()
        
        # Connect signals
        self.toggle_api_btn.clicked.connect(self.on_toggle_api)
        self.regen_key_btn.clicked.connect(self.on_regen_key)

    def update_api_buttons_ui(self):
        if self.api_enabled:
            self.toggle_api_btn.setText("Disable API")
            self.toggle_api_btn.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; border-radius: 4px; padding: 6px;")
            self.regen_key_btn.setEnabled(True)
            self.regen_key_btn.setStyleSheet("background-color: #0078d4; color: white; font-weight: bold; border-radius: 4px; padding: 6px;")
        else:
            self.toggle_api_btn.setText("Enable API")
            self.toggle_api_btn.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; border-radius: 4px; padding: 6px;")
            self.regen_key_btn.setEnabled(False)
            self.regen_key_btn.setStyleSheet("background-color: #555555; color: #aaaaaa; font-weight: bold; border-radius: 4px; padding: 6px;")

    def on_toggle_api(self):
        from PySide6.QtWidgets import QMessageBox
        action_text = "Disable" if self.api_enabled else "Enable"
        confirm = QMessageBox.warning(
            self,
            f"{action_text} API",
            f"Are you sure you want to {action_text.lower()} the local API? This takes effect immediately.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.No:
            return
            
        self.api_enabled = not self.api_enabled
        self.update_api_buttons_ui()
        
        settings = get_app_settings()
        settings.setValue("api_enabled", "true" if self.api_enabled else "false")
        
        if self.parent() and hasattr(self.parent(), "api_manager"):
            if not self.api_enabled:
                self.parent().api_manager.stop_api_server()
                self.parent().chat_view.add_system_message("🔴 Local API Server has been forcefully disabled.")
            else:
                self.parent().api_manager.stop_api_server()
                self.parent().api_manager.start_api_server()
                self.parent().chat_view.add_system_message("🌐 Local API Server started with active key.")

    def on_regen_key(self):
        from PySide6.QtWidgets import QMessageBox
        confirm = QMessageBox.warning(
            self,
            "Regenerate Key",
            "Are you sure you want to regenerate your API Key? This will instantly destroy your old key, drop all active connections, and restart the server.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.No:
            return
            
        new_key = f"llm-local-auth-{uuid.uuid4().hex[:10]}"
        self.api_key_display.setText(new_key)
        
        settings = get_app_settings()
        settings.setValue("local_api_auth_key", new_key)
        
        if self.parent() and hasattr(self.parent(), "api_manager"):
            self.parent().api_manager.stop_api_server()
            self.parent().api_manager.start_api_server()
            self.parent().chat_view.add_system_message("🌐 Local API Server restarted to apply new key.")

    def setup_rerank_ui(self, is_dark: bool):
        """Resolves references to Advanced Retrieval Reranking elements loaded from the UI file, and applies dynamic styling."""
        from PySide6.QtWidgets import QGroupBox, QCheckBox, QComboBox, QLineEdit
        
        self.rerank_group = self.findChild(QGroupBox, "rerank_group")
        self.rerank_enable_cb = self.findChild(QCheckBox, "rerank_enable_cb")
        self.rerank_engine_combo = self.findChild(QComboBox, "rerank_engine_combo")
        self.rerank_endpoint_input = self.findChild(QLineEdit, "rerank_endpoint_input")
        self.rerank_key_input = self.findChild(QLineEdit, "rerank_key_input")
        
        # Premium CSS styling matching the active dialog theme
        if is_dark:
            if self.rerank_group:
                self.rerank_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        color: #ffffff;
                        border: 1px solid #3c3c3c;
                        border-radius: 6px;
                        margin-top: 15px;
                        padding-top: 20px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        subcontrol-position: top left;
                        left: 10px;
                        padding: 0 5px;
                    }
                    QCheckBox { color: #ffffff; font-weight: normal; }
                    QLineEdit, QComboBox {
                        background-color: #2d2d2d; 
                        color: #ffffff; 
                        border: 1px solid #3c3c3c; 
                        border-radius: 5px; 
                        padding: 5px; 
                    }
                    QLineEdit:disabled, QComboBox:disabled {
                        background-color: #1e1e1e;
                        color: #777777;
                        border: 1px solid #252526;
                    }
                """)
        else:
            if self.rerank_group:
                self.rerank_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        color: #333333;
                        border: 1px solid #cccccc;
                        border-radius: 6px;
                        margin-top: 15px;
                        padding-top: 20px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        subcontrol-position: top left;
                        left: 10px;
                        padding: 0 5px;
                    }
                    QCheckBox { color: #333333; font-weight: normal; }
                    QLineEdit, QComboBox {
                        background-color: #f5f5f5; 
                        border: 1px solid #cccccc; 
                        border-radius: 5px; 
                        padding: 5px; 
                    }
                    QLineEdit:disabled, QComboBox:disabled {
                        background-color: #e1e1e1;
                        color: #aaaaaa;
                        border: 1px solid #cccccc;
                    }
                """)
            
        # Scale dialog size to host the new GroupBox without clipping
        self.setMinimumSize(500, 480)
        self.resize(500, 480)
        
        # Connect visual signal reactions
        if self.rerank_enable_cb:
            self.rerank_enable_cb.toggled.connect(self.on_rerank_enabled_toggled)
        if self.rerank_engine_combo:
            self.rerank_engine_combo.currentIndexChanged.connect(self.on_rerank_engine_changed)

    def on_rerank_enabled_toggled(self, checked: bool):
        """Disables or enables reranker input fields dynamically depending on toggle state."""
        self.rerank_engine_combo.setEnabled(checked)
        if checked:
            self.on_rerank_engine_changed(self.rerank_engine_combo.currentIndex())
        else:
            self.rerank_endpoint_input.setEnabled(False)
            self.rerank_key_input.setEnabled(False)

    def on_rerank_engine_changed(self, index: int):
        """Shows/hides custom endpoint and secret key parameters depending on selected model style."""
        if not self.rerank_enable_cb.isChecked():
            return
            
        if index == 0:  # Local Mode
            self.rerank_endpoint_input.setEnabled(False)
            self.rerank_key_input.setEnabled(False)
        elif index == 1:  # Cloud Cohere Mode
            self.rerank_endpoint_input.setEnabled(False)
            self.rerank_key_input.setEnabled(True)
        elif index == 2:  # Custom OpenAPI Mode
            self.rerank_endpoint_input.setEnabled(True)
            self.rerank_key_input.setEnabled(True)
        
    def setup_redis_ui(self, is_dark: bool):
        """Resolves references to Redis Configuration widgets loaded from the UI file, and applies dynamic styling."""
        from PySide6.QtWidgets import QGroupBox, QCheckBox, QLineEdit, QSpinBox
        
        self.redis_group = self.findChild(QGroupBox, "redis_group")
        self.redis_enable_cb = self.findChild(QCheckBox, "redis_enable_cb")
        self.redis_host_input = self.findChild(QLineEdit, "redis_host_input")
        self.redis_port_input = self.findChild(QSpinBox, "redis_port_input")
        self.redis_password_input = self.findChild(QLineEdit, "redis_password_input")
        
        if not (self.redis_enable_cb and self.redis_host_input and self.redis_port_input and self.redis_password_input):
            return
            
        # Premium CSS styling matching the active dialog theme
        if is_dark:
            if self.redis_group:
                self.redis_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        color: #ffffff;
                        border: 1px solid #3c3c3c;
                        border-radius: 6px;
                        margin-top: 15px;
                        padding-top: 20px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        subcontrol-position: top left;
                        left: 10px;
                        padding: 0 5px;
                    }
                    QCheckBox { color: #ffffff; font-weight: normal; }
                    QLineEdit, QSpinBox {
                        background-color: #2d2d2d; 
                        color: #ffffff; 
                        border: 1px solid #3c3c3c; 
                        border-radius: 5px; 
                        padding: 5px; 
                    }
                    QLineEdit:disabled, QSpinBox:disabled {
                        background-color: #1e1e1e;
                        color: #777777;
                        border: 1px solid #252526;
                    }
                """)
        else:
            if self.redis_group:
                self.redis_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        color: #333333;
                        border: 1px solid #cccccc;
                        border-radius: 6px;
                        margin-top: 15px;
                        padding-top: 20px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        subcontrol-position: top left;
                        left: 10px;
                        padding: 0 5px;
                    }
                    QCheckBox { color: #333333; font-weight: normal; }
                    QLineEdit, QSpinBox {
                        background-color: #f5f5f5; 
                        border: 1px solid #cccccc; 
                        border-radius: 5px; 
                        padding: 5px; 
                    }
                    QLineEdit:disabled, QSpinBox:disabled {
                        background-color: #e1e1e1;
                        color: #aaaaaa;
                        border: 1px solid #cccccc;
                    }
                """)
                
        # Connect signals
        self.redis_enable_cb.toggled.connect(self.on_redis_enabled_toggled)

    def on_redis_enabled_toggled(self, checked: bool):
        """Toggles enable states of Redis input widgets."""
        if hasattr(self, "redis_host_input") and self.redis_host_input:
            self.redis_host_input.setEnabled(checked)
        if hasattr(self, "redis_port_input") and self.redis_port_input:
            self.redis_port_input.setEnabled(checked)
        if hasattr(self, "redis_password_input") and self.redis_password_input:
            self.redis_password_input.setEnabled(checked)

    def load_current_settings(self):
        settings = get_app_settings()
        
        use_defaults = settings.value("gen_use_defaults", "false") == "true"
        
        curr_temp = float(settings.value("gen_temperature", 0.7))
        curr_tokens = int(settings.value("gen_max_tokens", 4096))
        
        if self.temp_input:
            self.temp_input.setValue(curr_temp)
        if self.tokens_input:
            self.tokens_input.setValue(curr_tokens)
            
        # Hydrate custom reranking config
        rerank_enabled = str(settings.value("rerank_enabled", "false")).lower() == "true"
        rerank_engine = str(settings.value("rerank_engine", "local")).lower().strip()
        rerank_endpoint = str(settings.value("rerank_endpoint", ""))
        rerank_api_key = str(settings.value("rerank_api_key", ""))
        
        if hasattr(self, "rerank_enable_cb"):
            self.rerank_enable_cb.setChecked(rerank_enabled)
            
            # Match engine index
            engine_idx = 0
            if rerank_engine == "cloud_cohere":
                engine_idx = 1
            elif rerank_engine == "cloud_custom":
                engine_idx = 2
            self.rerank_engine_combo.setCurrentIndex(engine_idx)
            
            self.rerank_endpoint_input.setText(rerank_endpoint)
            self.rerank_key_input.setText(rerank_api_key)
            
            # Fire initial visibility states
            self.on_rerank_enabled_toggled(rerank_enabled)
            
        # Hydrate Redis config
        if hasattr(self, "redis_enable_cb") and self.redis_enable_cb:
            redis_enabled = str(settings.value("redis_enabled", "false")).lower() == "true"
            redis_host = str(settings.value("redis_host", "127.0.0.1"))
            redis_port = int(settings.value("redis_port", 6379))
            redis_password = str(settings.value("redis_password", ""))
            
            self.redis_enable_cb.setChecked(redis_enabled)
            self.redis_host_input.setText(redis_host)
            self.redis_port_input.setValue(redis_port)
            self.redis_password_input.setText(redis_password)
            
            # Fire initial visibility states
            self.on_redis_enabled_toggled(redis_enabled)

        # Hydrate logging config
        if hasattr(self, "log_enable_cb") and self.log_enable_cb:
            log_enabled = str(settings.value("logging/enable_log", "false")).lower() == "true"
            debug_enabled = str(settings.value("logging/enable_debug", "false")).lower() == "true"
            self.log_enable_cb.setChecked(log_enabled)
            self.debug_enable_cb.setChecked(debug_enabled)
        
        if use_defaults:
            if self.preset_combo:
                self.preset_combo.setCurrentIndex(4)
            if self.temp_input:
                self.temp_input.setEnabled(False)
            if self.tokens_input:
                self.tokens_input.setEnabled(False)
            if self.temp_desc:
                self.temp_desc.setText("☁️ Using remote cloud baseline. No overrides active.")
            if self.token_desc:
                self.token_desc.setText("☁️ Using remote cloud baseline. No overrides active.")
        else:
            # Initialize explanations
            self.update_temp_explanation(curr_temp)
            self.update_tokens_explanation(curr_tokens)
        
    def update_temp_explanation(self, val):
        if val <= 0.2:
            desc = "💡 **Precise**: Strictly factual and deterministic. Best for pure computer code and math."
        elif val <= 0.5:
            desc = "⚖️ **Coherent**: Mostly factual with very slight linguistic variety. Good for formal business summaries."
        elif val <= 0.8:
            desc = "🤝 **Balanced**: Standard defaults. Mix of precision and human-like variation. Best all-rounder."
        elif val <= 1.2:
            desc = "🎨 **Creative**: High variance and colorful vocabulary. Best for fiction, storytelling, and brainstorming."
        else:
            desc = "🔥 **Experimental**: Total chaos. Highly random and unpredictable. Useful for avant-garde conceptual generation."
        
        self.temp_desc.setText(desc)
        
        # Reset to "Custom" preset if inputs were touched manually
        if self.sender() == self.temp_input:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0) # Set back to "Custom"
            self.preset_combo.blockSignals(False)

    def update_tokens_explanation(self, val):
        desc = f"📏 Sets the ceiling for response length. Selected capacity provides about ~{int(val * 0.75)} English words max."
        self.token_desc.setText(desc)
        
        if self.sender() == self.tokens_input:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0) # "Custom"
            self.preset_combo.blockSignals(False)

    def on_preset_changed(self, index):
        # Block infinite loop feedback
        self.temp_input.blockSignals(True)
        self.tokens_input.blockSignals(True)
        
        if index == 1: # Precise
            self.temp_input.setEnabled(True)
            self.tokens_input.setEnabled(True)
            self.temp_input.setValue(0.1)
            self.tokens_input.setValue(4096)
        elif index == 2: # Balanced
            self.temp_input.setEnabled(True)
            self.tokens_input.setEnabled(True)
            self.temp_input.setValue(0.7)
            self.tokens_input.setValue(4096)
        elif index == 3: # Creative
            self.temp_input.setEnabled(True)
            self.tokens_input.setEnabled(True)
            self.temp_input.setValue(1.0)
            self.tokens_input.setValue(8192)
        elif index == 4: # Model Default (None)
            self.temp_input.setEnabled(False)
            self.tokens_input.setEnabled(False)
            self.temp_desc.setStyleSheet("color: #aaaaaa; font-style: italic; font-weight: bold;")
            self.temp_desc.setText("☁️ Using remote cloud baseline. Temperature is NOT hardcoded.")
            self.token_desc.setText("☁️ Using remote cloud baseline. Max tokens are NOT hardcoded.")
            self.temp_input.blockSignals(False)
            self.tokens_input.blockSignals(False)
            return # Skip general updates
        else: # Custom/Fallback
            self.temp_input.setEnabled(True)
            self.tokens_input.setEnabled(True)
            self.temp_desc.setStyleSheet("color: #aaaaaa; font-style: italic;")
            
        self.temp_input.blockSignals(False)
        self.tokens_input.blockSignals(False)
        
        # Force description updates
        self.update_temp_explanation(self.temp_input.value())
        self.update_tokens_explanation(self.tokens_input.value())

    def save_and_close(self):
        settings = get_app_settings()
        is_default_mode = self.preset_combo.currentIndex() == 4 if self.preset_combo else False
        
        settings.setValue("gen_use_defaults", "true" if is_default_mode else "false")
        if self.temp_input:
            settings.setValue("gen_temperature", self.temp_input.value())
        if self.tokens_input:
            settings.setValue("gen_max_tokens", self.tokens_input.value())
            
        # Commit custom reranking changes
        if hasattr(self, "rerank_enable_cb"):
            settings.setValue("rerank_enabled", "true" if self.rerank_enable_cb.isChecked() else "false")
            
            engine_map = {0: "local", 1: "cloud_cohere", 2: "cloud_custom"}
            idx = self.rerank_engine_combo.currentIndex()
            settings.setValue("rerank_engine", engine_map.get(idx, "local"))
            
            settings.setValue("rerank_endpoint", self.rerank_endpoint_input.text().strip())
            settings.setValue("rerank_api_key", self.rerank_key_input.text().strip())
            
        # Commit logging changes
        if hasattr(self, "log_enable_cb") and self.log_enable_cb:
            settings.setValue("logging/enable_log", "true" if self.log_enable_cb.isChecked() else "false")
            settings.setValue("logging/enable_debug", "true" if self.debug_enable_cb.isChecked() else "false")
            try:
                from server.utils.logger import AppLogger
                AppLogger.get_instance().reconfigure()
            except ImportError:
                pass
            
        # Commit Redis changes
        if hasattr(self, "redis_enable_cb") and self.redis_enable_cb:
            settings.setValue("redis_enabled", "true" if self.redis_enable_cb.isChecked() else "false")
            settings.setValue("redis_host", self.redis_host_input.text().strip())
            settings.setValue("redis_port", self.redis_port_input.value())
            settings.setValue("redis_password", self.redis_password_input.text().strip())
            
            # Dynamically apply config to active Redis & Event Bus services
            try:
                from server.logic.services.base_service import ServiceRegistry
                redis_svc = ServiceRegistry.get("redis")
                event_bus_svc = ServiceRegistry.get("event_bus")
                
                # Graceful shutdown followed by re-initialization with new parameters
                event_bus_svc.shutdown()
                redis_svc.shutdown()
                
                redis_svc.initialize()
                event_bus_svc.initialize()
                
                # Feedback notice on the chat view if parent exists
                if self.parent() and hasattr(self.parent(), "chat_view"):
                    state_msg = "🟢 Redis central connection established." if redis_svc.is_live() else "🟡 Redis operating in offline-mock fallback."
                    self.parent().chat_view.add_system_message(f"⚙️ Redis settings updated. {state_msg}")
            except Exception as e:
                import logging
                logging.getLogger("QuantumRedisUI").error(f"Failed to dynamically apply new Redis configuration: {str(e)}")
            
        self.accept()
