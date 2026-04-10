# ui/model_manager.py
# This file defines the ModelManagerDialog class, which provides a UI for managing LLM models. It allows users to add, edit, and delete models that are stored in models.json. The dialog displays a table of existing models with their ID, name, description, and whether they are free or    not. Users can select a model to edit or delete, or add a new model using the ModelEditDialog. Changes are saved back to models.json and the active model selection is updated in QSettings if necessary.  

import json
from PySide6.QtWidgets import (
    QDialog, QMessageBox, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtUiTools import QUiLoader

from ui.model_edit_dialog import ModelEditDialog
from utils.path_utils import get_resource_path

class ModelManagerDialog(QDialog):
    """Main dialog for viewing and managing models."""

    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self.theme = theme
        self.models = []

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
        self.table = self.findChild(object, "table")
        self.add_btn = self.findChild(object, "add_btn")
        self.edit_btn = self.findChild(object, "edit_btn")
        self.delete_btn = self.findChild(object, "delete_btn")
        self.close_btn = self.findChild(object, "close_btn")
        self.refresh_btn = self.findChild(object, "refresh_btn")

        self.setup_table()
        self.setup_connections()
        self.load_models()
        self.populate_table()
        self.apply_theme()

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
        self.table.doubleClicked.connect(self.edit_model)

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
        return get_resource_path("resources/models.json")

    def load_models(self):
        models_file = self.get_models_file_path()
        if models_file.exists():
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.models = data.get("models", [])
        else:
            self.models = []

    def save_models(self):
        models_file = self.get_models_file_path()
        data = {"models": self.models}
        with open(models_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def update_count_label(self):
        self.count_label.setText(f"{len(self.models)} model(s)")

    def populate_table(self):
        self.table.setRowCount(len(self.models))
        for row, model in enumerate(self.models):
            from PySide6.QtWidgets import QTableWidgetItem

            id_item = QTableWidgetItem(model.get("id", ""))
            id_item.setData(Qt.ItemDataRole.UserRole, row)
            self.table.setItem(row, 0, id_item)

            self.table.setItem(row, 1, QTableWidgetItem(model.get("name", "")))
            #self.table.setItem(row, 2, QTableWidgetItem(model.get("description", "")))

            # Description with Top-Left alignment for wrapping
            desc_text = model.get("description", "")
            desc_item = QTableWidgetItem(desc_text)
            self.table.setItem(row, 2, desc_item)

            is_free = model.get("free", True)
            free_text = "✅ Free" if is_free else "💰 Paid"
            free_item = QTableWidgetItem(free_text)
            free_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            free_item.setForeground(QColor("#4caf50") if is_free else QColor("#ff9800"))
            self.table.setItem(row, 3, free_item)

        self.update_count_label()
        self.table.resizeRowsToContents()

    def get_selected_row_index(self):
        row = self.table.currentRow()
        return row if row >= 0 else None

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
            self.populate_table()
            self.table.selectRow(len(self.models) - 1)
            self.table.scrollToBottom()

    def edit_model(self):
        row = self.get_selected_row_index()
        if row is None:
            QMessageBox.information(self, "No Selection", "Please select a model to edit.")
            return

        model_data = self.models[row]
        dialog = ModelEditDialog(model_data=model_data, theme=self.theme, parent=self)

        if dialog.exec():
            updated_model = dialog.get_model_data()
            self.models[row] = updated_model
            self.save_models()
            self.populate_table()
            self.table.selectRow(row)

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