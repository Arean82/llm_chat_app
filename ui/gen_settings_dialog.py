# ui/gen_settings_dialog.py
import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QDoubleSpinBox, QSpinBox, QComboBox, QLabel, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QSettings, Qt
from PySide6.QtGui import QIcon

from utils.path_utils import get_resource_path
from utils.helpers import set_app_icon

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
        settings = QSettings("LLMChatApp", "Settings")
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
        
        # Load the UI container
        self.ui = loader.load(str(ui_file_path))
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.ui)
        layout.setContentsMargins(0,0,0,0)
        
        # Bind references
        self.preset_combo = self.ui.findChild(QComboBox, "preset_combo")
        self.temp_input = self.ui.findChild(QDoubleSpinBox, "temp_input")
        self.tokens_input = self.ui.findChild(QSpinBox, "tokens_input")
        self.temp_desc = self.ui.findChild(QLabel, "temp_desc")
        self.token_desc = self.ui.findChild(QLabel, "token_desc")
        self.save_btn = self.ui.findChild(QPushButton, "save_btn")
        self.cancel_btn = self.ui.findChild(QPushButton, "cancel_btn")
        
        # Signal bindings
        self.temp_input.valueChanged.connect(self.update_temp_explanation)
        self.tokens_input.valueChanged.connect(self.update_tokens_explanation)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        self.save_btn.clicked.connect(self.save_and_close)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.load_current_settings()
        
    def load_current_settings(self):
        settings = QSettings("LLMChatApp", "Settings")
        
        use_defaults = settings.value("gen_use_defaults", "false") == "true"
        
        curr_temp = float(settings.value("gen_temperature", 0.7))
        curr_tokens = int(settings.value("gen_max_tokens", 4096))
        
        self.temp_input.setValue(curr_temp)
        self.tokens_input.setValue(curr_tokens)
        
        if use_defaults:
            self.preset_combo.setCurrentIndex(4)
            self.temp_input.setEnabled(False)
            self.tokens_input.setEnabled(False)
            self.temp_desc.setText("☁️ Using remote cloud baseline. No overrides active.")
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
        settings = QSettings("LLMChatApp", "Settings")
        is_default_mode = self.preset_combo.currentIndex() == 4
        
        settings.setValue("gen_use_defaults", "true" if is_default_mode else "false")
        settings.setValue("gen_temperature", self.temp_input.value())
        settings.setValue("gen_max_tokens", self.tokens_input.value())
        self.accept()
