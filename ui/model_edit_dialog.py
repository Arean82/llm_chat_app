# ui/model_edit_dialog.py
# This dialog is used for both adding new models and editing existing ones. It has fields for model ID, display name, description, and a checkbox for whether the model is free or not. The dialog validates that the ID and name are provided before accepting. It also applies theming based on the current theme (dark or light) for a consistent look with the rest of the application. The get_model_data() method can be called after acceptance to retrieve the entered data as a dictionary.

import json
from PySide6.QtWidgets import (
    QDialog, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtUiTools import QUiLoader

from utils.path_utils import get_resource_path

class ModelEditDialog(QDialog):
    """Dialog for adding or editing a single model."""

    def __init__(self, model_data=None, theme="dark", parent=None):
        super().__init__(parent)
        self.model_data = model_data or {}
        self.is_edit_mode = bool(model_data)
        self.theme = theme

        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/model_edit_dialog.ui")

        # BLANK WINDOW FIX: pass self as parent
        self.ui = loader.load(str(ui_file), self)
        if self.ui and self.ui.layout():
            self.setLayout(self.ui.layout())

        self.setFixedSize(520, 300)

        # Widget references
        self.title_label = self.findChild(object, "dialogTitle")
        self.id_input = self.findChild(object, "id_input")
        self.name_input = self.findChild(object, "name_input")
        self.desc_input = self.findChild(object, "desc_input")
        self.free_checkbox = self.findChild(object, "free_checkbox")
        self.button_box = self.findChild(object, "buttonBox")

        # Set title
        if self.is_edit_mode:
            self.setWindowTitle("Edit Model")
            self.title_label.setText("✏️ Edit Model")
        else:
            self.setWindowTitle("Add New Model")
            self.title_label.setText("➕ Add New Model")

        self.populate_fields()
        self.apply_theme()

        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)

    def populate_fields(self):
        if self.model_data:
            self.id_input.setText(self.model_data.get("id", ""))
            self.name_input.setText(self.model_data.get("name", ""))
            self.desc_input.setText(self.model_data.get("description", ""))
            self.free_checkbox.setChecked(self.model_data.get("free", True))
            self.id_input.setEnabled(False)

    def validate_and_accept(self):
        model_id = self.id_input.text().strip()
        name = self.name_input.text().strip()

        if not model_id:
            QMessageBox.warning(self, "Validation Error", "Model ID is required.")
            self.id_input.setFocus()
            return
        if not name:
            QMessageBox.warning(self, "Validation Error", "Display Name is required.")
            self.name_input.setFocus()
            return

        self.accept()

    def get_model_data(self):
        return {
            "id": self.id_input.text().strip(),
            "name": self.name_input.text().strip(),
            "description": self.desc_input.text().strip(),
            "free": self.free_checkbox.isChecked()
        }

    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                }
                QLabel {
                    color: #e0e0e0;
                    font-size: 13px;
                }
                QGroupBox {
                    border: 1px solid #3c3c3c;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 20px 15px 15px 15px;
                    font-size: 13px;
                }
                QGroupBox::title {
                    color: #0078d4;
                    subcontrol-origin: margin;
                    left: 15px;
                    padding: 0 5px;
                }
                QLineEdit {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    border: 1px solid #3c3c3c;
                    border-radius: 5px;
                    padding: 8px 12px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border-color: #0078d4;
                }
                QLineEdit:disabled {
                    background-color: #252526;
                    color: #888888;
                }
                QCheckBox {
                    color: #e0e0e0;
                    spacing: 8px;
                    font-size: 13px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 2px solid #3c3c3c;
                    background-color: #1e1e1e;
                }
                QCheckBox::indicator:checked {
                    background-color: #0078d4;
                    border-color: #0078d4;
                }
                QDialogButtonBox QPushButton {
                    background-color: #0078d4;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 25px;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                    min-width: 90px;
                }
                QDialogButtonBox QPushButton:hover {
                    background-color: #106ebe;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                    font-size: 13px;
                }
                QGroupBox {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding: 20px 15px 15px 15px;
                    font-size: 13px;
                }
                QGroupBox::title {
                    color: #0078d4;
                    subcontrol-origin: margin;
                    left: 15px;
                    padding: 0 5px;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    padding: 8px 12px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border-color: #0078d4;
                }
                QLineEdit:disabled {
                    background-color: #f5f5f5;
                    color: #888888;
                }
                QCheckBox {
                    color: #333333;
                    spacing: 8px;
                    font-size: 13px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 2px solid #cccccc;
                    background-color: #ffffff;
                }
                QCheckBox::indicator:checked {
                    background-color: #0078d4;
                    border-color: #0078d4;
                }
                QDialogButtonBox QPushButton {
                    background-color: #0078d4;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 25px;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                    min-width: 90px;
                }
                QDialogButtonBox QPushButton:hover {
                    background-color: #106ebe;
                }
            """)
