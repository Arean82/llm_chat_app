# ui/model_popup.py
# This module defines a reusable dialog for selecting the active model from a list defined in models.json. It displays the model name and description, and allows the user to select one as active. The selection is saved to QSettings for persistence. 


import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QDialog, QCheckBox, QHBoxLayout, QTableWidgetItem, QAbstractItemView, QWidget
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor

from utils.path_utils import get_resource_path, get_app_settings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtUiTools import QUiLoader

class ModelPopupClass(QDialog):
    def __init__(self, current_model_id=None, parent=None, force_show_all=False):
        super().__init__(parent)
        
        self.current_model_id = current_model_id
        self.force_show_all = force_show_all
        self.models_data = [] # Will store the raw dicts from models.json
        self.selected_model_id = None
        
        # Load UI
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/model_popup.ui")
        self.ui = loader.load(str(ui_file), self)

        # --- BLANK WINDOW FIX ---
        # Take the layout from the loaded UI and apply it to this Dialog
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())

        self.setMinimumSize(900, 650)
        self.setup_table()
        
        # Link the UI-defined checkbox and capability filter combobox to the refresh logic
        self.ui.show_all_cb.stateChanged.connect(self.populate_models)
        self.ui.capability_filter.currentIndexChanged.connect(self.populate_models)
        
        if self.force_show_all:
            self.ui.show_all_cb.setChecked(True)
            self.ui.show_all_cb.setEnabled(False)
        
        self.populate_models()
        
        # Wire buttons
        self.ui.apply_btn.clicked.connect(self.on_apply)
        self.ui.cancel_btn.clicked.connect(self.reject)
        # Cancel is already wired in the .ui file to reject()

    def setup_table(self):
        table = self.ui.model_table
        
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setWordWrap(True) # Enable word wrap for long descriptions
        
        from PySide6.QtWidgets import QHeaderView
        header = table.horizontalHeader()
        
        # Define specific behaviors for columns
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 60) # Active checkbox
        
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Ecosystem
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Developer
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Model Name
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # Description Stretch
        
        # Ensure row heights expand for wrapped text
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def populate_models(self):
        from logic.model_io import load_all_models
        import keyring
        try:
            all_models = load_all_models()
            active_p = get_app_settings().value("active_provider_id", "nvidia")
            show_all = self.ui.show_all_cb.isChecked()
            
            # Universal Key Check: Only show models if an API key exists for that provider
            connected_models = []
            for m in all_models:
                prov = m.get('provider', 'nvidia').lower()
                has_key = False
                
                if prov == "nvidia":
                    has_key = bool(keyring.get_password("LLMChatApp", "api_key_nvidia") or 
                                   keyring.get_password("LLMChatApp", "api_key"))
                elif prov == "google":
                    has_key = bool(keyring.get_password("LLMChatApp", "api_key_google"))
                else:
                    # Generic check for custom providers (Credential Manager format)
                    has_key = bool(keyring.get_password("LLMChatApp", f"api_key_openai_{prov}"))
                
                if has_key:
                    connected_models.append(m)
            
            # Final filtering based on Ecosystem and 'Show All' toggle (strictly show chat models only)
            self.models_data = [
                m for m in connected_models 
                if (show_all or m.get('provider', 'nvidia') == active_p) and m.get('type', 'chat') == 'chat'
            ]

            # Dynamic capability filtering
            filter_idx = self.ui.capability_filter.currentIndex()
            if filter_idx > 0:
                from utils.model_config import does_model_support_tools
                filtered_by_cap = []
                for m in self.models_data:
                    m_id = m.get("id", "")
                    m_desc = m.get("description", "").lower()
                    m_id_lower = m_id.lower()
                    
                    supports_tools = does_model_support_tools(m_id)
                    is_vision = "vision" in m_id_lower or "-vl" in m_id_lower or "vision" in m_desc or "multimodal" in m_desc
                    
                    if filter_idx == 1: # General Chat
                        if not is_vision:
                            filtered_by_cap.append(m)
                    elif filter_idx == 2: # Supports Tools
                        if supports_tools:
                            filtered_by_cap.append(m)
                    elif filter_idx == 3: # Multimodal / Vision
                        if is_vision:
                            filtered_by_cap.append(m)
                self.models_data = filtered_by_cap
        except Exception as e:
            print(f"Error fetching models for popup: {e}")
            self.models_data = []
            
        table = self.ui.model_table
        table.setRowCount(len(self.models_data))
        
        for row, model in enumerate(self.models_data):
            # Col 0: CENTERED CHECKBOX
            container = QWidget()
            cb_layout = QHBoxLayout(container)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            checkbox = QCheckBox()
            checkbox.setProperty("row", row)
            checkbox.stateChanged.connect(self.on_checkbox_toggled)
            cb_layout.addWidget(checkbox)
            table.setCellWidget(row, 0, container)

            # Dummy item for background color
            dummy_item = QTableWidgetItem()
            dummy_item.setFlags(dummy_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, dummy_item)
            
            # Col 1: Ecosystem (Provider)
            prov = model.get('provider', 'nvidia').upper()
            prov_item = QTableWidgetItem(prov)
            prov_item.setFlags(prov_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, prov_item)
            
            # Col 2: Developer
            dev = model.get('developer', 'Unknown')
            dev_item = QTableWidgetItem(dev)
            dev_item.setFlags(dev_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 2, dev_item)
                        
            # Col 3: Model Name
            from utils.model_config import does_model_support_tools
            supports_tools = does_model_support_tools(model.get('id'))
            name_suffix = " 🛠️" if supports_tools else ""
            name_item = QTableWidgetItem(model.get('name', 'Unnamed') + name_suffix)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 3, name_item)
            
            # Col 4: Description
            desc_item = QTableWidgetItem(model.get('description', ''))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 4, desc_item)
            
            if model['id'] == self.current_model_id:
                self.set_row_active(row, True)
            else:
                self.set_row_active(row, False)

    def on_checkbox_toggled(self, state):
        # Get the row from the checkbox property
        checkbox = self.sender()
        row = checkbox.property("row")
        
        if state == Qt.CheckState.Checked.value:
            # Uncheck and decolor ALL other rows first
            for r in range(self.ui.model_table.rowCount()):
                if r != row:
                    self.set_row_active(r, False)
            
            # Activate the clicked row
            self.set_row_active(row, True)
            self.selected_model_id = self.models_data[row]['id']
        else:
            # If they uncheck the active one, just deactivate it
            self.set_row_active(row, False)
            self.selected_model_id = None

    def set_row_active(self, row, is_active):
        # Find checkbox inside the new container widget
        container = self.ui.model_table.cellWidget(row, 0)
        if container:
            cb = container.findChild(QCheckBox)
            if cb:
                cb.blockSignals(True)
                cb.setChecked(is_active)
                cb.blockSignals(False)
        
        # LIGHT THEME COLORS
        if is_active:
            bg_color = QColor("#E3F2FD")  # Light blue
            text_color = QColor("#0D47A1") # Dark blue text
        else:
            bg_color = QColor("#FFFFFF")  # White
            text_color = QColor("#333333") # Dark gray text
        
        # Apply to all 5 columns
        for col in range(5):
            item = self.ui.model_table.item(row, col)
            if item:
                item.setBackground(bg_color)
                item.setForeground(text_color)

    def on_apply(self):
        if self.selected_model_id:
            # Save to QSettings
            settings = get_app_settings()
            settings.setValue("current_model_id", self.selected_model_id)
            self.accept() # Close dialog with success
        else:
            # Optional: Warn them they didn't select anything
            pass 

    def get_selected_model_id(self):
        return self.selected_model_id
