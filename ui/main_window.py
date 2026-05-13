# ui/main_window.py
# Shell Controller for Modular Platform Architecture

import sys
import os
import keyring
from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox, QSystemTrayIcon, QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QSplitter
from PySide6.QtCore import QTimer, Qt, QSettings, QEvent
from PySide6.QtGui import QIcon, QPixmap, QAction, QTextBlockUserData, QActionGroup
from PySide6.QtUiTools import QUiLoader

from logic.llm_client import LLMClient
from logic.api_manager import ApiManager
from logic.formatter import MessageFormatter
from ui.theme_manager import ThemeManager
from workers.connection_worker import ConnectionWorker
from workers.local_model_detector import LocalModelDetector
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

        # Fire non-blocking Local Model Auto-Detection Sweep (Ollama/LM Studio)
        self.local_detector = LocalModelDetector()
        self.local_detector.detection_completed.connect(self.on_local_models_detected)
        self.local_detector.start()

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

    def on_local_models_detected(self, provider, count):
        """Accept telemetry from auto-sweep daemon and announce toast notification."""
        msg = f"⚡ Local {provider} Engine Detected - {count} new models synced."
        # 1. Statusbar non-blocking toast
        self.statusBar().showMessage(msg, 6000)
        # 2. Inject persistent announcement directly into the active chat log stream
        if hasattr(self, 'chat_view') and self.chat_view:
             self.chat_view.add_system_message(msg)

    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # Master View Switcher
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Conversation", self.chat_view.start_new_chat, "Ctrl+N")
        file_menu.addAction("Save Conversation", self.chat_view.auto_save_current_chat, "Ctrl+S")
        file_menu.addAction("Import Chat (.json)", self.chat_view.load_conversation)
        file_menu.addAction("Export Chat (.json)", self.chat_view.save_conversation)
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
        settings_menu.addAction("✏️ System Instructions", self.edit_system_instructions, "Ctrl+I")
        settings_menu.addAction("⚙️ Generation Parameters", self.show_gen_settings)
        settings_menu.addSeparator()
        settings_menu.addAction("🗄️ Storage Manager", self.show_storage_manager)
        settings_menu.addAction("📂 Open Data Folder", self.open_storage_location)

        # Log menu
        log_menu = menubar.addMenu("Log")
        log_menu.addAction("📋 View Update Log", self.show_update_log)
        log_menu.addAction("🗑️ Clear Log", self.clear_update_log)

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
        
        # 1. Apply Global Theme state
        self.theme_manager.apply_theme(settings.value("theme", "light"))
        
        # 2. Restore Parallel Google Ecosystem Access
        gk = keyring.get_password("LLMChatApp", "api_key_google")
        if gk: self.llm_client.set_google_api_key(gk)
        
        # 3. Restore Active OpenAI-Compatible Ecosystem Access (Audit ID 028 Fix)
        active_p = settings.value("active_provider_id", "nvidia")
        
        # Fetch targeted localized endpoint
        b_url = settings.value(f"url_{active_p}") or settings.value("base_url")
        # Filter google endpoints to avoid OpenAI client path contamination
        if b_url and active_p != "google" and "google" not in b_url: 
             self.llm_client.set_base_url(b_url)
             
        # Fetch targeted API credential from isolated slot
        ak = None
        if active_p != "google":
             ak = keyring.get_password("LLMChatApp", f"api_key_{active_p}")
             
        # Generic Fallback Scan: Support legacy setups and cross-ecosystem transitions
        if not ak:
             # Probe primary and explicit historical vault keys
             candidate = keyring.get_password("LLMChatApp", "api_key") or keyring.get_password("LLMChatApp", "api_key_nvidia")
             # CRITICAL: Safeguard prevents feeding Google native tokens into OpenAI pipeline
             if candidate and not candidate.startswith("AIzaSy"):
                  ak = candidate
                  
        if ak: self.llm_client.set_api_key(ak)
        
        # 4. Restore Last Selected Model & UI States
        mid = str(settings.value("current_model_id", "")).strip()
        # Explicitly filter out null cast strings and empty variants
        if mid and mid.lower() != "none" and mid != "":
            # MASTER GATE SEAL: Confirm model ID actually exists in current ecosystem manifest
            # Prevents rogue keys from re-enabling chat blindly without actual available model support.
            valid = False
            try:
                from logic.model_io import load_all_models
                for m in load_all_models():
                    if m.get('id') == mid:
                        valid = True
                        break
            except: pass

            if valid:
                self.llm_client.set_model(mid)
                self.chat_view.update_model_ui(mid)
                self.chat_view.set_chat_enabled(True)
            else:
                # Manifest inconsistency detected! Zero cached memory to guarantee security.
                get_app_settings().remove("current_model_id")
                get_app_settings().sync()
                self.chat_view.set_chat_enabled(False)
        else:
            self.chat_view.set_chat_enabled(False)

        self.theme_manager.refresh_auth_button_style()
        
        # 5. Defer restoring splitter handles to ensure layouts are fully computed first
        QTimer.singleShot(100, self.restore_splitter_states)

    def restore_splitter_states(self):
        settings = get_app_settings()
        if hasattr(self, 'chat_view') and self.chat_view:
            s = self.chat_view.findChild(QSplitter, "main_splitter")
            state = settings.value("ui/main_splitter_state")
            if s and state:
                try: s.restoreState(state)
                except Exception: pass
        if hasattr(self, 'arena_view') and self.arena_view:
            s = self.arena_view.findChild(QSplitter, "arena_splitter")
            state = settings.value("ui/arena_splitter_state")
            if s and state:
                try: s.restoreState(state)
                except Exception: pass

        # Fire persistent system tray icon if presence of active authentication is confirmed
        if self.llm_client.has_api_key(): 
             self.tray_icon.show()

    def handle_auth_button(self):
        if self.llm_client.is_globally_authenticated(): self.logout()
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
        # Secure Comprehensive User Cleanout
        try:
            # 1. Wipe the global legacy fallback token (often the culprit in phantom restarts)
            try: keyring.delete_password("LLMChatApp", "api_key")
            except: pass
            
            # 2. Build composite list of all known ecosystem identifiers
            providers = ["nvidia", "google", "groq", "openai", "lmstudio", "ollama"]
            
            # Dynamic Load from Config to guarantee 100% capture rate
            from utils.path_utils import get_resource_path
            import json
            try:
                conf_path = get_resource_path("resources/api_providers.json")
                with open(conf_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    providers.extend([p.get("id") for p in data.get("providers", []) if p.get("id")])
            except: pass
            
            # Dynamic Load from Custom User Storage
            from utils.storage_config import StorageManager
            try:
                root = StorageManager.get_instance().get_storage_root()
                custom_file = root / "custom_providers.json"
                if custom_file.exists():
                    with open(custom_file, 'r', encoding='utf-8') as f:
                        c_data = json.load(f)
                        providers.extend([p.get("id") for p in c_data.get("providers", []) if p.get("id")])
            except: pass

            # 3. Execute full sweep across all distinct vault slots
            for p_id in set(providers):
                try: keyring.delete_password("LLMChatApp", f"api_key_{p_id}")
                except: pass

        except Exception as e:
            print(f"Logout partial warning (non-critical): {e}")
            
        get_app_settings().remove("current_model_id")
        get_app_settings().remove("active_provider_id")
        get_app_settings().sync() # ABSOLUTE SEAL: Force total hardware commit of memory wiping to disk immediately
        self.llm_client.clear_keys()
        self.chat_view.clear_chat()
        self.chat_view.set_chat_enabled(False)
        self.theme_manager.refresh_auth_button_style()
        self.tray_icon.hide()
        success = self.open_settings()
        if not success:
             QTimer.singleShot(0, QApplication.instance().quit)

    def edit_system_instructions(self):
        from ui.system_prompt_manager import SystemPromptManagerClass
        SystemPromptManagerClass(self).exec()
        self.chat_view.add_system_message("Instruction Library updated.")

    def show_model_manager(self):
        from ui.model_manager import ModelManagerDialog
        ModelManagerDialog(theme=self.theme_manager.current_theme, parent=self).exec()

    def show_storage_manager(self):
        """Launch UI to pivot the underlying app data storage directories"""
        from ui.storage_manager_dialog import StorageManagerDialog
        dialog = StorageManagerDialog(theme=self.theme_manager.current_theme, parent=self)
        dialog.exec()

    def open_storage_location(self):
        """Direct OS trigger to pop open active filesystem database root"""
        from utils.storage_config import StorageManager
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        root = StorageManager.get_instance().get_storage_root()
        if root.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))

    def show_gen_settings(self):
        """Restored from baseline: Opens the Smart Generation Parameters dialog."""
        from ui.gen_settings_dialog import GenSettingsDialog
        dialog = GenSettingsDialog(None)
        if dialog.exec():
            self.chat_view.add_system_message("✅ Generation parameters updated.")

    def show_update_log(self):
        """Restored from baseline: Access real-time engine logging stream"""
        from ui.log_viewer import LogViewerDialog
        dialog = LogViewerDialog(self)
        dialog.exec()

    def clear_update_log(self):
        """Restored from baseline: Hard reset of runtime update datasets"""
        from PySide6.QtWidgets import QMessageBox
        from workers.update_logger import get_logger
        reply = QMessageBox.question(
            self,
            "Clear Log",
            "Are you sure you want to clear all update logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            logger = get_logger()
            logger.clear()
            self.chat_view.add_system_message("🗑️ Update logs purged successfully.")

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
        
        if hasattr(self, 'local_detector') and self.local_detector.isRunning():
            self.local_detector.terminate()
            self.local_detector.wait()
        
        # Stop any active dual workers in arena just in case
        if hasattr(self, 'arena_view'):
            self.arena_view.stop_duel()

        # Persist Splitter sizes across sessions
        settings = get_app_settings()
        if hasattr(self, 'chat_view') and self.chat_view:
            s = self.chat_view.findChild(QSplitter, "main_splitter")
            if s: settings.setValue("ui/main_splitter_state", s.saveState())
        if hasattr(self, 'arena_view') and self.arena_view:
            s = self.arena_view.findChild(QSplitter, "arena_splitter")
            if s: settings.setValue("ui/arena_splitter_state", s.saveState())

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

    def showEvent(self, event):
        super().showEvent(event)
        
        # 1. Guarantee layout restoration runs after initial container geometries are fully computed
        QTimer.singleShot(50, self.restore_splitter_states)

        

    def closeEvent(self, event):
        # Simply minimize to tray or quit safely
        self.quit_app()
        event.accept()
    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            is_maximized = self.windowState() & Qt.WindowState.WindowMaximized
            is_fullscreen = self.windowState() & Qt.WindowState.WindowFullScreen
            if not is_maximized and not is_fullscreen:
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
