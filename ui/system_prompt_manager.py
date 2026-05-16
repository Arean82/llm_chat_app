# ui/system_prompt_manager.py
import json
from pathlib import Path
from ui.shared_widgets import set_app_icon

from PySide6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QTableWidgetItem, QHeaderView, QLabel, QTextEdit, QPushButton, QVBoxLayout, QLineEdit
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

        # SET ICON
        set_app_icon(self)
                
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/system_prompt_manager.ui")
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
        
        # UI ENHANCEMENTS
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search instructions...")
        self.search_input.textChanged.connect(self.refresh_table)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Select an instruction to preview its content...")
        self.preview_text.setMaximumHeight(100)
        
        # Inject into existing layout
        main_layout = self.layout()
        main_layout.insertWidget(2, self.search_input) # Below info label
        main_layout.insertWidget(4, QLabel("<b>Preview:</b>"))
        main_layout.insertWidget(5, self.preview_text)
        
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
        
        # Connect table selection for preview
        self.table_widget.itemSelectionChanged.connect(self.update_preview)
        
        # Connect table item changed (for checkboxes)
        self.table_widget.itemChanged.connect(self.on_item_changed)

    def load_data_from_settings(self):
        """Loads instructions from resources/user_prompts.json"""
        file_path = get_resource_path("resources/user_prompts.json")
        
        # Check if the file exists
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.instructions = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading prompts: {e}")
                self.instructions = []
        else:
            # File doesn't exist, create default list
            self.instructions = [
                {
                    "id": 1,
                    "name": "General Assistant",
                    "text": "You are a helpful, intelligent AI assistant.",
                    "checked": True
                }
            ]
            # Save default list so file gets created
            self.save_data_to_settings()

    def save_data_to_settings(self):
        """Saves instructions to resources/user_prompts.json"""
        file_path = get_resource_path("resources/user_prompts.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # indent=4 makes the file human-readable
                json.dump(self.instructions, f, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "Save Error", f"Could not save prompts to:\n{file_path}\n\nError: {e}")

    def refresh_table(self):
        self.table_widget.setRowCount(0)
        self.table_widget.blockSignals(True)  
        
        search_term = self.search_input.text().lower()

        for instr in self.instructions:
            if search_term and search_term not in instr['name'].lower():
                continue
                
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)

            # Checkbox (Column 0)
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked if instr.get('checked', False) else Qt.Unchecked)
            check_item.setData(Qt.UserRole, instr['id']) # Store ID for lookups
            self.table_widget.setItem(row, 0, check_item)

            # Name (Column 1)
            name_item = QTableWidgetItem(instr['name'])
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table_widget.setItem(row, 1, name_item)

        self.table_widget.blockSignals(False)
        self.update_preview()

    def update_preview(self):
        """Updates the preview area with the currently selected instruction's text."""
        instr = self.get_selected_instruction()
        if instr:
            self.preview_text.setPlainText(instr['text'])
        else:
            self.preview_text.clear()

    def get_selected_instruction(self):
        row = self.table_widget.currentRow()
        if row < 0:
            return None
            
        # Get ID from hidden data to handle filtered view
        item = self.table_widget.item(row, 0)
        instr_id = item.data(Qt.UserRole)
        
        return next((i for i in self.instructions if i['id'] == instr_id), None)

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
        
        if col == 0:
            # Get ID from hidden data
            instr_id = item.data(Qt.UserRole)
            instr = next((i for i in self.instructions if i['id'] == instr_id), None)
            
            if instr:
                is_checked = (item.checkState() == Qt.Checked)
                instr['checked'] = is_checked
                self.save_data_to_settings()
            