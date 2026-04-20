# ui/system_prompt_manager.py

# ui/system_prompt_manager.py

import json
from pathlib import Path

from PySide6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QTableWidgetItem, QHeaderView, QLabel, QTextEdit, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader

# Import utility from main to get path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.path_utils import get_resource_path

class InstructionEditorDialog(QDialog):
    """Mini dialog to edit Name and Text of an instruction"""
    def __init__(self, name="", text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Instruction")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)

        # Name Input
        layout.addWidget(QLabel("Instruction Name:"))
        from PySide6.QtWidgets import QLineEdit
        self.name_input = QLineEdit()
        self.name_input.setText(name)
        layout.addWidget(self.name_input)

        # Text Input
        layout.addWidget(QLabel("Instruction Text:"))
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter the detailed instructions here...")
        self.text_input.setPlainText(text)
        layout.addWidget(self.text_input)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.name_input.text().strip(), self.text_input.toPlainText().strip()

class SystemPromptManagerClass(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/system_prompt_manager.ui")
        print(f"DEBUG: Trying to load UI from: {str(ui_file)}")
        self.ui = loader.load(str(ui_file), self)
        if self.ui is None:
            QMessageBox.critical(self, "UI Error", f"Failed to load UI file from:\n{str(ui_file)}\n\nMake sure the file exists in the ui_designer folder.")
            return

        # Set the main layout from the loaded UI
        # The UI file already has a layout, so we just need to set it as the dialog's layout
        if self.ui.layout():
            self.setLayout(self.ui.layout())
        
        self.table_widget = self.ui.table_widget
        self.setup_connections_and_style()  # Renamed to avoid confusion

        # Data storage
        self.instructions = [] 
        self.load_data_from_settings()
        self.refresh_table()

    def setup_connections_and_style(self):
        """Setup table styling and button connections (without creating a new layout)"""
        self.setWindowTitle(self.ui.windowTitle())
        
        # Setup table columns
        self.table_widget.setColumnWidth(0, 60)  # Width for checkbox
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        # Connect buttons
        self.ui.btn_add.clicked.connect(self.add_instruction)
        self.ui.btn_edit.clicked.connect(self.edit_instruction)
        self.ui.btn_delete.clicked.connect(self.delete_instruction)
        self.ui.btn_close.clicked.connect(self.accept)
        
        # Connect table item changed (for checkboxes)
        self.table_widget.itemChanged.connect(self.on_item_changed)

    def load_data_from_settings(self):
        from PySide6.QtCore import QSettings
        settings = QSettings("LLMChatApp", "Settings")
        json_data = settings.value("system_prompt_library", "")
        
        if json_data:
            try:
                self.instructions = json.loads(json_data)
            except json.JSONDecodeError:
                self.instructions = []
        else:
            # Default instruction if none exist
            self.instructions = [
                {
                    "id": 1,
                    "name": "General Assistant",
                    "text": "You are a helpful, intelligent AI assistant.",
                    "checked": True
                }
            ]

    def save_data_to_settings(self):
        from PySide6.QtCore import QSettings
        settings = QSettings("LLMChatApp", "Settings")
        json_data = json.dumps(self.instructions)
        settings.setValue("system_prompt_library", json_data)

    def refresh_table(self):
        self.table_widget.setRowCount(0)
        self.table_widget.blockSignals(True)  # Prevent triggering itemChanged while filling

        for instr in self.instructions:
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)

            # Checkbox (Column 0)
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked if instr.get('checked', False) else Qt.Unchecked)
            self.table_widget.setItem(row, 0, check_item)

            # Name (Column 1)
            name_item = QTableWidgetItem(instr['name'])
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)  # Make name read-only in table
            self.table_widget.setItem(row, 1, name_item)

        self.table_widget.blockSignals(False)

    def get_selected_instruction(self):
        row = self.table_widget.currentRow()
        if row < 0:
            return None
        # Use index to get from list because table order might be sorted or filtered in future
        # But here table order matches list order for simplicity
        return self.instructions[row]

    def add_instruction(self):
        dialog = InstructionEditorDialog(parent=self)
        if dialog.exec():
            name, text = dialog.get_data()
            if not name or not text:
                QMessageBox.warning(self, "Error", "Name and Text cannot be empty.")
                return
            
            new_id = max([i['id'] for i in self.instructions], default=0) + 1
            self.instructions.append({
                "id": new_id,
                "name": name,
                "text": text,
                "checked": False
            })
            self.refresh_table()
            self.save_data_to_settings()

    def edit_instruction(self):
        instr = self.get_selected_instruction()
        if not instr:
            QMessageBox.information(self, "No Selection", "Please select an instruction to edit.")
            return

        dialog = InstructionEditorDialog(instr['name'], instr['text'], self)
        if dialog.exec():
            new_name, new_text = dialog.get_data()
            if not new_name or not new_text:
                return
            
            instr['name'] = new_name
            instr['text'] = new_text
            self.refresh_table()
            self.save_data_to_settings()

    def delete_instruction(self):
        instr = self.get_selected_instruction()
        if not instr:
            QMessageBox.information(self, "No Selection", "Please select an instruction to delete.")
            return

        reply = QMessageBox.question(self, "Delete", "Are you sure you want to delete this instruction?", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.instructions.remove(instr)
            self.refresh_table()
            self.save_data_to_settings()

    def on_item_changed(self, item):
        row = item.row()
        col = item.column()
        
        if col == 0 and row < len(self.instructions):
            # Update underlying data model
            is_checked = (item.checkState() == Qt.Checked)
            self.instructions[row]['checked'] = is_checked
            self.save_data_to_settings()
            