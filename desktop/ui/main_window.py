# ui/main_window.py
# Shell Controller for Modular Platform Architecture

import sys
import os
import keyring
from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox, QSystemTrayIcon, QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QSplitter, QTableWidgetItem
from PySide6.QtCore import QTimer, Qt, QSettings, QEvent
from PySide6.QtGui import QIcon, QPixmap, QAction, QTextBlockUserData, QActionGroup
from PySide6.QtUiTools import QUiLoader

from server.logic.llm_client import LLMClient
from server.logic.api_manager import ApiManager
from server.logic.formatter import MessageFormatter
from desktop.ui.theme_manager import ThemeManager
from server.workers.connection_worker import ConnectionWorker
from server.workers.local_model_detector import LocalModelDetector
from server.utils.path_utils import get_resource_path, get_app_settings
from desktop.ui.shared_widgets import set_app_icon
from web.app import SaaSServer
from web.core.config_manager import SaaSConfigManager

# Import child modules
from desktop.ui.chat_view import ChatViewWidget
from desktop.ui.arena_view import ArenaViewWidget
from desktop.ui.agent_hub_view import AgentHubViewWidget

# Shared Data Classes used by view internals
from desktop.ui.shared_widgets import MessageData, ChatDisplay

class MainWindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Initializing Main Window Host Shell...")
        self.setWindowTitle("Synora Studio v9.0")
        
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

        # Instantiate Views dynamically!
        self.chat_view = ChatViewWidget(self, self.llm_client, self.theme_manager, self.formatter)
        self.arena_view = ArenaViewWidget(self, self.llm_client, self.theme_manager, self.formatter)
        self.agent_hub_view = AgentHubViewWidget(self)
        
        # Instantiate and auto-start SaaS Server if configured
        self.saas_server = SaaSServer()
        self.saas_server.api_manager_action.connect(self.handle_saas_api_action)
        self.settings_manager = SaaSConfigManager()
        
        # Push them into our master stack!
        self.ui.main_stack.addWidget(self.chat_view)
        self.ui.main_stack.addWidget(self.arena_view)
        self.ui.main_stack.addWidget(self.agent_hub_view)
        
        # Default to Chat Mode on launch
        self.ui.main_stack.setCurrentWidget(self.chat_view)
        # System Setup
        self.setup_menu_bar()
        self.setup_tray()
        self.load_settings()
        
        # Apply SaaS configuration state
        self.apply_saas_state()
        
        print("Shell ready. Launching in default View Mode.")

    def start_services(self):
        """Starts background workers only after authentication is confirmed."""
        try:
            from server.logic.services import ServiceRegistry
            ServiceRegistry.initialize_all()
        except Exception as e:
            print(f"[Services] Failed to initialize: {e}")

        # Setup Shared Connection Worker
        self.connection_worker = ConnectionWorker(parent=self)
        self.connection_worker.status_changed.connect(self.on_connection_status_changed)
        self.connection_worker.start()

        # Fire non-blocking Local Model Auto-Detection Sweep (Ollama/LM Studio)
        self.local_detector = LocalModelDetector(parent=self)
        self.local_detector.detection_completed.connect(self.on_local_models_detected)
        self.local_detector.start()


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

    def show_agent_hub_mode(self):
        self.ui.main_stack.setCurrentWidget(self.agent_hub_view)
        self.agent_hub_view.refresh_ui()
        self.statusBar().showMessage("Switched to Agent Hub", 2000)

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

    def on_api_status_changed(self, success, message):
        """Callback from ApiManager to update UI status."""
        if success or message:
            self.chat_view.add_system_message(f"🌐 Universal API Server: {message}")
            
        if hasattr(self, 'api_server_action'):
            is_running = False
            if hasattr(self, 'api_manager') and self.api_manager.api_server:
                is_running = self.api_manager.api_server.running
            self.api_server_action.setChecked(is_running)

    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # Master View Switcher
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Conversation", self.chat_view.start_new_chat, "Ctrl+N")
        file_menu.addAction("Save Conversation", self.chat_view.auto_save_current_chat, "Ctrl+S")
        file_menu.addSeparator()
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
        settings_menu.addAction("🔐 Credential Manager", self.open_credential_manager)
        settings_menu.addAction("📦 Model Manager", self.show_model_manager)
        settings_menu.addAction("✏️ System Instructions", self.edit_system_instructions, "Ctrl+I")
        settings_menu.addAction("⚙️ Generation Parameters", self.show_gen_settings)
        settings_menu.addAction("📡 SaaS Gateway Configuration", self.show_saas_settings)
        settings_menu.addSeparator()
        settings_menu.addAction("📂 Open Data Folder", self.open_storage_location)
        settings_menu.addSeparator()
        settings_menu.addAction("🛠️ Companion Operation", self.launch_migration_companion)

        # Log menu
        log_menu = menubar.addMenu("Log")
        log_menu.addAction("📋 View Update Log", self.show_update_log)
        log_menu.addAction("🗑️ Clear Log", self.clear_update_log)

        # Tools Menu
        tools_menu = menubar.addMenu("Tools")
        
        self.saas_console_action = tools_menu.addAction("🖥️ Open SaaS Web Console")
        self.saas_console_action.triggered.connect(self.open_saas_web_console)
        self.saas_console_action.setEnabled(False)
        
        self.api_server_action = tools_menu.addAction("🌐 Universal API Server")
        self.api_server_action.setCheckable(True)
        self.api_server_action.triggered.connect(self.api_manager.toggle_api_server)
        
        tools_menu.addSeparator()
        self.health_action = tools_menu.addAction("📊 System Health & Telemetry")
        self.health_action.triggered.connect(self.show_system_health)
        
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("📖 Readme", self.show_readme)
        help_menu.addAction("📜 License", self.show_license)
        help_menu.addAction("📡 API Documentation", self.api_doc)
        help_menu.addAction("📟 Headless Engine Guide", self.show_headless_guide)
        help_menu.addAction("🔌 IDE Integration Guide", self.show_ide_integration)
        help_menu.addAction("🛡️ Security Policy", self.show_security_policy)
        help_menu.addSeparator()
        help_menu.addAction("📦 Download VS Code Extension", self.download_vscode_extension)
        help_menu.addAction("🧩 Download JetBrains Plugin", self.download_jetbrains_plugin)
        help_menu.addSeparator()
        help_menu.addAction("ℹ️ About", self.show_about)

    def load_settings(self):
        settings = get_app_settings()
        
        # 1. Apply Global Theme state
        self.theme_manager.apply_theme(settings.value("theme", "light"))
        
        # 2. Authentication Check: Stop if no active session
        active_p = settings.value("active_provider_id")
        if not active_p:
             return
             
        # 3. Restore Credentials ONLY for active session
        from server.utils.security_utils import decrypt_data, SESSION_MASTER_PASSWORD
        gk = keyring.get_password("LLMChatApp", "api_key_google")
        if gk:
            gk = decrypt_data(gk, SESSION_MASTER_PASSWORD)
            self.llm_client.set_google_api_key(gk)
        
        # Fetch targeted localized endpoint
        b_url = settings.value(f"url_{active_p}") or settings.value("base_url")
        # Filter google endpoints to avoid OpenAI client path contamination
        if b_url and active_p != "google" and "google" not in b_url: 
             self.llm_client.set_base_url(b_url)
             
        # Fetch targeted API credential from isolated slot
        ak = None
        if active_p != "google":
             ak = keyring.get_password("LLMChatApp", f"api_key_{active_p}")
                   
        if ak:
            ak = decrypt_data(ak, SESSION_MASTER_PASSWORD)
            self.llm_client.set_api_key(ak)
        
        # 4. Restore Last Selected Model & UI States
        mid = str(settings.value("current_model_id", "")).strip()
        from server.logic.model_io import load_all_models
        all_models = load_all_models()
        
        # MASTER GATE SEAL: Confirm model ID actually exists in current ecosystem manifest
        valid = False
        if mid and mid.lower() != "none" and mid != "":
            for m in all_models:
                if m.get('id') == mid:
                    valid = True
                    break
        
        # Auto-recovery: If no valid model, pick the first one for the active provider
        if not valid:
            for m in all_models:
                prov = m.get('provider')
                if prov and str(prov).lower() == str(active_p).lower():
                    mid = m.get('id')
                    valid = True
                    settings.setValue("current_model_id", mid)
                    break

        if valid:
            self.llm_client.set_model(mid)
            self.chat_view.update_model_ui(mid)
            self.chat_view.set_chat_enabled(True)
        else:
            self.chat_view.set_chat_enabled(False)

        self.theme_manager.refresh_auth_button_style()
        
        # 5. Defer restoring splitter handles to ensure layouts are fully computed first
        QTimer.singleShot(100, self.restore_splitter_states)

    def restore_splitter_states(self):
        """Delegates layout restoration to active views."""
        if hasattr(self, 'chat_view'):
            self.chat_view.load_layout_settings()
        if hasattr(self, 'arena_view'):
            self.arena_view.load_layout_settings()

        # Fire persistent system tray icon if presence of active authentication is confirmed
        if self.llm_client.has_api_key(): 
             self.tray_icon.show()

    def handle_auth_button(self):
        self.open_settings()

    def switch_ecosystem(self):
        """Spawns the Ecosystem selector to swap dynamic AI providers cleanly."""
        self.open_settings()

    def open_settings(self):
        from desktop.ui.ecosystem_selector import EcosystemSelectorClass
        dlg = EcosystemSelectorClass(parent=self)
        # Only reload if the user actually clicked Save/Login
        if dlg.exec():
            self.load_settings()
            return self.llm_client.is_globally_authenticated()
        return False

    def show_model_popup(self):
        from desktop.ui.model_popup import ModelPopupClass
        from server.logic.model_io import load_all_models
        mid = get_app_settings().value("current_model_id", "")
        d = ModelPopupClass(current_model_id=mid, parent=self)
        if d.exec():
            sid = d.get_selected_model_id()
            if sid:
                # 1. Identify Provider of the newly selected model
                models = load_all_models()
                new_provider = "nvidia" # Default fallback
                dev_name = "Unknown"
                model_name = sid
                for m in models:
                    if m.get('id') == sid:
                        new_provider = m.get('provider', 'nvidia')
                        dev_name = m.get('developer', 'Unknown')
                        model_name = m.get('name', sid)
                        break
                
                # 2. Persist the provider shift to settings to ensure correct key hydration on next reload
                settings = get_app_settings()
                settings.setValue("active_provider_id", new_provider)
                
                # 3. Update Client and UI
                self.llm_client.set_model(sid)
                self.chat_view.update_model_ui(sid)
                self.chat_view.set_chat_enabled(True)
                
                # 4. Trigger a settings reload to hydrate the newly active provider's key
                self.load_settings()
                self.chat_view.add_system_message(f"🔄 <b>Ecosystem:</b> {new_provider.upper()} | <b>Developer:</b> {dev_name} | <b>Model:</b> {model_name}", allow_html=True)



    def open_credential_manager(self):
        from desktop.ui.credential_manager import show_settings_hub
        show_settings_hub(parent=self, theme_manager=self.theme_manager)
        self.load_settings()
        if hasattr(self, 'chat_view'):
            self.chat_view.update_model_ui(self.llm_client.current_model)

    def edit_system_instructions(self):
        from desktop.ui.system_prompt_manager import SystemPromptManagerClass
        SystemPromptManagerClass(self).exec()
        self.chat_view.add_system_message("Instruction Library updated.")

    def show_model_manager(self):
        from desktop.ui.model_manager import ModelManagerDialog
        if ModelManagerDialog._fetch_in_progress:
            QMessageBox.warning(
                self,
                "Fetch in Progress",
                "Model fetch is already running in the background.\n\n"
                "Please wait for it to complete before opening Model Manager."
            )
            return
        # Phase 2: Pass theme_manager for visual synchronization
        self.model_manager_dialog = ModelManagerDialog(
            theme=self.theme_manager.current_theme, 
            parent=self, 
            theme_manager=self.theme_manager
        )
        self.model_manager_dialog.exec()


    def open_storage_location(self):
        """Direct OS trigger to pop open active filesystem database root"""
        from server.utils.storage_config import StorageManager
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        root = StorageManager.get_instance().get_storage_root()
        if root.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))

    def show_gen_settings(self):
        """Restored from baseline: Opens the Smart Generation Parameters dialog."""
        from desktop.ui.gen_settings_dialog import GenSettingsDialog
        dialog = GenSettingsDialog(self)
        if dialog.exec():
            self.chat_view.add_system_message("✅ Generation parameters updated.")

    def launch_migration_companion(self):
        """
        Phase 10.3: Launches the standalone Companion Operation as a detached subprocess
        and gracefully exits the main application to release database locks.
        """
        reply = QMessageBox.question(
            self,
            "Launch Companion Operation",
            "This will close the Synora Studio to release all database locks, "
            "then launch the standalone Companion Operation utility.\n\n"
            "⚠️ All unsaved conversations will be auto-saved before closing.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # Auto-save active conversation before shutdown
        try:
            self.chat_view.auto_save_current_chat()
        except Exception:
            pass

        import subprocess
        if getattr(sys, 'frozen', False):
            # Frozen environment (Production .exe)
            exe_dir = os.path.dirname(sys.executable)
            companion_name = "Companion Operation.exe" if sys.platform == "win32" else "Companion Operation"
            companion_bin = os.path.join(exe_dir, companion_name)
            if not os.path.exists(companion_bin):
                QMessageBox.critical(
                    self, "Not Found",
                    f"Companion Operation executable not found at:\n{companion_bin}\n\n"
                    "Ensure it was compiled alongside the main application."
                )
                return
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            subprocess.Popen([companion_bin], creationflags=creation_flags)
        else:
            # Loose script environment (Development)
            companion_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "operator_tools", "companion", "companion_operation.py")
            subprocess.Popen([sys.executable, companion_script])

        # Gracefully terminate main app to release Turso/libSQL handles
        print("[Companion Operation] Companion launched. Shutting down main application...")
        QApplication.instance().quit()

    def show_saas_settings(self):
        """Phase 7: Opens the SaaS architecture configuration dialog."""
        from desktop.ui.saas_settings_dialog import SaaSSettingsDialogClass
        dialog = SaaSSettingsDialogClass(parent=self)
        if dialog.exec():
            # Refresh server state based on new config
            self.apply_saas_state()

    def show_system_health(self):
        """Opens the standalone System Health & Telemetry dialog."""
        from desktop.ui.system_health import SystemHealthDialog
        dialog = SystemHealthDialog(parent=self)
        dialog.exec()

    def handle_saas_api_action(self, action: str):
        """Processes cross-thread actions commanded by the SaaS Admin Interface."""
        if action == "stop":
            self.api_manager.stop_api_server()
            self.chat_view.add_system_message("🔴 Local API Server forcefully disabled via SaaS Admin.")
        elif action == "restart":
            self.api_manager.stop_api_server()
            self.api_manager.start_api_server()
            self.chat_view.add_system_message("🌐 Local API Server restarted via SaaS Admin.")

    def apply_saas_state(self):
        """Evaluates SaaS config and starts/stops the background daemon."""
        cfg = SaaSConfigManager()
        enabled = cfg.get_bool("NETWORK", "enabled", True)
        host = cfg.get_str("NETWORK", "host", "127.0.0.1")
        port = cfg.get_int("NETWORK", "port", 8080)
        
        if not enabled:
            if self.saas_server.running:
                self.saas_server.stop()
                if hasattr(self, 'chat_view') and self.chat_view:
                    self.chat_view.add_system_message("🔴 SaaS Gateway disabled.")
            if hasattr(self, 'saas_console_action'):
                self.saas_console_action.setEnabled(False)
            return

        # Restart server if host/port changed or if not running
        if self.saas_server.running:
            if self.saas_server.host != host or self.saas_server.port != port:
                self.saas_server.stop()
            else:
                if hasattr(self, 'saas_console_action'):
                    self.saas_console_action.setEnabled(True)
                return # Already running on correct bind

        self.saas_server.host = host
        self.saas_server.port = port
        # Persist the computed local URL for UI consumption
        cfg = SaaSConfigManager()
        cfg.set_local_url(host, port)
        success, msg = self.saas_server.start_server()
        
        if hasattr(self, 'saas_console_action'):
            self.saas_console_action.setEnabled(success)
            
        if success:
            alert = f"🟢 SaaS Gateway running at http://{host}:{port}"
        else:
            alert = f"🔴 SaaS Gateway failed to start: {msg}"
            
        if hasattr(self, 'chat_view') and self.chat_view:
            self.chat_view.add_system_message(alert)

    def open_saas_web_console(self):
        """Opens the SaaS gateway portal in the user's default browser."""
        if hasattr(self, 'saas_server') and self.saas_server.running:
            import webbrowser
            url = f"http://{self.saas_server.host}:{self.saas_server.port}"
            webbrowser.open(url)

    def show_about(self):
        from server.utils.constants import APP_VERSION
        border_color = "#3c3c3c" if self.theme_manager.current_theme == "dark" else "#e0e0e0"
        
        text = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <h2 style="color: #0078d4; margin-bottom: 5px;">Synora Studio</h2>
            <p><b>Version:</b> {APP_VERSION}<br>
            <b>Lead Architect:</b> Arean Narrayan</p>
            
            <hr style="border: 1px solid {border_color}; margin: 10px 0;">
            
            <p>A premium, high-performance desktop workstation engineered to serve as a 
            universal, ecosystem-agnostic gateway into state-of-the-art Large Language Models.</p>
            
            <p><b>Key Technologies:</b></p>
            <ul>
                <li>🚀 Infinite Context via <b>Adaptive Memory Compression</b></li>
                <li>🧬 Hybrid RAG Persistence (<b>NumPy</b> & <b>Qdrant</b> Vector Database)</li>
                <li>🛠️ Isolated <b>Interactive Execution Sandbox</b></li>
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
        from desktop.ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="Readme", 
            file_names=["README.md", "README.txt", "README"], 
            is_markdown=True, 
            size=(750, 600), 
            parent=self
        )
        dialog.exec()

    def show_license(self):
        from desktop.ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="License", 
            file_names=["LICENSE", "LICENSE.txt", "License"], 
            is_markdown=False, 
            size=(630, 410), 
            parent=self
        )
        dialog.exec()

    def api_doc(self):
        from desktop.ui.file_viewer import FileViewerDialog
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
        self.tray_icon.setToolTip("Synora Studio")
        
        m = QMenu()
        m.addAction("Restore", self.show_and_activate)
        m.addSeparator()
        m.addAction("Quit", self.quit_app)
        self.tray_icon.setContextMenu(m)
        
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_and_activate()

    def show_and_activate(self):
        self.showNormal()
        self.showMaximized()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        # 0. Shutdown service layer
        if hasattr(self, 'telemetry_timer'):
            self.telemetry_timer.stop()
        try:
            from server.logic.services import ServiceRegistry
            ServiceRegistry.shutdown_all()
        except Exception:
            pass

        # 1. Stop background API server if running
        if hasattr(self, 'api_manager'):
            self.api_manager.stop_api_server()
            
        # 1.5 Stop background SaaS Server
        if hasattr(self, 'saas_server') and self.saas_server.running:
            self.saas_server.stop()

        # 2. Graceful Thread Teardown
        if hasattr(self, 'connection_worker'):
            self.connection_worker.requestInterruption()
            self.connection_worker.quit()
            self.connection_worker.wait()
        
        if hasattr(self, 'local_detector') and self.local_detector.isRunning():
            self.local_detector.requestInterruption()
            self.local_detector.quit()
            self.local_detector.wait()
        
        # 3. Stop any active dual workers in arena just in case
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
        # Ensure telemetry timer is terminated
        if hasattr(self, 'telemetry_timer'):
            self.telemetry_timer.stop()
        print("[Shutdown] Cleaning up services...")
        try:
            from server.logic.services import ServiceRegistry
            ServiceRegistry.shutdown_all()
        except Exception:
            pass
        
        # 1. Stop global window-level workers
        if hasattr(self, 'connection_worker'):
            self.connection_worker.requestInterruption()
            self.connection_worker.quit()
            self.connection_worker.wait()
            
        if hasattr(self, 'local_detector') and self.local_detector.isRunning():
            self.local_detector.requestInterruption()
            self.local_detector.quit()
            self.local_detector.wait()
            
        # 1.5 Stop background SaaS Server
        if hasattr(self, 'saas_server') and self.saas_server.running:
            self.saas_server.stop()

        # 2. Stop view-specific workers and save layouts
        if hasattr(self, 'chat_view'):
            self.chat_view.save_layout_settings()
            self.chat_view.shutdown()
        if hasattr(self, 'arena_view'):
            self.arena_view.save_layout_settings()
            
        event.accept()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            is_maximized = self.windowState() & Qt.WindowState.WindowMaximized
            is_fullscreen = self.windowState() & Qt.WindowState.WindowFullScreen
            if not is_maximized and not is_fullscreen:
                QTimer.singleShot(0, self.showMaximized)
        super().changeEvent(event)

    def show_ide_integration(self):
        from desktop.ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="IDE Integration Guide",
            file_names=["IDE_INTEGRATION.md"],
            is_markdown=True,
            size=(750, 600),
            parent=self
        )
        dialog.exec()

    def show_security_policy(self):
        from desktop.ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="Security & Privacy Policy",
            file_names=["SECURITY.md", "SECURITY.txt", "SECURITY"],
            is_markdown=True,
            size=(750, 600),
            parent=self
        )
        dialog.exec()

    def show_headless_guide(self):
        from desktop.ui.file_viewer import FileViewerDialog
        dialog = FileViewerDialog(
            title="Headless Engine Guide",
            file_names=["HEADLESS_GUIDE.md"],
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
                "The extension folder is now open.\n\nInstall:\n1. VS Code → Extensions → ... → Install from VSIX\n2. Select vscode-llm-chat-2.0.0.vsix"
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
                "The extension folder is now open.\n\nInstall:\n1. Settings → Plugins → ⚙️ → Install Plugin from Disk\n2. Select jetbrains-llm-chat-2.0.0.zip"
            )
        else:
            QMessageBox.warning(self, "Folder Not Found", "extension folder not found")

    def show_update_log(self):
        """Phase 1: Restored premium Log Viewer with filter logic and .ui integration."""
        from desktop.ui.log_viewer import LogViewerDialog
        dialog = LogViewerDialog(parent=self)
        dialog.exec()

    def clear_update_log(self):
        """Clears the persistent diagnostic log."""
        from server.workers.update_logger import get_logger
        if QMessageBox.question(self, "Clear Logs", "Are you sure you want to delete all diagnostic logs?") == QMessageBox.Yes:
            get_logger().clear()
            self.chat_view.add_system_message("🗑️ Update logs purged successfully.")

