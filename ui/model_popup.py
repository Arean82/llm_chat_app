import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QDialog, QCheckBox, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor

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
        ui_file = Path(__file__).parent.parent / "ui_designer" / "model_popup.ui"
        self.ui = loader.load(str(ui_file), self)

        # --- BLANK WINDOW FIX ---
        # Take the layout from the loaded UI and apply it to this Dialog
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())
        # -------------------------

        self.setup_table()
        self.populate_models()
        
        # Wire buttons
        self.ui.apply_btn.clicked.connect(self.on_apply)
        # Cancel is already wired in the .ui file to reject()

    def setup_table(self):
        table = self.ui.model_table
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
        # Read models.json
        models_file = Path(__file__).parent.parent / "resources" / "models.json"
        if not models_file.exists():
            return
            
        import json
        with open(models_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.models_data = data.get("models", [])
        self.ui.model_table.setRowCount(len(self.models_data))
        
        for row, model in enumerate(self.models_data):
            # Col 0: Checkbox
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox { margin-left: 20px; }")
            # Store row index in checkbox to know which one was clicked
            checkbox.setProperty("row", row)
            checkbox.stateChanged.connect(self.on_checkbox_toggled)
            self.ui.model_table.setCellWidget(row, 0, checkbox)
            
            # Col 1: Model Name (Need a dummy QTableWidgetItem to allow selection)
            name_item = QTableWidgetItem(model['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.model_table.setItem(row, 1, name_item)
            
            # Col 2: Description
            desc_item = QTableWidgetItem(model['description'])
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.model_table.setItem(row, 2, desc_item)
            
            # Check if this is the currently active model
            if model['id'] == self.current_model_id:
                self.set_row_active(row, True)

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
        # Handle Checkbox (block signals so we don't trigger an infinite loop)
        cb = self.ui.model_table.cellWidget(row, 0)
        cb.blockSignals(True)
        cb.setChecked(is_active)
        cb.blockSignals(False)
        
        # Handle Row Color
        color = QColor("#1a3d36") if is_active else QColor("transparent") # Dark Teal
        text_color = QColor("#4caf50") if is_active else QColor("#d4d4d4") # Green text vs normal text
        
        for col in range(3):
            item = self.ui.model_table.item(row, col)
            if item:
                item.setBackground(color)
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