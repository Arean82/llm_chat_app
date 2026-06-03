# ui/model_popup.py
# This module defines a reusable dialog for selecting the active model from a list defined in models.json. It displays the model name and description, and allows the user to select one as active. The selection is saved to QSettings for persistence. 


import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QDialog, QCheckBox, QHBoxLayout, QTableWidgetItem, QAbstractItemView, QWidget
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor

from server.utils.path_utils import get_resource_path, get_app_settings
from server.utils.helpers import strip_markdown
from desktop.ui.shared_widgets import set_app_icon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtUiTools import QUiLoader

class ModelPopupClass(QDialog):
    def __init__(self, current_model_id=None, parent=None, force_show_all=False):
        super().__init__(parent)
        set_app_icon(self)
        
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
        
        # Restore Geometry
        settings = get_app_settings()
        geom = settings.value("geometry_model_popup")
        if geom:
            self.restoreGeometry(geom)

    def closeEvent(self, event):
        settings = get_app_settings()
        settings.setValue("geometry_model_popup", self.saveGeometry())
        super().closeEvent(event)

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
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Capabilities
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)          # Description Stretch
        
        # Ensure row heights expand for wrapped text
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def populate_models(self):
        from server.logic.model_io import load_all_models, load_provider_metadata
        import keyring
        import json
        try:
            all_models = load_all_models()
            active_p = get_app_settings().value("active_provider_id", "nvidia")
            show_all = self.ui.show_all_cb.isChecked()
            
            metadata = load_provider_metadata()
            base_providers = {p.get("id"): p for p in metadata.get("providers", [])}
            
            def normalize(p):
                return str(p).lower().replace(" ", "").replace("_", "").replace("-", "")

            def check_has_key(provider):
                p_id = normalize(provider)
                
                mapped_id = p_id
                for base_id, base_p in base_providers.items():
                    if normalize(base_p.get("display_name", "")) == p_id or normalize(base_id) == p_id:
                        mapped_id = base_id
                        break
                        
                if mapped_id in base_providers:
                    if keyring.get_password("LLMChatApp", f"api_key_{mapped_id}"):
                        return True
                    if mapped_id == "nvidia" and keyring.get_password("LLMChatApp", "api_key"):
                        return True
                        
                custom = json.loads(get_app_settings().value("custom_providers", "[]"))
                for cp in custom:
                    if normalize(cp['ecosystem']) == p_id:
                        eco_key = cp['ecosystem'].lower().replace(' ', '_')
                        return bool(keyring.get_password("LLMChatApp", f"api_key_{cp['sdk']}_{eco_key}"))
                return False

            connected_models = [m for m in all_models if check_has_key(m.get('provider', 'nvidia'))]
            
            # Final filtering based on Ecosystem and 'Show All' toggle (strictly show chat models only)
            self.models_data = [
                m for m in connected_models 
                if (show_all or normalize(m.get('provider', 'nvidia')) == normalize(active_p)) and m.get('type', 'chat') == 'chat'
            ]

            # Dynamic capability filtering
            filter_idx = self.ui.capability_filter.currentIndex()
            if filter_idx > 0:
                filtered_by_cap = []
                for m in self.models_data:
                    m_id = m.get("id", "")
                    m_desc = m.get("description", "").lower()
                    m_id_lower = m_id.lower()
                    
                    has_vision = m.get("vision", False) or "vision" in m_id_lower or "-vl" in m_id_lower or "vision" in m_desc or "multimodal" in m_desc or "pixtral" in m_id_lower or "gemini" in m_id_lower
                    has_audio = m.get("audio", False) or any(k in m_id_lower for k in ["audio", "voice", "canary", "stt", "tts"]) or "gemini" in m_id_lower
                    has_video = m.get("video", False) or "video" in m_id_lower or "gemini-1.5" in m_id_lower or "gemini-2.0" in m_id_lower or "gemini-exp" in m_id_lower
                    has_coding = m.get("coding", False) or any(k in m_id_lower for k in ["code", "coder", "codellama"]) or "gemini" in m_id_lower or "gpt-4" in m_id_lower
                    
                    if filter_idx == 1: # General Chat
                        if not has_vision and not has_audio and not has_video:
                            filtered_by_cap.append(m)
                    elif filter_idx == 2: # Supports Tools
                        from server.utils.model_config import does_model_support_tools
                        if does_model_support_tools(m_id):
                            filtered_by_cap.append(m)
                    elif filter_idx == 3: # Multimodal / Vision
                        if has_vision:
                            filtered_by_cap.append(m)
                    elif filter_idx == 4: # Audio / Voice
                        if has_audio:
                            filtered_by_cap.append(m)
                    elif filter_idx == 5: # Video / Media
                        if has_video:
                            filtered_by_cap.append(m)
                    elif filter_idx == 6: # Coding / Software
                        if has_coding:
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
            from server.utils.model_config import does_model_support_tools
            supports_tools = does_model_support_tools(model.get('id'))
            name_suffix = " 🛠️" if supports_tools else ""
            name_item = QTableWidgetItem(model.get('name', 'Unnamed') + name_suffix)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 3, name_item)

            # Col 4: Capabilities
            caps = []
            m_id_lower = model.get("id", "").lower()
            m_desc_lower = model.get("description", "").lower()
            if model.get("vision", False) or "vision" in m_id_lower or "-vl" in m_id_lower or "vision" in m_desc_lower or "multimodal" in m_desc_lower or "pixtral" in m_id_lower or "gemini" in m_id_lower:
                caps.append("👁️ Vision")
            if model.get("audio", False) or any(k in m_id_lower for k in ["audio", "voice", "canary", "stt", "tts"]) or "gemini" in m_id_lower:
                caps.append("🎙️ Audio")
            if model.get("video", False) or "video" in m_id_lower or "gemini-1.5" in m_id_lower or "gemini-2.0" in m_id_lower or "gemini-exp" in m_id_lower:
                caps.append("🎥 Video")
            if model.get("coding", False) or any(k in m_id_lower for k in ["code", "coder", "codellama"]) or "gemini" in m_id_lower or "gpt-4" in m_id_lower:
                caps.append("💻 Coding")
            
            caps_str = ", ".join(caps) if caps else "💬 Chat"
            caps_item = QTableWidgetItem(caps_str)
            caps_item.setFlags(caps_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 4, caps_item)
            
            # Col 5: Description
            desc_item = QTableWidgetItem(strip_markdown(model.get('description', '')))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 5, desc_item)
            
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
        
        # Apply to all 6 columns
        for col in range(6):
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
