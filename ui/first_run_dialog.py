# ui/first_run_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QFrame, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap

import sys
from pathlib import Path
from utils.storage_config import StorageManager

class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LLM Chat App - Welcome Setup")
        self.setFixedSize(500, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Set global basic style in case external QSS is missing
        self.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
                color: #FFFFFF;
            }
            QLabel#Header {
                font-size: 20px;
                font-weight: bold;
                color: #4CAF50;
            }
            QLabel#SubHeader {
                font-size: 13px;
                color: #AAAAAA;
            }
            QFrame#OptionCard {
                background-color: #333333;
                border: 1px solid #444444;
                border-radius: 8px;
            }
            QPushButton#ActionBtn {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
            }
            QPushButton#ActionBtn:hover {
                background-color: #45a049;
            }
            QPushButton#ActionBtn:pressed {
                background-color: #388E3C;
            }
            QLabel#OptionTitle {
                font-size: 14px;
                font-weight: bold;
                color: white;
            }
            QLabel#OptionDesc {
                font-size: 11px;
                color: #BBBBBB;
            }
        """)
        
        self.storage_mgr = StorageManager.get_instance()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # Header
        header_lbl = QLabel("Initial Data Setup")
        header_lbl.setObjectName("Header")
        main_layout.addWidget(header_lbl)

        sub_lbl = QLabel("Select where to store chat history, cached assets, and settings.\nYou can modify this only by moving the data folder manually later.")
        sub_lbl.setObjectName("SubHeader")
        sub_lbl.setWordWrap(True)
        main_layout.addWidget(sub_lbl)

        main_layout.addSpacing(10)

        # Option 1: Standard (User AppData)
        appdata_card = self.create_option_card(
            "Standard Install (Recommended)",
            f"Saves everything to your secure User Profile.\n({self.storage_mgr.get_default_app_data_path()})",
            "Install",
            self.on_select_appdata
        )
        main_layout.addWidget(appdata_card)

        # Option 2: Portable Mode
        exe_path = self.storage_mgr.get_exe_dir()
        portable_card = self.create_option_card(
            "Truly Portable Mode",
            f"Zero registry footprint. Keeps everything inside the program folder.\n({exe_path})",
            "Go Portable",
            self.on_select_portable
        )
        main_layout.addWidget(portable_card)

        # Option 3: Custom Path
        custom_card = self.create_option_card(
            "Custom Storage Location",
            "Store data on an external drive, USB stick, or synced Dropbox folder.",
            "Browse...",
            self.on_select_custom
        )
        main_layout.addWidget(custom_card)

        main_layout.addStretch()

    def create_option_card(self, title, desc, btn_text, callback):
        card = QFrame()
        card.setObjectName("OptionCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(15, 10, 15, 10)
        
        txt_container = QVBoxLayout()
        
        t_lbl = QLabel(title)
        t_lbl.setObjectName("OptionTitle")
        
        d_lbl = QLabel(desc)
        d_lbl.setObjectName("OptionDesc")
        d_lbl.setWordWrap(True)
        
        txt_container.addWidget(t_lbl)
        txt_container.addWidget(d_lbl)
        
        card_layout.addLayout(txt_container, stretch=1)
        
        btn = QPushButton(btn_text)
        btn.setObjectName("ActionBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedWidth(120)
        btn.clicked.connect(callback)
        card_layout.addWidget(btn, alignment=Qt.AlignVCenter)
        
        return card

    def on_select_appdata(self):
        self.storage_mgr.finalize_setup("APPDATA")
        self.accept()

    def on_select_portable(self):
        reply = QMessageBox.question(
            self, "Confirm Portable", 
            "This will create a 'portable.txt' file in your executable folder. Proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.storage_mgr.finalize_setup("PORTABLE")
            self.accept()

    def on_select_custom(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Data Storage Directory")
        if dir_path:
            target = Path(dir_path)
            if not self.storage_mgr.check_dir_writable(target):
                 QMessageBox.critical(self, "Error", "This directory is not writable. Please choose another location.")
                 return
            self.storage_mgr.finalize_setup("CUSTOM", target)
            self.accept()

if __name__ == "__main__":
    # Fast UI testing stub
    app = QApplication([])
    win = FirstRunDialog()
    win.show()
    sys.exit(app.exec())
