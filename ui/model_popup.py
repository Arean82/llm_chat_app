# ui/model_popup.py
# This module defines a reusable dialog for selecting the active model from a list defined in models.json. It displays the model name and description, and allows the user to select one as active. The selection is saved to QSettings for persistence. 


import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QDialog, QCheckBox, QHBoxLayout, QTableWidgetItem, QAbstractItemView, QWidget
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor

from utils.path_utils import get_resource_path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtUiTools import QUiLoader

class ModelPopupClass(QDialog):
    def __init__(self, current_model_id=None, parent=None):
        super().__init__(parent)
        
        self.current_model_id = current_model_id
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

        # Set proper title and size
        self.setWindowTitle("Select Model")
        self.setMinimumSize(550, 450)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.setup_table()
        self.populate_models()
        
        # Wire buttons
        self.ui.apply_btn.clicked.connect(self.on_apply)
        self.ui.cancel_btn.clicked.connect(self.reject)
        # Cancel is already wired in the .ui file to reject()

    def setup_table(self):
        table = self.ui.model_table

        # Clear .ui file defaults first so the 3 columns apply correctly
        table.clear()

        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Active", "Model Name", "Description"])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        
        # Set column widths
        table.setColumnWidth(0, 60)  # Checkbox column
        table.setColumnWidth(1, 180) # Name column
        table.horizontalHeader().setStretchLastSection(True) # Description fills rest

    def populate_models(self):
        from logic.model_io import load_all_models
        try:
            self.models_data = load_all_models()
        except Exception as e:
            print(f"Error fetching models for popup: {e}")
            self.models_data = []
        self.ui.model_table.setRowCount(len(self.models_data))
        
        for row, model in enumerate(self.models_data):
            # Col 0: CENTERED CHECKBOX ---
            container = QWidget()
            cb_layout = QHBoxLayout(container)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Centers it perfectly
            cb_layout.setContentsMargins(0, 0, 0, 0) # Removes extra spacing

            checkbox = QCheckBox()
            checkbox.setProperty("row", row)
            checkbox.stateChanged.connect(self.on_checkbox_toggled)
            cb_layout.addWidget(checkbox)

            self.ui.model_table.setCellWidget(row, 0, container)

            # Dummy item for background color
            dummy_item = QTableWidgetItem()
            dummy_item.setFlags(dummy_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.model_table.setItem(row, 0, dummy_item)
                        
            # Col 1: Model Name
            name_item = QTableWidgetItem(model['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.model_table.setItem(row, 1, name_item)
            
            # Col 2: Description
            desc_item = QTableWidgetItem(model['description'])
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.model_table.setItem(row, 2, desc_item)
            
            # MUST be at the very end so the items actually exist in the table
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
        
        # Apply to all 3 columns
        for col in range(3):
            item = self.ui.model_table.item(row, col)
            if item:
                item.setBackground(bg_color)
                item.setForeground(text_color)

    def on_apply(self):
        if self.selected_model_id:
            # Save to QSettings
            settings = QSettings("LLMChatApp", "Settings")
            settings.setValue("current_model_id", self.selected_model_id)
            self.accept() # Close dialog with success
        else:
            # Optional: Warn them they didn't select anything
            pass 

    def get_selected_model_id(self):
        return self.selected_model_id