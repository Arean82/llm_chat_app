import sys
import os
import time
from pathlib import Path

# Ensure we can resolve root imports when running from resources folder
sys.path.append(str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from desktop.ui.main_window import MainWindowClass

def generate_all():
    """Dynamically cycles through themes and views to export complete screenshot pack."""
    print("Initialize QApplication...", flush=True)
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("Booting MainWindowClass (this may take a few seconds to load DBs and Workers)...", flush=True)
    window = MainWindowClass()
    window.resize(1280, 720)
    
    print("MainWindow initialized successfully.", flush=True)
    
    # Setup absolute base directory for output
    base_dir = Path(__file__).parent.parent / "resources" / "screenshots"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Initiating Auto-Snap Engine targeting: {base_dir}", flush=True)
    
    current_dialog = [None] # Store reference to prevent garbage collection
    
    def load_operator_tool_ui(relative_path, stylesheet="", window_title=""):
        if current_dialog[0]:
            current_dialog[0].close()
            current_dialog[0].deleteLater()
            
        from PySide6.QtUiTools import QUiLoader
        from PySide6.QtCore import QFile
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        
        full_path = str(Path(__file__).parent.parent / relative_path)
        ui_file = QFile(full_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        widget = loader.load(ui_file, None)
        ui_file.close()
        
        dlg = QDialog()
        dlg.setWindowTitle(window_title)
        if stylesheet:
            dlg.setStyleSheet(stylesheet)
            # Apply to widget too in case it blocks inheritance
            widget.setStyleSheet(stylesheet)
            
        dlg.setMinimumSize(800, 600)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(widget)
        current_dialog[0] = dlg
        dlg.show()
        return dlg

    # Migration Companion CSS
    mc_css = """
    * { font-family: "Segoe UI", "Inter", "Roboto", "Helvetica Neue", Arial, sans-serif; font-size: 10pt; }
    QMainWindow, QDialog, QTabWidget::pane { background-color: #f8f9fa; border: none; }
    QTabBar::tab { background-color: #e9ecef; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
    QTabBar::tab:selected { background-color: #ffffff; border-bottom: 2px solid #0078d4; font-weight: bold; }
    QGroupBox { font-weight: bold; border: 1px solid #dee2e6; border-radius: 6px; margin-top: 12px; background-color: #ffffff; }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #0078d4; }
    QPushButton { background-color: #0078d4; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
    QPushButton:hover { background-color: #106ebe; }
    QPushButton:pressed { background-color: #005a9e; }
    QPushButton:disabled { background-color: #a0a0a0; }
    QLineEdit, QComboBox { border: 1px solid #ced4da; border-radius: 4px; padding: 6px; background-color: #ffffff; }
    QLineEdit:focus, QComboBox:focus { border: 1px solid #0078d4; }
    """

    # Reset Admin CSS
    ra_css = """
    QDialog { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', Arial, sans-serif; }
    QLabel { color: #c9d1d9; }
    QLabel#warning_icon { color: #d73a49; font-size: 48px; }
    QLabel#title_label { color: #ffffff; font-size: 18px; font-weight: bold; }
    QTextEdit { background-color: #010409; color: #8b949e; border: 1px solid #30363d; border-radius: 5px; }
    QPushButton#btn_reset { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d73a49, stop:1 #cb2431); color: #ffffff; border: 1px solid #cb2431; border-radius: 8px; }
    QPushButton#btn_reset:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #cb2431, stop:1 #b31d28); }
    QPushButton#btn_close { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 8px; }
    QPushButton#btn_close:hover { background-color: #30363d; border: 1px solid #484f58; }
    """

    # Execution queue: (Theme, SetupFn, FilenameSuffix, CustomDir)
    tasks = [
        ("light",  lambda: window.show_chat_mode(), "Main_Window.png", None),
        ("light",  lambda: window.show_arena_mode(), "Arena_Mode.png", None),
        ("light",  lambda: show_dialog("FirstRunDialog"), "Initial_Data_Setup_Preview.png", None),
        ("light",  lambda: show_dialog("ModelManagerDialog"), "Model_Manager.png", None),
        ("light",  lambda: show_dialog("LogViewerDialog"), "Log_Viewer.png", None),
        ("light",  lambda: show_dialog("LoginDialogClass"), "Login_Dialog.png", None),
        ("light",  lambda: show_dialog("CustomProviderDialogClass"), "Custom_Provider_Dialog.png", None),
        ("light",  lambda: show_dialog("GenSettingsDialog"), "Gen_Settings.png", None),
        ("light",  lambda: show_dialog("SystemPromptManagerClass"), "System_Prompt_Manager.png", None),
        ("light",  lambda: load_operator_tool_ui("operator_tools/migration/ui_assets/dashboard.ui", mc_css, "Administrator Dashboard"), "Migration_Companion.png", "operator_tools/migration"),
        ("light",  lambda: load_operator_tool_ui("operator_tools/admin_reset/ui_assets/reset_admin.ui", ra_css, "Master Protocol Reset"), "Reset_Admin.png", "operator_tools/admin_reset")
    ]
    
    def show_dialog(class_name):
        # Close any open dialog
        if current_dialog[0]:
            current_dialog[0].close()
            current_dialog[0].deleteLater()
            
        import desktop.ui.first_run_dialog
        import desktop.ui.model_manager
        import desktop.ui.log_viewer
        import desktop.ui.login_dialog
        import desktop.ui.custom_provider_dialog
        import desktop.ui.gen_settings_dialog
        import desktop.ui.system_prompt_manager
        
        # Dynamically instantiate the requested dialog
        cls_map = {
            "FirstRunDialog": ui.first_run_dialog.FirstRunDialog,
            "ModelManagerDialog": ui.model_manager.ModelManagerDialog,
            "LogViewerDialog": ui.log_viewer.LogViewerDialog,
            "LoginDialogClass": ui.login_dialog.LoginDialogClass,
            "CustomProviderDialogClass": ui.custom_provider_dialog.CustomProviderDialogClass,
            "GenSettingsDialog": ui.gen_settings_dialog.GenSettingsDialog,
            "SystemPromptManagerClass": ui.system_prompt_manager.SystemPromptManagerClass
        }
        dlg = cls_map[class_name]()
        current_dialog[0] = dlg
        dlg.show()
        return dlg
        
    def process_next_task(queue):
        if not queue:
            print("\n🎉 ALL SNAPS COMPLETED SUCCESSFULLY.", flush=True)
            window.close()
            app.quit()
            return
            
        theme, view_fn, filename, custom_dir = queue.pop(0)
        print(f"📸 Capturing {filename} in {theme.upper()}...", flush=True)
        
        # 1. Apply Visual State
        window.theme_manager.apply_theme(theme)
        view_fn()
        window.show()
        
        # 2. Allow layout to breathe, then snap
        def snap():
            if custom_dir:
                # Ensure the target custom directory exists
                target_dir = Path(__file__).parent.parent / custom_dir
                target_dir.mkdir(parents=True, exist_ok=True)
                save_path = target_dir / filename
            else:
                save_path = base_dir / filename
                
            if current_dialog[0]:
                pixmap = current_dialog[0].grab()
            else:
                pixmap = window.grab()
                
            if pixmap.save(str(save_path), "PNG"):
                print(f"   ✅ Saved -> {save_path}", flush=True)
            else:
                print(f"   ❌ FAILED -> {filename}", flush=True)
            
            # Process next after slight delay for UI safety
            QTimer.singleShot(500, lambda: process_next_task(queue))
            
        QTimer.singleShot(800, snap)

    # Kick off first task
    process_next_task(tasks)
    sys.exit(app.exec())

if __name__ == "__main__":
    generate_all()
