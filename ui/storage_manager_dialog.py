# ui/storage_manager_dialog.py
import os
import sys
import shutil
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QFrame, QMessageBox, 
                               QLineEdit, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QUrl
from PySide6.QtUiTools import QUiLoader

from utils.storage_config import StorageManager
from utils.path_utils import get_resource_path

class StorageManagerDialog(QDialog):
    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self.theme = theme
        
        # Setup Logic Data
        self.storage_mgr = StorageManager.get_instance()
        self.current_root = self.storage_mgr.get_storage_root()
        
        # LOAD EXTERNAL UI DESIGN
        loader = QUiLoader()
        ui_file_path = get_resource_path("ui_designer/storage_manager.ui")
        self.ui = loader.load(str(ui_file_path), self)
        
        # Attach Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)
        
        # Configure Initial UI State
        self.setWindowTitle("Storage Management Center")
        self.ui.pathEdit.setText(str(self.current_root))
        self.ui.metricsLabel.setText(self.calculate_storage_size())
        
        # Bind Signals
        self.ui.revealBtn.clicked.connect(self.on_reveal)
        self.ui.relocateBtn.clicked.connect(self.on_relocate_workflow)
        self.ui.doneBtn.clicked.connect(self.accept)
        
        self.apply_theme()

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
                QLineEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #3c3c3c;
                    border-radius: 4px;
                    padding: 6px;
                }
                QFrame {
                    border: 1px solid #3c3c3c;
                    border-radius: 6px;
                    background-color: #252526;
                }
                QPushButton {
                    background-color: #0078d4;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #106ebe; }
                
                #headerLabel {
                    color: #ffffff;
                    border: none;
                    background: transparent;
                }
                #doneBtn {
                    background-color: #3c3c3c;
                }
                #doneBtn:hover { background-color: #4c4c4c; }
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
                QLineEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 6px;
                }
                QFrame {
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    background-color: #f9f9f9;
                }
                QPushButton {
                    background-color: #0078d4;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #106ebe; }
                
                #headerLabel {
                    color: #000000;
                    border: none;
                    background: transparent;
                }
                #doneBtn {
                    background-color: #e0e0e0;
                    color: #333333;
                }
                #doneBtn:hover { background-color: #d0d0d0; }
            """)

    def calculate_storage_size(self) -> str:
        """Calculate disk footprint of relevant sub-folders for premium feel."""
        total_size = 0
        targets = ['conversations', 'resources', 'cache']
        try:
            for folder in targets:
                folder_path = self.current_root / folder
                if folder_path.exists():
                    for entry in os.scandir(folder_path):
                        if entry.is_file():
                            total_size += entry.stat().st_size
                        elif entry.is_dir():
                            for sub in os.scandir(entry.path):
                                if sub.is_file():
                                    total_size += sub.stat().st_size
            
            mb = total_size / (1024 * 1024)
            return f"📊 Local Footprint Assessment: {mb:.2f} MB used across history and metadata streams."
        except Exception:
            return "📊 Footprint assessment unavailable."

    def on_reveal(self):
        """Instantly launch current location in system file explorer."""
        if self.current_root.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.current_root)))
        else:
            QMessageBox.warning(self, "Path Missing", "Active root path could not be located.")

    def on_relocate_workflow(self):
        """Launch nested relocation choice selector."""
        confirm = QMessageBox.question(
            self, 
            "Initiate Data Migration?", 
            "This protocol will lock filesystem streams, clone your current dataset to a new target, and require an immediate Application Restart.\n\nDo you wish to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        from PySide6.QtWidgets import QInputDialog
        items = ["⚡ Portable Mode (Keeps it in the Program Folder)", 
                 "🛡️ Standard Mode (System AppData Profile)", 
                 "🌍 Custom Network/Drive Location"]
        
        item, ok = QInputDialog.getItem(self, "Choose New Storage Strategy", 
                                        "Select target allocation model:", items, 0, False)
        
        if not ok or not item:
            return

        target_type = None
        target_path = None

        if "Portable" in item:
            target_type = "PORTABLE"
            target_path = self.storage_mgr.get_exe_dir()
        elif "Standard" in item:
            target_type = "APPDATA"
            target_path = self.storage_mgr.get_default_app_data_path()
        else:
            target_type = "CUSTOM"
            dir_path = QFileDialog.getExistingDirectory(self, "Select Custom Destination Folder")
            if not dir_path:
                return
            target_path = Path(dir_path)

        if target_path.resolve() == self.current_root.resolve():
            QMessageBox.information(self, "Same Location", "Destination matches current location. Abandoning migration.")
            return
            
        if not self.storage_mgr.check_dir_writable(target_path):
            QMessageBox.critical(self, "Permission Denied", "Target is write-protected. Aborting relocation.")
            return

        self.execute_safe_migration(target_type, target_path)

    def execute_safe_migration(self, mode, target_path):
        progress = QMessageBox(self)
        progress.setWindowTitle("Relocating...")
        progress.setText("Syncing localized databases and cloning assets to new target...\nPlease do not interrupt process.")
        progress.setStandardButtons(QMessageBox.NoButton)
        progress.show()
        QApplication.processEvents()
        
        try:
            # 1. Sever active IO handles from Parent Main Window
            if self.parent() and hasattr(self.parent(), 'conversation_manager'):
                 mgr = self.parent().conversation_manager
                 if mgr and hasattr(mgr, 'conn') and mgr.conn:
                      mgr.conn.close()
                      mgr.conn = None
            
            target_path.mkdir(parents=True, exist_ok=True)
            
            payloads = ['conversations', 'resources', 'cache']
            for p in payloads:
                src = self.current_root / p
                dst = target_path / p
                if src.exists() and src.is_dir():
                     if dst.exists():
                         shutil.rmtree(dst)
                     shutil.copytree(src, dst)
            
            old_exe_dir = self.storage_mgr.get_exe_dir()
            if self.storage_mgr.is_portable and mode != "PORTABLE":
                portable_marker = old_exe_dir / "portable.txt"
                if portable_marker.exists():
                    try:
                        portable_marker.unlink()
                    except Exception: pass
            
            from PySide6.QtCore import QSettings
            settings = QSettings("LLMChatApp", "Settings")
            if mode == "PORTABLE":
                settings.remove("storage/data_root")
            
            self.storage_mgr.finalize_setup(mode, target_path)
            progress.hide()
            
            QMessageBox.information(
                self, 
                "Migration Complete", 
                "System data fully cloned. Application will now restart."
            )
            self.restart_application()

        except Exception as e:
            progress.hide()
            QMessageBox.critical(self, "Migration Failure", f"Handoff failed:\n{str(e)}")

    def restart_application(self):
        try:
            args = sys.argv[:]
            exe = sys.executable
            subprocess.Popen([exe] + args)
            QApplication.quit()
            sys.exit(0)
        except Exception:
            QApplication.quit()
