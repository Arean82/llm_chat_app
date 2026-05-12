# ui/main_window.py
# Shell Controller for Modular Platform Architecture

import sys
import os
import keyring
from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox, QSystemTrayIcon, QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit
from PySide6.QtCore import QTimer, Qt, QSettings, QEvent
from PySide6.QtGui import QIcon, QPixmap, QAction, QTextBlockUserData, QActionGroup
from PySide6.QtUiTools import QUiLoader

from logic.llm_client import LLMClient
from logic.api_manager import ApiManager
from logic.formatter import MessageFormatter
from ui.theme_manager import ThemeManager
from workers.connection_worker import ConnectionWorker
from utils.path_utils import get_resource_path, get_app_settings
from utils.helpers import set_app_icon

# Import child modules
from ui.chat_view import ChatViewWidget
from ui.arena_view import ArenaViewWidget

# Shared Data Classes used by view internals
from ui.shared_widgets import MessageData, ChatDisplay

class MainWindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Initializing Main Window Host Shell...")

        # Master System Singletons (Shared by ALL views)
        self.theme_manager = ThemeManager(self)
        self.api_manager = ApiManager(self)
        self.formatter = MessageFormatter(self.theme_manager)
        self.llm_client = LLMClient()
        self.is_connected = True

        # Load Empty Master Shell Layout
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/main_window.ui")
        self.ui = loader.load(str(ui_file))
        self.setCentralWidget(self.ui)
        set_app_icon(self)

        # Setup Shared Connection Worker
        self.connection_worker = ConnectionWorker()
        self.connection_worker.status_changed.connect(self.on_connection_status_changed)
        self.connection_worker.start()

        # Instantiate Views dynamically!
        self.chat_view = ChatViewWidget(self, self.llm_client, self.theme_manager, self.formatter)
        self.arena_view = ArenaViewWidget(self, self.llm_client, self.theme_manager, self.formatter)
        
        # Push them into our master stack!
        self.ui.main_stack.addWidget(self.chat_view)
        self.ui.main_stack.addWidget(self.arena_view)
        
        # Default to Chat Mode on launch
        self.ui.main_stack.setCurrentWidget(self.chat_view)

        # System Setup
        self.setup_menu_bar()
        self.setup_tray()
        self.load_settings()
        
        print("Shell ready. Launching in default View Mode.")

    # ---------------------------------------------------------
    # DYNAMIC MODE SWITCHING ENGINE
    # ---------------------------------------------------------
    def show_chat_mode(self):
        self.ui.main_stack.setCurrentWidget(self.chat_view)
        if hasattr(self, 'act_chat_mode'): self.act_chat_mode.setChecked(True)
        self.statusBar().showMessage("Switched to Chat Mode", 2000)

    def show_arena_mode(self):
        self.ui.main_stack.setCurrentWidget(self.arena_view)
        if hasattr(self, 'act_arena_mode'): self.act_arena_mode.setChecked(True)
        self.statusBar().showMessage("Switched to Model Arena", 2000)

    # ---------------------------------------------------------
    # SHARED GLOBAL CONTROLLERS (Forward to active view where needed)
    # ---------------------------------------------------------
    def on_connection_status_changed(self, connected):
        self.is_connected = connected
        self.update_connection_icon()

    def update_connection_icon(self):
        icon = "🌐" if self.is_connected else "🔴"
        # Push status update to active view
        if hasattr(self.ui.main_stack.currentWidget(), 'connection_status_btn'):
            self.ui.main_stack.currentWidget().connection_status_btn.setText(icon)

    def force_disconnected_state(self):
        self.is_connected = False
        self.update_connection_icon()

    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # Master View Switcher
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Conversation", self.chat_view.start_new_chat, "Ctrl+N")
        file_menu.addAction("Save Conversation", self.chat_view.auto_save_current_chat, "Ctrl+S")
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.quit_app, "Ctrl+Q")
        
        view_menu = menubar.addMenu("📺 View Mode")
        
        self.view_mode_group = QActionGroup(self)
        self.view_mode_group.setExclusive(True)
        
        self.act_chat_mode = view_menu.addAction("💬 Single Chat Mode", self.show_chat_mode)
        self.act_chat_mode.setCheckable(True)
        self.act_chat_mode.setChecked(True)
        self.view_mode_group.addAction(self.act_chat_mode)
        
        self.act_arena_mode = view_menu.addAction("⚔️ Model Arena", self.show_arena_mode)
        self.act_arena_mode.setCheckable(True)
        self.view_mode_group.addAction(self.act_arena_mode)

        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("📦 Model Manager", self.show_model_manager)
        settings_menu.addAction("✏️ Instructions", self.edit_system_instructions)
        
        # Tools Menu
        tools_menu = menubar.addMenu("Tools")
        self.api_server_action = tools_menu.addAction("🌐 Universal API Server")
        self.api_server_action.setCheckable(True)
        self.api_server_action.triggered.connect(self.api_manager.toggle_api_server)
        
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("📖 Readme", self.show_readme)
        help_menu.addAction("📜 License", self.show_license)
        help_menu.addAction("📡 API Documentation", self.api_doc)
        help_menu.addAction("🔌 IDE Integration Guide", self.show_ide_integration)
        help_menu.addSeparator()
        help_menu.addAction("📦 Download VS Code Extension", self.download_vscode_extension)
        help_menu.addAction("🧩 Download JetBrains Plugin", self.download_jetbrains_plugin)
        help_menu.addSeparator()
        help_menu.addAction("ℹ️ About", self.show_about)

    def load_settings(self):
        settings = get_app_settings()
        nk = keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key")
        gk = keyring.get_password("LLMChatApp", "api_key_google")
        mid = settings.value("current_model_id", "")
        
        self.theme_manager.apply_theme(settings.value("theme", "light"))
        
        if nk: self.llm_client.set_api_key(nk)
        if gk: self.llm_client.set_google_api_key(gk)
        
        if mid:
            self.llm_client.set_model(mid)
            self.chat_view.update_model_ui(mid)
            self.chat_view.set_chat_enabled(True)
        else:
            self.chat_view.set_chat_enabled(False)

        if nk or gk: self.tray_icon.show()

    def handle_auth_button(self):
        if self.llm_client.has_api_key(): self.logout()
        else: self.open_settings()

    def open_settings(self):
        from ui.login_dialog import SettingsDialogClass
        d = SettingsDialogClass(None)
        if d.exec():
            self.load_settings()
            return True
        return False

    def show_model_popup(self):
        from ui.model_popup import ModelPopupClass
        mid = get_app_settings().value("current_model_id", "")
        d = ModelPopupClass(current_model_id=mid, parent=self)
        if d.exec():
            sid = d.get_selected_model_id()
            if sid:
                self.llm_client.set_model(sid)
                self.chat_view.update_model_ui(sid)
                self.chat_view.set_chat_enabled(True)

    def logout(self):
        # Simple global logout
        try:
            keyring.delete_password("LLMChatApp", "api_key_nvidia")
            keyring.delete_password("LLMChatApp", "api_key_google")
        except: pass
        get_app_settings().remove("current_model_id")
        self.llm_client.clear_keys()
        self.chat_view.clear_chat()
        self.chat_view.set_chat_enabled(False)
        self.tray_icon.hide()
        self.open_settings()

    def edit_system_instructions(self):
        from ui.system_prompt_manager import SystemPromptManagerClass
        SystemPromptManagerClass(self).exec()
        self.chat_view.add_system_message("Instruction Library updated.")

    def show_model_manager(self):
        from ui.model_manager import ModelManagerDialog
        ModelManagerDialog(theme=self.theme_manager.current_theme, parent=self).exec()

    def show_about(self):
        from utils.constants import APP_VERSION
        border_color = "#3c3c3c" if self.theme_manager.current_theme == "dark" else "#e0e0e0"
        
        text = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <h2 style="color: #0078d4; margin-bottom: 5px;">LLM Chat App</h2>
            <p><b>Version:</b> {APP_VERSION}<br>
            <b>Lead Architect:</b> Arean Narrayan</p>
            
            <hr style="border: 1px solid {border_color}; margin: 10px 0;">
            
            <p>A premium, high-performance desktop workstation engineered to serve as a 
            universal, ecosystem-agnostic gateway into state-of-the-art Large Language Models.</p>
            
            <p><b>Key Technologies:</b></p>
            <ul>
                <li>🚀 Infinite Context via <b>Adaptive Memory Compression</b></li>
                <li>🤖 Universal Orchestration (NVIDIA, Google, Groq, Ollama, OpenAI)</li>
                <li>⚡ High-Velocity Markdown & Code Syntax Rendering</li>
                <li>🔐 Secure OS-Level Credential Custody Vault</li>
                <li>🌐 Local OpenAI-Compatible API Server</li>
            </ul>
            
            <hr style="border: 1px solid {border_color}; margin: 10px 0;">
            
            <p style="font-size: 11px; color: #666666;">
            Empowering Universal AI Compute Access<br>
            Built with <b>Python 3.12</b> & <b>PySide6</b></p>
        </div>
        """
        QMessageBox.about(self, "About", text)

    def show_readme(self):
        from ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="Readme", 
            file_names=["README.md", "README.txt", "README"], 
            is_markdown=True, 
            size=(750, 600), 
            parent=self
        )
        dialog.exec()

    def show_license(self):
        from ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="License", 
            file_names=["LICENSE", "LICENSE.txt", "License"], 
            is_markdown=False, 
            size=(630, 410), 
            parent=self
        )
        dialog.exec()

    def api_doc(self):
        from ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="Universal API Server Documentation",
            file_names=["API_SERVER.md"], 
            is_markdown=True,
            size=(800, 600),
            parent=self
        )
        dialog.exec()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(str(get_resource_path("resources/app_icon.png"))))
        m = QMenu()
        m.addAction("Restore", self.show)
        m.addAction("Quit", self.quit_app)
        self.tray_icon.setContextMenu(m)

    def quit_app(self):
        # Graceful Thread Teardown
        if hasattr(self, 'connection_worker'):
            self.connection_worker.terminate()
            self.connection_worker.wait()
        
        # Stop any active dual workers in arena just in case
        if hasattr(self, 'arena_view'):
            self.arena_view.stop_duel()

        self.tray_icon.hide()
        QApplication.quit()

    def eventFilter(self, obj, event):
        # Shared input dispatch for keyboard shortcuts passed from views
        if event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() == Qt.ShiftModifier:
                 active = self.ui.main_stack.currentWidget()
                 if active == self.chat_view:
                      self.chat_view.send_message()
                      return True
                 elif active == self.arena_view:
                      self.arena_view.handle_duel_action()
                      return True
        return super().eventFilter(obj, event)

    def toggle_theme(self):
        self.theme_manager.toggle_theme()

    def closeEvent(self, event):
        # Simply minimize to tray or quit safely
        self.quit_app()
        event.accept()
        
    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
             if not (self.windowState() & Qt.WindowState.WindowMaximized) and not (self.windowState() & Qt.WindowState.WindowFullScreen):
                  QTimer.singleShot(0, self.showMaximized)
        super().changeEvent(event)

    def show_ide_integration(self):
        from ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="IDE Integration Guide",
            file_names=["IDE_INTEGRATION.md"],
            is_markdown=True,
            size=(750, 600),
            parent=self
        )
        dialog.exec()

    def download_vscode_extension(self):
        import os
        from pathlib import Path
        folder = Path(__file__).parent.parent / "extension"
        if folder.exists():
            os.startfile(str(folder))
            QMessageBox.information(
                self, "VS Code Extension",
                "The extension folder is now open.\n\nInstall:\n1. VS Code → Extensions → ... → Install from VSIX\n2. Select vscode-llm-chat-1.0.1.vsix"
            )
        else:
            QMessageBox.warning(self, "Folder Not Found", "extension folder not found")

    def download_jetbrains_plugin(self):
        import os
        from pathlib import Path
        folder = Path(__file__).parent.parent / "extension"
        if folder.exists():
            os.startfile(str(folder))
            QMessageBox.information(
                self, "JetBrains Plugin",
                "The extension folder is now open.\n\nInstall:\n1. Settings → Plugins → ⚙️ → Install Plugin from Disk\n2. Select jetbrains-llm-chat-1.0.1.zip"
            )
        else:
            QMessageBox.warning(self, "Folder Not Found", "extension folder not found")
