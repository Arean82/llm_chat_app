# ui/main_window.py
# Main application window for LLM Chat App

import sys
import os
from pathlib import Path
import re
import base64
import socket 

import time
import json
import keyring

from logic.api_server import APIServer
from utils.constants import CONNECTION_CHECK_INTERVAL_CONNECTED_MS, CONNECTION_CHECK_INTERVAL_DISCONNECTED_MS, RESPONSE_BUFFER_CHARS
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox, QFileDialog, QLabel, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget, QApplication, QListWidgetItem, QAbstractItemView
from PySide6.QtCore import QEvent, QTimer, Qt, QSettings, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QTextBlockUserData, QTextCursor
from PySide6.QtUiTools import QUiLoader

from logic.llm_client import LLMClient
from logic.chat_worker import ChatWorker
from logic.conversation_manager import ConversationManager
from workers.connection_worker import ConnectionWorker
from logic.api_manager import ApiManager
from logic.formatter import MessageFormatter

from utils.path_utils import get_resource_path
from utils.model_config import get_context_limit

from PySide6.QtWidgets import QSizePolicy 

from ui.system_prompt_manager import SystemPromptManagerClass

from utils.helpers import set_app_icon
from ui.theme_manager import ThemeManager

class MessageData(QTextBlockUserData):
    """Helper class to store the raw markdown text inside a text block."""
    def __init__(self, text):
        super().__init__()
        self.text = text

class ChatDisplay(QTextEdit):
    """Custom QTextEdit that handles clicking on the 'Copy' link."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Allow links to be clicked
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        # Ensure we track mouse movement
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        # Check what is under the mouse cursor
        cursor = self.cursorForPosition(event.pos())
        
        # If the character under the mouse is a link (anchor)
        if cursor.charFormat().isAnchor():
            # Force the Hand Cursor
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # Revert to standard text cursor (IBeam)
            self.viewport().unsetCursor()
        
        # Call parent to keep text selection working
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        cursor = self.cursorForPosition(event.pos())
        char_format = cursor.charFormat()
        
        if char_format.isAnchor():
            href = char_format.anchorHref()
            
            # --- Case 1: Copy Raw (Whole Message) ---
            if href == "copy":
                self.copy_message_content(cursor)
            
            # --- Case 2: Copy Code Block ---
            elif href.startswith("copy_code:"):
                self.copy_code_content(href)
                
            # --- Case 3: Regenerate Response ---
            elif href == "regenerate":
                # FIX: Use self.window() to get the MainWindowClass instance
                main_window = self.window()
                if main_window:
                    main_window.regenerate_last_response()

    def copy_message_content(self, cursor):
        block = cursor.block()
        data = block.userData()
        if not data:
            prev_block = block.previous()
            if prev_block.isValid():
                data = prev_block.userData()
        
        if data and hasattr(data, 'text'):
            clipboard = QApplication.clipboard()
            clipboard.setText(data.text)

    def copy_code_content(self, href):
        # Extract the base64 encoded code from the href
        try:
            # href format: "copy_code:BASE64_STRING"
            encoded_code = href.split(":", 1)[1]
            code_text = base64.b64decode(encoded_code).decode('utf-8')
            
            clipboard = QApplication.clipboard()
            clipboard.setText(code_text)
            print(f"Copied Code Block ({len(code_text)} chars)")
        except Exception as e:
            print(f"Error copying code: {e}")

class MainWindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        
        print("MainWindowClass.__init__ starting...")

        self.theme_manager = ThemeManager(self)
        self.api_manager = ApiManager(self)
        self.formatter = MessageFormatter(self.theme_manager)
    
        # STATE VARIABLES
        self.llm_client = LLMClient()
        self.conversation_manager = ConversationManager()
        self.chat_history = []
        self.current_worker = None
        self.current_response_text = ""
        self.response_start_time = None
        self.is_generating = False
        self.stream_start_position = None
        self.attached_files = []
        self.total_tokens = 0
        self.current_conv_id = None
        self.chat_html_history = [] # Rendered HTML chunks for caching
    
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/main_window.ui")
        
        if not ui_file.exists():
            self.setup_fallback_ui()
            return
    
        self.setWindowTitle("LLM Chat Application")
    
        self.ui = loader.load(str(ui_file))
        if self.ui is None:
            self.setup_fallback_ui()
            return
        
        self.setCentralWidget(self.ui)
    
        # Apply Window Icon
        set_app_icon(self)
        
        # System Tray
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(str(get_resource_path("resources/app_icon.png"))))

        # Tray menu
        tray_menu = QMenu()
        minimize_action = tray_menu.addAction("Minimize to Tray")
        minimize_action.triggered.connect(self.hide_to_tray)
        restore_action = tray_menu.addAction("Restore")
        restore_action.triggered.connect(self.restore_from_tray)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # DEFERRED SHOW: Do not call self.tray_icon.show() here.
        # It will be displayed only after user login state is validated.

        # Apply Header Logo
        self.setup_header_logo() 
    
        # Swap the standard chat_display with our custom ChatDisplay
        # Note: In the new design, chat_display is inside chat_display_panel layout
        old_chat = self.ui.chat_display
        self.chat_display = ChatDisplay()
        
        # Find the layout that holds the chat display
        display_layout = self.ui.chat_display_layout
        display_layout.replaceWidget(old_chat, self.chat_display)
        
        old_chat.setParent(None)
        old_chat.deleteLater()
    
        # WIDGETS - MOVED UP BEFORE load_settings
        self.input_field = self.ui.input_field
        self.input_field.installEventFilter(self)

        self.send_btn = self.ui.send_btn
        self.send_btn.setToolTip("Send message (Enter)")
        self.input_field.setToolTip("Type your message. Press Enter to send, Shift+Enter for new line")

        self.model_btn = self.ui.model_btn
        self.model_desc_label = self.ui.model_desc_label
        self.auth_btn = self.ui.auth_btn
        self.upload_btn = self.ui.upload_btn 
        self.theme_toggle_btn = self.ui.theme_toggle_btn
        self.connection_status_btn = self.ui.connection_status_btn 
    
        # Connection Status Monitor (Now in a background thread)
        self.is_connected = True
        self.connection_worker = ConnectionWorker()
        self.connection_worker.status_changed.connect(self.on_connection_status_changed)
        self.connection_worker.start()
    
        # SETUP
        self.setup_menu_bar()   
        self.setup_connections()
        
        # SIDEBAR CONNECTIONS
        self.ui.new_chat_btn.clicked.connect(self.start_new_chat)
        self.ui.delete_all_btn.clicked.connect(self.clear_all_history)
        self.ui.chat_history_list.itemClicked.connect(self.load_selected_history)
        
        # Context menu for individual delete
        self.ui.chat_history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.chat_history_list.customContextMenuRequested.connect(self.show_history_context_menu)
        self.ui.chat_history_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.refresh_history_list()
        
        # LOAD SETTINGS LAST - AFTER everything is initialized
        self.load_settings()
        
        print("MainWindowClass.__init__ completed")
        
    def setup_fallback_ui(self):
        print("Setting up fallback UI...")
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        label = QLabel("UI file failed to load.")
        layout.addWidget(label)
        self.setCentralWidget(central_widget)

    def setup_header_logo(self):
        """Adds the application logo to the top bar via Python."""
        # 1. Create the Label widget
        self.logo_label = QLabel(self.ui.top_bar)
        self.logo_label.setFixedSize(32, 32)       # Set size (32x32 pixels)
        self.logo_label.setScaledContents(True)    # Ensure image fills the box
        self.logo_label.setToolTip("LLM Chat App")
        
        # 2. Load the icon image
        icon_path = get_resource_path("resources/app_icon.png")
        pixmap = QPixmap(icon_path)
        
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap)       # Set the image
        else:
            # Fallback if image is missing (shows an emoji instead)
            self.logo_label.setText("🚀")
            self.logo_label.setStyleSheet("font-size: 20px; padding-left: 5px;")

        # 3. Insert the label into the top bar layout
        # index 0 means it goes to the very left, before all other buttons
        self.ui.top_bar_layout.insertWidget(0, self.logo_label)

    # ---------------------------------------------------------
    # THEME SYSTEM
    # ---------------------------------------------------------    # THEME DELEGATION (Reduces MainWindow complexity)
    def apply_theme(self, theme: str):
        self.theme_manager.apply_theme(theme)

    def toggle_theme(self):
        self.theme_manager.toggle_theme()

    def refresh_auth_button_style(self):
        self.theme_manager.refresh_auth_button_style()

    def get_system_message_color(self):
        return self.theme_manager.get_system_message_color()

    def get_terminate_color(self):
        return self.theme_manager.get_terminate_color()

    def get_thinking_color(self):
        return self.theme_manager.get_thinking_color()

    def get_code_block_style(self):
        return self.theme_manager.get_code_block_style()

    def get_code_text_style(self):
        return self.theme_manager.get_code_text_style()

    def get_metrics_border_color(self):
        return self.theme_manager.get_metrics_border_color()

    def get_copy_button_html(self):
        return self.theme_manager.get_copy_button_html()

    # ---------------------------------------------------------
    # SYSTEM TRAY
    # ---------------------------------------------------------    

    def hide_to_tray(self):
        self.hide()
        self.tray_icon.showMessage(
            "LLM Chat App",
            "Application minimized to system tray. API server still running.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def restore_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_from_tray()

    def quit_app(self):
        self._force_exit = True
        self.close()

    def perform_graceful_cleanup(self):
        """Consolidated logic to shut down all background processes safely."""
        self.tray_icon.hide()
        
        if hasattr(self, 'api_manager'):
            try:
                self.api_manager.stop_api_server()
            except Exception:
                pass
            
        if hasattr(self, 'connection_worker'):
            self.connection_worker.stop()
            self.connection_worker.requestInterruption()
            self.connection_worker.wait()
        
        # Stop any active generation
        if self.is_generating:
            self.stop_generation()

        # Final auto-save to ensure current chat is preserved
        self.auto_save_current_chat()

    def closeEvent(self, event):
        if hasattr(self, '_force_exit') and self._force_exit:
            self.perform_graceful_cleanup()
            event.accept()
            return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("LLM Chat App")
        msg_box.setText("The application can continue running in the system tray.")
        msg_box.setInformativeText("What would you like to do?")

        tray_btn = msg_box.addButton("Minimize to Tray", QMessageBox.ButtonRole.AcceptRole)
        exit_btn = msg_box.addButton("Exit Application", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        tray_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)

        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:pressed {
                background-color: #8e0000;
            }
        """)

        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:pressed {
                background-color: #2c2c2c;
            }
        """)

        msg_box.exec()

        clicked = msg_box.clickedButton()

        if clicked == tray_btn:
            event.ignore()
            self.hide_to_tray()
        elif clicked == exit_btn:
            # --- GRACEFUL TERMINATION LOGIC ---
            self.perform_graceful_cleanup()
            event.accept()
        else:
            event.ignore()

    # ---------------------------------------------------------
    # END THEME SYSTEM
    # ---------------------------------------------------------

    def on_connection_status_changed(self, connected):
        """Callback from background connection worker."""
        if connected != self.is_connected:
            self.is_connected = connected
            self.update_connection_icon()

    def update_connection_icon(self):
        """Updates the globe icon and tooltip based on status."""
        if self.is_connected:
            self.connection_status_btn.setText("🌐")
            self.connection_status_btn.setToolTip("Connected")
        else:
            self.connection_status_btn.setText("🔴")
            self.connection_status_btn.setToolTip("Disconnected - Checking...")

    def force_disconnected_state(self):
        """Immediately force UI to disconnected state (called on API errors)."""
        if self.is_connected:
            self.is_connected = False
            self.update_connection_icon()

    def setup_menu_bar(self):
        """Build menu bar purely in Python"""
        menubar = self.menuBar()

        # File menu with conversation management
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Conversation", self.new_conversation, "Ctrl+N")
        file_menu.addSeparator()
        file_menu.addAction("Save Conversation", self.save_conversation, "Ctrl+S")
        file_menu.addAction("Load Conversation", self.load_conversation, "Ctrl+L")
        file_menu.addAction("Minimize to Tray", self.hide_to_tray, "Ctrl+M")
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.quit_app, "Ctrl+Q")

        # Edit menu with clear chat
        edit_menu = menubar.addMenu("Edit")

        clear_action = edit_menu.addAction("Clear Chat")
        clear_action.triggered.connect(self.clear_chat)
        clear_action.setShortcut("Ctrl+D")

        edit_menu.addSeparator()

        copy_action = edit_menu.addAction("Copy Last Response")
        copy_action.triggered.connect(self.copy_last_response)
        copy_action.setShortcut("Ctrl+Shift+C")

        # Settings menu with Model Manager
        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("📦 Model Manager", self.show_model_manager)
        settings_menu.addAction("✏️ System Instructions", self.edit_system_instructions, "Ctrl+I")
        settings_menu.addAction("⚙️ Generation Parameters", self.show_gen_settings)
        settings_menu.addSeparator()
        settings_menu.addAction("🗄️ Storage Manager", self.show_storage_manager)
        settings_menu.addAction("📂 Open Data Folder", self.open_storage_location)
        # settings_menu.addAction("🔑 API Key", self.handle_auth_button)

        # Log menu
        log_menu = menubar.addMenu("Log")
        log_menu.addAction("📋 View Update Log", self.show_update_log)
        log_menu.addAction("🗑️ Clear Log", self.clear_update_log)

        # Tools menu:
        tools_menu = menubar.addMenu("Tools")
        self.api_server_action = tools_menu.addAction("🌐 Universal API Server")
        self.api_server_action.triggered.connect(self.api_manager.toggle_api_server)
        self.api_server_action.setCheckable(True)

        # Help menu with placeholder actions
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
        
    def setup_connections(self):
        self.send_btn.clicked.connect(self.handle_send_stop_toggle)
        #self.input_field.returnPressed.connect(self.send_message)
        self.model_btn.clicked.connect(self.show_model_popup)
        self.auth_btn.clicked.connect(self.handle_auth_button)
        self.upload_btn.clicked.connect(self.handle_upload)
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)

    def eventFilter(self, obj, event):
        """
        Intercepts key events for the input field to handle Enter/Shift+Enter.
        """
        # 1. Check if the event is a Key Press happening on the input_field
        if obj == self.input_field and event.type() == event.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            # 2. Check if Enter or Return is pressed
            if key in (Qt.Key_Return, Qt.Key_Enter):
                
                # 3. Check if Shift is held down
                if modifiers == Qt.ShiftModifier:
                    # Case A: Shift+Enter -> Let the text edit handle it (New Line)
                    return False 
                else:
                    # Case B: Enter Only -> Send Message & Stop the new line
                    self.send_message()
                    return True # Return True means "I handled this, don't pass it to the widget"

        # 4. For all other keys/events, use default behavior
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """
        Handle keyboard events.
        - Enter: Send Message
        - Shift+Enter: New Line
        """
        # Check if the focus is on the input field
        if self.input_field.hasFocus():
            
            # Check if Enter or Return key is pressed
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                
                # Check if Shift modifier is held down
                modifiers = event.modifiers()
                if modifiers == Qt.ShiftModifier:
                    # Shift+Enter: Allow default behavior (inserts new line)
                    super().keyPressEvent(event)
                else:
                    # Enter only: Send Message (Prevents new line insertion)
                    self.send_message()
                    return # Stop event from processing further
            
            # Allow Tab to work normally (focus handling)
            else:
                super().keyPressEvent(event)
        
        else:
            # If focus is not on input, handle keys normally
            super().keyPressEvent(event)

    def edit_system_instructions(self):
        """Opens the System Prompt Manager window."""
        dialog = SystemPromptManagerClass(self)
        dialog.exec()
        # Optional: notify user
        self.add_system_message("ℹ️ Instruction Library updated.")
        
    def load_models(self):
        pass

    # API SERVER DELEGATION
    def toggle_api_server(self, checked):
        self.api_manager.toggle_api_server(checked)

    def start_api_server(self):
        self.api_manager.start_api_server()

    def stop_api_server(self):
        self.api_manager.stop_api_server()
    # ---------------------------------------------------------
    # FIRST-RUN LOGIC & POPUP HANDLERS
    # ---------------------------------------------------------

    def load_settings(self):
        settings = QSettings("LLMChatApp", "Settings")
        
        # Securely fetch api_key from system keychain (both providers)
        nvidia_key = keyring.get_password("LLMChatApp", "api_key_nvidia")
        if not nvidia_key:
             nvidia_key = keyring.get_password("LLMChatApp", "api_key") # Legacy fallback
             
        google_key = keyring.get_password("LLMChatApp", "api_key_google")
        
        base_url = settings.value("base_url", "https://integrate.api.nvidia.com/v1")
        model_id = settings.value("current_model_id", "")
        saved_theme = settings.value("theme", "light")
        
        # Apply saved theme FIRST
        self.apply_theme(saved_theme)

        # Inject credentials into the polymorphic facade
        if nvidia_key:
            self.llm_client.set_base_url(base_url)
            self.llm_client.set_api_key(nvidia_key) 
            
        if google_key:
            self.llm_client.set_google_api_key(google_key)

        self.refresh_auth_button_style()
        
        has_model = bool(model_id)
        # A user has permission to chat if AT LEAST ONE active credential exists!
        has_key = bool(nvidia_key) or bool(google_key)
        
        if has_model:
            self.update_model_ui(model_id)
            self.model_btn.setEnabled(True)
            self.llm_client.set_model(model_id)
        else:
            self.model_btn.setText("Select Model ▼")
            self.model_desc_label.setText("")
            self.model_desc_label.setVisible(False)
            self.model_btn.setEnabled(False)
            
        self.set_chat_enabled(has_key and has_model)
        
        # Show tray icon ONLY if we possess credentials
        if has_key:
            self.tray_icon.show()
        else:
            self.tray_icon.hide()
        
    def handle_auth_button(self):
        if self.llm_client.has_api_key():
            self.logout()
        else:
            self.open_settings()

    def open_settings(self):
        from ui.login_dialog import SettingsDialogClass
        # Pass None as parent to absolutely force it to act as a top-level OS window with its own taskbar icon
        dialog = SettingsDialogClass(None)
        dialog.raise_() 
        dialog.activateWindow()
        if dialog.exec():
            # Dialog internally sets keys into specific slots (api_key_nvidia, etc)
            # We just need to trigger a fresh reload into memory!
            nvidia_key = keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key")
            google_key = keyring.get_password("LLMChatApp", "api_key_google")
            
            base_url = dialog.get_base_url()
            
            if nvidia_key:
                self.llm_client.set_base_url(base_url)
                self.llm_client.set_api_key(nvidia_key)
                
            if google_key:
                 self.llm_client.set_google_api_key(google_key)
                 
            if nvidia_key or google_key:
                self.set_connected_status(True)
                self.refresh_auth_button_style()
                
                if not QSettings("LLMChatApp", "Settings").value("current_model_id"):
                    QTimer.singleShot(100, self.show_model_popup)
                else:
                    self.set_chat_enabled(True)
                    self.model_btn.setEnabled(True)
                
                # Successfully logged in -> can now show tray icon
                self.tray_icon.show()
            return True
        else:
            return False

    def show_gen_settings(self):
        """Opens the Smart Generation Parameters dialog."""
        from ui.gen_settings_dialog import GenSettingsDialog
        # Pass None as parent to force standalone taskbar entry (as established earlier!)
        dialog = GenSettingsDialog(None)
        if dialog.exec():
            self.add_system_message("✅ Generation parameters updated.")

    def show_model_popup(self):
        from ui.model_popup import ModelPopupClass
        
        current_id = QSettings("LLMChatApp", "Settings").value("current_model_id", "")
        dialog = ModelPopupClass(current_model_id=current_id, parent=self)
        
        if dialog.exec():
            selected_id = dialog.get_selected_model_id()
            if selected_id:
                self.llm_client.set_model(selected_id)
                model_name = self.get_model_name_by_id(selected_id)
                
                self.update_model_ui(selected_id)
                
                self.model_btn.setEnabled(True)
                self.set_chat_enabled(self.llm_client.has_api_key())
                self.add_system_message(f"Switched to model: {model_name}")

    def get_model_name_by_id(self, model_id):
        from logic.model_io import load_all_models
        try:
            models = load_all_models()
            for m in models:
                if m['id'] == model_id:
                    return m['name']
        except Exception as e:
            print(f"Error loading model names: {e}")
        return model_id 

    def update_model_ui(self, model_id):
        """Updates the model button text and the description label."""
        from logic.model_io import load_all_models
        name = model_id
        desc = ""
        
        try:
            models = load_all_models()
            for m in models:
                if m['id'] == model_id:
                    name = m.get('name', model_id)
                    desc = m.get('description', '')
                    break
        except Exception as e:
            print(f"Error loading model data: {e}")

        # Update button
        self.model_btn.setText(f"🤖 {name} ▼")
        
        # Update description label
        if desc:
            self.model_desc_label.setText(desc)
            self.model_desc_label.setWordWrap(True)
            self.model_desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.model_desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.model_desc_label.setVisible(True)
        else:
            self.model_desc_label.setVisible(False)

    def set_chat_enabled(self, enabled):
        self.input_field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

    def set_connected_status(self, connected):
        if connected:
            self.auth_btn.setText("🚪 Logout")
            self.auth_btn.setStyleSheet("""
                QPushButton { background-color: #d32f2f; border: none; border-radius: 5px; padding: 8px 20px; color: white; font-weight: bold; }
                QPushButton:hover { background-color: #b71c1c; }
            """)
        else:
            self.auth_btn.setText("🔓 Login")
            self.auth_btn.setStyleSheet("""
                QPushButton { background-color: #0078d4; border: none; border-radius: 5px; padding: 8px 20px; color: white; font-weight: bold; }
                QPushButton:hover { background-color: #106ebe; }
            """)
    # ---------------------------------------------------------
    # LOG LOGIC
    # ---------------------------------------------------------
    def show_update_log(self):
        from ui.log_viewer import LogViewerDialog
        dialog = LogViewerDialog(self)
        dialog.exec()

    def clear_update_log(self):
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
    
    # ---------------------------------------------------------
    # CHAT & STREAMING LOGIC
    # ---------------------------------------------------------

    def handle_upload(self):
        if self.is_generating:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Attach File", "", 
            "Code & Text Files (*.py *.js *.txt *.md *.json *.csv *.xml *.html *.css *.yaml *.yml);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                file_name = Path(file_path).name
                self.attached_files.append({'name': file_name, 'content': content})
                
                current_text = self.input_field.text()
                if not current_text:
                    self.input_field.setPlaceholderText(f"📎 {len(self.attached_files)} file(s) attached. Type your message...")
                    
                self.add_system_message(f"📎 Attached: {file_name}")
                
            except Exception as e:
                self.add_system_message(f"❌ Failed to read file: {str(e)}")

    def clear_attachments(self):
        self.attached_files = []
        self.input_field.setPlaceholderText("")

    def send_message(self, api_response_queue=None, custom_messages=None, custom_temp=None, custom_max_tokens=None):
        #user_message = self.input_field.text().strip()
        user_message = self.input_field.toPlainText().strip()
        if not user_message and not self.attached_files:
            return

        if not self.is_connected:
            QMessageBox.warning(self, "No Internet Connection", 
                           "Cannot send message. Please check your internet connection and try again.")
            return

        if not self.llm_client.has_api_key():
            QMessageBox.warning(self, "No API Key", "Please configure your API key.")
            self.open_settings()
            return
            
        if not self.llm_client.current_model:
            QMessageBox.warning(self, "No Model", "Please select a model.")
            self.show_model_popup()
            return

        self.response_start_time = time.perf_counter()  
        self.input_field.clear()
        
        final_prompt = user_message
        if self.attached_files:
            attachment_blocks = []
            for f in self.attached_files:
                attachment_blocks.append(f"--- File: {f['name']} ---\n```\n{f['content']}\n```")
            
            combined_text = "\n\n".join(attachment_blocks)
            if user_message:
                final_prompt = f"{combined_text}\n\nUser Request: {user_message}"
            else:
                final_prompt = f"{combined_text}\n\nPlease review the attached file(s)."
                
            self.clear_attachments()

        if user_message:
            self.add_user_message(user_message)
        else:
            self.add_user_message("📎 Sent attached file(s) for review.")
            
        self.chat_history.append({"role": "user", "content": final_prompt})
        
        # ==========================================
        # Model-aware context length & TOKEN checking
        # ==========================================
        TOKEN_BUFFER = 2000  # Reserve tokens for AI response

        # Estimate current message tokens (conservative: ~3 chars per token)
        estimated_new_tokens = len(final_prompt) // 3
        current_total_estimate = self.total_tokens + estimated_new_tokens
        
        token_limit = get_context_limit(self.llm_client.current_model)
        remaining_tokens = token_limit - current_total_estimate
        usage_percent = (current_total_estimate / token_limit) * 100
        
        # Format display strings
        limit_display = f"{token_limit // 1_000}K tokens" if token_limit >= 1000 else f"{token_limit} tokens"
        
        if remaining_tokens < TOKEN_BUFFER:
            # HARD BLOCK: Not enough space for AI to reply
            if remaining_tokens <= 0:
                remaining_display = "0 tokens"
            elif remaining_tokens >= 1000:
                remaining_display = f"{remaining_tokens // 1000}K tokens"
            else:
                remaining_display = f"{remaining_tokens} tokens"
                
            reply = QMessageBox.warning(self, "Context Limit Reached",
                f"Context usage is at {usage_percent:.0f}% ({current_total_estimate:,} tokens).\n"
                f"The model only has {remaining_display} left for its response.\n\n"
                f"Start a new conversation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.chat_history.pop()
                self.new_conversation()
                return
                
        elif usage_percent > 85:
            # SOFT WARNING
            self.add_system_message(f"⚠️ Context usage at {usage_percent:.0f}% ({limit_display}). Consider starting a new conversation soon.")
        # ==========================================

        self.input_field.setEnabled(False)
        self.add_typing_indicator()
        self.current_response_text = "" 
        
        # ------------------------------------------
        # Load current generation parameters
        # ------------------------------------------
        settings = QSettings("LLMChatApp", "Settings")
        use_remote_defaults = settings.value("gen_use_defaults", "false") == "true"
        
        # Priority: 1. Explicit arguments, 2. Server Default flag, 3. Saved UI values
        if use_remote_defaults and custom_temp is None and custom_max_tokens is None:
            active_temp = None
            active_tokens = None
        else:
            active_temp = custom_temp if custom_temp is not None else float(settings.value("gen_temperature", 0.7))
            active_tokens = custom_max_tokens if custom_max_tokens is not None else int(settings.value("gen_max_tokens", 4096))
        
        api_payload = custom_messages if custom_messages is not None else self.get_messages_for_api()
        self.current_worker = ChatWorker(self.llm_client, api_payload, temperature=active_temp, max_tokens=active_tokens)    
        self.current_worker.stream_chunk.connect(self.on_stream_chunk)
        self.current_worker.thinking_chunk.connect(self.on_thinking_chunk)
        self.current_worker.response_received.connect(self.on_response_complete)
        self.current_worker.error_occurred.connect(self.on_error)

        # If this is an API request, also route results to the response queue
        if api_response_queue:
            self.current_worker.response_received.connect(lambda resp: api_response_queue.put(resp))
            self.current_worker.error_occurred.connect(lambda err: api_response_queue.put(f"Error: {err}"))

        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.metrics_received.connect(self.on_metrics_received)
        self.current_worker.start()
        self.set_send_button_generating()
        
    def add_user_message(self, message: str):
        html = f"<b>You:</b> {self.formatter.escape_html(message)}"
        self.chat_display.append(html)
        self.chat_html_history.append(html)
        self.scroll_to_bottom()
        
    def add_assistant_message(self, message: str):
        # Use the new formatter which handles code blocks, language headers, and copy buttons
        html_content = self.formatter.format_ai_response(message)
        html = f"<b>Assistant:</b><br>{html_content}"
        self.chat_display.append(html)
        self.chat_html_history.append(html)
        self.scroll_to_bottom()
        
    def add_system_message(self, message: str):
        if not hasattr(self, 'chat_display'):
            return  # Skip if chat_display doesn't exist yet
        color = self.get_system_message_color()
        html = f"<i style='color: {color};'>ℹ️ {self.formatter.escape_html(message)}</i>"
        self.chat_display.append(html)
        self.chat_html_history.append(html)
        self.scroll_to_bottom()

    def add_typing_indicator(self):
        self.chat_display.append("<i>Assistant is typing...</i>")
        self.scroll_to_bottom()
        
    def remove_typing_indicator(self):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.movePosition(cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()
        if "Assistant is typing..." in text:
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
        
    def on_stream_chunk(self, chunk: str):
        # We are receiving data, so we are definitely connected
        if not self.is_connected:
            self.is_connected = True
            self.update_connection_icon()

        if self.current_response_text == "":
            self.remove_typing_indicator()
            self.chat_display.append("<b>Assistant:</b> ")
            self.stream_start_position = self.chat_display.textCursor().position()

        self.current_response_text += chunk

        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.scroll_to_bottom()
    
    def on_response_complete(self, full_response: str):
        import markdown
        self.chat_history.append({"role": "assistant", "content": full_response})

        if self.stream_start_position is not None:
            cursor = self.chat_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.setPosition(self.stream_start_position, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

            # 1. Generate the Rich HTML (Markdown + Code Blocks)
            html_content = self.formatter.format_ai_response(full_response)

            # 2. Insert the HTML directly
            # Note: "Assistant:" label was already added at the start of streaming
            self.chat_display.insertHtml(f"<br>{html_content}<br>")
            
            # 3. Append Copy Button
            copy_buttons = self.get_copy_button_html()
            self.chat_display.insertHtml(copy_buttons)
            
            # 4. Construct the FULL block for the HTML cache
            # We reconstruct it here because we cleared the streaming text above
            full_html_block = f"<b>Assistant:</b><br>{html_content}<br>{copy_buttons}"
            self.chat_html_history.append(full_html_block)
            
            self.stream_start_position = None
            
            # 5. Attach Data for Copying
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.movePosition(QTextCursor.StartOfBlock)
            block = cursor.block()
            block.setUserData(MessageData(full_response))

        else:
            # Fallback for non-streamed
            self.chat_display.append("<b>Assistant:</b> ") 
            
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.StartOfBlock)
            block = cursor.block()
            block.setUserData(MessageData(full_response))
            
            html = self.formatter.format_ai_response(full_response)
            self.chat_display.insertHtml(html)

        # AUTO-SAVE TO SQLITE
        self.auto_save_current_chat()
        self.chat_display.insertHtml(self.get_copy_button_html())

        self.current_response_text = ""
        
        # Timing
        if self.response_start_time:
            elapsed = time.perf_counter() - self.response_start_time
            self.chat_display.append(
                f"<div style='color: #888888; font-size: 12px; margin-top: 5px; text-align: right;'>"
                f"⏱️ {elapsed:.2f}s</div>"
            )
        self.scroll_to_bottom()

    def on_metrics_received(self, metrics: dict):
        border_color = self.get_metrics_border_color()
        metrics_html = f"""
        <div style='display: flex; gap: 15px; justify-content: flex-end; color: #888888; font-size: 11px; margin-top: 8px; padding-top: 5px; border-top: 1px solid {border_color};'>
            <span>⚡ TTFT: {metrics['ttft']}s</span>
            <span>🚀 Speed: {metrics['tps']} tok/s</span>
            <span>📝 Tokens: {metrics['prompt_tokens']} in / {metrics['completion_tokens']} out</span>
        </div>
        """
        self.chat_display.append(metrics_html)
        self.total_tokens = metrics['prompt_tokens'] + metrics['completion_tokens']
        self.scroll_to_bottom()

    def on_error(self, error_message: str):
        self.remove_typing_indicator()

        # IMPROVED - Better error classification
        error_lower = error_message.lower()

        if "timeout" in error_lower:
            self.add_system_message("⏰ Connection timeout. Please check your internet connection.")
            self.force_disconnected_state()
        elif "connection" in error_lower or "network" in error_lower or "internet" in error_lower:
            self.add_system_message("🌐 Network error detected. Please check your internet connection.")
            self.force_disconnected_state()
        elif "api key" in error_lower or "authentication" in error_lower or "unauthorized" in error_lower:
            self.add_system_message(f"🔑 Authentication error: {error_message}")
            # Optionally trigger logout or settings dialog
        elif "rate limit" in error_lower or "too many requests" in error_lower:
            self.add_system_message("⚠️ Rate limit reached. Please wait a moment before sending more messages.")
        else:
            self.add_system_message(f"❌ Error: {error_message}")

        # If error happened WHILE AI was generating (e.g., internet dropped)
        if self.is_generating:
            # Remove the incomplete user message from history so it can be retried
            if self.chat_history and self.chat_history[-1]["role"] == "user":
                self.chat_history.pop()

            self.is_generating = False
            self.stream_start_position = None
            self.current_response_text = ""
            self.response_start_time = None
            self.current_worker = None

            self.set_send_button_idle()
            self.send_btn.setEnabled(True)
            self.input_field.setEnabled(True)
            self.input_field.setFocus()

    def on_worker_finished(self):
        self.set_send_button_idle()
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.current_worker = None
        
    def scroll_to_bottom(self):
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def regenerate_last_response(self):
        # 1. Check if we have history
        if len(self.chat_history) < 2:
            return

        # 2. The last message should be the Assistant's.
        # We need to pop it so the LLM generates a fresh one.
        last_role = self.chat_history[-1]["role"]
        
        if last_role == "assistant":
            # Remove the assistant's response from memory
            removed = self.chat_history.pop()
            
            # Remove the visual content from the chat display
            # Note: This is a simple visual clear. A more complex way is 
            # to remove the last specific text block, but clearing the last
            # line is safer for a quick implementation.
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            # Also try to remove the "Copy Raw" line
            cursor.deletePreviousChar()

            # 3. Re-trigger the worker
            self.current_response_text = ""
            self.add_typing_indicator()
            
            # Load current generation parameters
            settings = QSettings("LLMChatApp", "Settings")
            use_remote_defaults = settings.value("gen_use_defaults", "false") == "true"
            
            if use_remote_defaults:
                active_temp = None
                active_tokens = None
            else:
                active_temp = float(settings.value("gen_temperature", 0.7))
                active_tokens = int(settings.value("gen_max_tokens", 4096))
            
            self.current_worker = ChatWorker(self.llm_client, self.get_messages_for_api(), temperature=active_temp, max_tokens=active_tokens)
            self.current_worker.stream_chunk.connect(self.on_stream_chunk)
            self.current_worker.thinking_chunk.connect(self.on_thinking_chunk)
            self.current_worker.response_received.connect(self.on_response_complete)
            self.current_worker.error_occurred.connect(self.on_error)
            self.current_worker.finished.connect(self.on_worker_finished)
            self.current_worker.metrics_received.connect(self.on_metrics_received)
            self.current_worker.start()
            self.set_send_button_generating()
            
            # Add system message for feedback
            self.add_system_message("🔄 Regenerating response...")


    # ---------------------------------------------------------
    # STOP GENERATION & TOGGLE
    # ---------------------------------------------------------

    def stop_generation(self):
        self.clear_attachments()        
        worker = self.current_worker
        self.current_worker = None  
        
        if worker and worker.isRunning():
            worker.requestInterruption()   # Tell worker to stop gracefully
            worker.quit()                  # Exit event loop
            worker.wait(3000)              # Wait up to 3 seconds

            if worker.isRunning():
                worker.terminate()         # Force stop if still running
                worker.wait()
            
        self.remove_typing_indicator()
        
        terminate_color = self.get_terminate_color()
        if self.response_start_time:
            elapsed = time.perf_counter() - self.response_start_time
            self.chat_display.append(
                f"<i style='color: {terminate_color};'>⏹️ Generation terminated by user ({elapsed:.2f}s)</i><br>"
            )
        elif self.current_response_text:
            self.chat_display.append(f"<br><i style='color: {terminate_color};'>⏹️ Generation terminated by user.</i><br>")
        else:
            self.chat_display.append(f"<br><i style='color: {terminate_color};'>⏹️ Generation terminated by user.</i><br>")
        
        if self.current_response_text:
            self.chat_history.append({"role": "assistant", "content": self.current_response_text})

        self.stream_start_position = None
        self.current_response_text = ""
        self.response_start_time = None
        
        self.set_send_button_idle()
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def handle_send_stop_toggle(self):
        if self.is_generating:
            self.stop_generation()
        else:
            self.send_message()

    def set_send_button_idle(self):
        self.is_generating = False 
        self.send_btn.setText("Send")
        if self.theme_manager.current_theme == "dark":
            disabled_style = "QPushButton:disabled { background-color: #3c3c3c; color: #888; }"
        else:
            disabled_style = "QPushButton:disabled { background-color: #e0e0e0; color: #aaaaaa; }"
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0078d4;
                border: none;
                border-radius: 8px;
                padding: 12px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #106ebe; }}
            QPushButton:pressed {{ background-color: #005a9e; }}
            {disabled_style}
        """)

    def set_send_button_generating(self):
        self.is_generating = True
        self.send_btn.setEnabled(True)  
        self.send_btn.setText("Stop")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                border: none;
                border-radius: 8px;
                padding: 12px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #b71c1c; }
            QPushButton:pressed { background-color: #8e0000; }
        """)

    # ---------------------------------------------------------
    # UTILITIES, MENUS, WINDOW STATE
    # ---------------------------------------------------------
        
    def new_conversation(self):
        if self.chat_history:
            reply = QMessageBox.question(
                self, "New Conversation",
                "Start a new conversation? Current chat will be cleared.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.clear_chat()
                
    def clear_chat(self):
        self.chat_display.clear()
        self.chat_history = []
        self.total_tokens = 0
        self.current_response_text = ""
        self.stream_start_position = None
        self.response_start_time = None
        self.add_system_message("New conversation started")

    def copy_last_response(self):
        """Copy the last assistant response to clipboard"""
        for msg in reversed(self.chat_history):
            if msg["role"] == "assistant":
                clipboard = QApplication.clipboard()
                clipboard.setText(msg["content"])
                self.add_system_message("📋 Last response copied to clipboard")
                return
        self.add_system_message("No response to copy")

    def save_conversation(self):
        if not self.chat_history:
            QMessageBox.information(self, "Nothing to Save", "No conversation to save.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Conversation", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            current_model = self.llm_client.current_model or ""
            self.conversation_manager.export_to_json(self.chat_history, file_path, current_model)
            self.statusBar().showMessage(f"Conversation exported to {file_path}", 5000)
            
    def load_conversation(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Conversation", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            data = self.conversation_manager.import_from_json(file_path)
            messages = data.get("messages", [])
            
            if messages:
                self.clear_chat()
                self.chat_history = messages
                
                saved_model_id = data.get("model_id", "")
                if saved_model_id:
                    self.llm_client.set_model(saved_model_id)
                    
                    self.update_model_ui(saved_model_id)
                    
                    self.model_btn.setEnabled(True)
                    self.set_chat_enabled(True)
                
                for msg in messages:
                    if msg["role"] == "user":
                        self.add_user_message(msg["content"])
                    elif msg["role"] == "assistant":
                        self.add_assistant_message(msg["content"])
                        
                self.add_system_message(f"Conversation loaded from {file_path}")
                
    def show_about(self):
        from utils.constants import APP_VERSION
        border_color = "#e0e0e0" if self.theme_manager.current_theme == "light" else "#3c3c3c"
        about_text = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <h2 style="color: #0078d4; margin-bottom: 5px;">LLM Chat App</h2>
            <p><b>Version:</b> {APP_VERSION}<br>
            <b>Developer:</b> Arean Narrayan</p>
            
            <hr style="border: 1px solid {border_color}; margin: 10px 0;">
            
            <p>A sleek, modern desktop application designed to seamlessly connect you 
            with cutting-edge Large Language Models via the NVIDIA NIM and Google Gemini APIs.</p>
            
            <p><b>Key Features:</b></p>
            <ul>
                <li>Real-time streaming responses</li>
                <li>Seamlessly switch between multiple state-of-the-art AI models</li>
                <li>Rich text and code syntax rendering (Markdown)</li>
                <li>Save and load conversation histories locally</li>
                <li>Clean, adaptive user interface</li>
            </ul>
            
            <hr style="border: 1px solid {border_color}; margin: 10px 0;">
            
            <p style="font-size: 11px; color: #666666;">
            Powered by <b>NVIDIA NIM</b> & <b>Google Gemini</b><br>
            Built with <b>Python</b> & <b>PySide6</b></p>
        </div>
        """
        
        QMessageBox.about(self, "About LLM Chat App", about_text)

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

    def api_doc(self):
        """
        Handler for help_menu.addAction("License", self.api_doc)
        Now updated to load the API Server documentation.
        """
        from ui.file_viewer import FileViewerDialog

        # We pass the filename you created. 
        # Your FileViewerDialog will find it in the project root.
        dialog = FileViewerDialog(
            title="Universal API Server Documentation",
            file_names=["API_SERVER.md"], 
            is_markdown=True,
            size=(800, 600),
            parent=self
        )
        dialog.exec()

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

    def download_vscode_extension(self):
        import os
        from pathlib import Path
        
        folder = Path(__file__).parent.parent / "extension"
        if folder.exists():
            os.startfile(str(folder))
            QMessageBox.information(
                self,
                "VS Code Extension",
                "The extension folder is now open.\n\n"
                "Install:\n"
                "1. VS Code → Extensions → ... → Install from VSIX\n"
                "2. Select vscode-llm-chat-1.0.1.vsix"
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
                self,
                "JetBrains Plugin",
                "The extension folder is now open.\n\n"
                "Install:\n"
                "1. Settings → Plugins → ⚙️ → Install Plugin from Disk\n"
                "2. Select jetbrains-llm-chat-1.0.1.zip"
            )
        else:
            QMessageBox.warning(self, "Folder Not Found", "extension folder not found")

    def format_code_blocks(self, text: str) -> str:
        return self.formatter.escape_html(text)

    def escape_html(self, text: str) -> str:
        return self.formatter.escape_html(text)

    def get_messages_for_api(self):
        """
        Returns the chat history with current library instructions strictly enforced as the first message.
        """
        # 1. Start with the current history, but STRIP OUT any existing system messages
        # This ensures that our "Live" library instructions are the only ones active.
        messages = [msg for msg in self.chat_history if msg['role'] != 'system']
        
        # 2. Load the System Instruction Library from FILE
        import json
        import os
        from utils.path_utils import get_resource_path
        
        library = []
        file_path = get_resource_path("resources/user_prompts.json")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    library = json.load(f)
            except Exception as e:
                print(f"Error reading user_prompts.json: {e}")

        # 3. Filter active instructions
        active_texts = []
        for item in library:
            if item.get('checked', False):
                # Get the text content
                instruction_text = item.get('text', '')
                if instruction_text:
                    active_texts.append(f"- {instruction_text}")

        # 4. Combine and inject at the start
        if active_texts:
            combined_prompt = "Follow these instructions:\n" + "\n".join(active_texts)
            messages.insert(0, {"role": "system", "content": combined_prompt})
            
        # 5. Final Sanity Check: Filter out any empty messages (causes API Error 400)
        final_messages = []
        for msg in messages:
            content = msg.get('content', "").strip()
            if content:
                final_messages.append({
                    "role": msg['role'],
                    "content": content
                })
        
        return final_messages

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            is_maximized = self.windowState() & Qt.WindowState.WindowMaximized
            is_fullscreen = self.windowState() & Qt.WindowState.WindowFullScreen
            if not is_maximized and not is_fullscreen:
                QTimer.singleShot(0, self.showMaximized)
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        
        if hasattr(self, '_initial_popups_shown'):
            return
            
        self._initial_popups_shown = True
        
        
        settings = QSettings("LLMChatApp", "Settings")
        api_key = keyring.get_password("LLMChatApp", "api_key") or ""
        model_id = settings.value("current_model_id", "")
        
        if not api_key:
            success = self.open_settings()
            if not success:
                QTimer.singleShot(0, QApplication.instance().quit)
                return
        elif not model_id:
            self.show_model_popup()
        else:
            self.add_system_message("Ready to chat.")

    def logout(self):
        # 1. Handle saving the current chat (your existing logic)
        if self.chat_history:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle("Unsaved Session")
            msg_box.setText("You have an active chat session.")
            msg_box.setInformativeText("Do you want to save it before logging out?")

            save_btn = msg_box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
            discard_btn = msg_box.addButton("Don't Save", QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            msg_box.exec()

            if msg_box.clickedButton() == save_btn:
                file_path, _ = QFileDialog.getSaveFileName(self, "Save Conversation", "", "JSON Files (*.json)")
                if file_path:
                    current_model = self.llm_client.current_model or ""
                    self.conversation_manager.save_conversation(self.chat_history, file_path, current_model)
                else:
                    return # User canceled the save dialog
            elif msg_box.clickedButton() == cancel_btn:
                return
        else:
            reply = QMessageBox.question(
                self, "Logout", 
                "Are you sure you want to logout?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # 2. Clear all states (Securely wiping all segmented identity tokens)
        settings = QSettings("LLMChatApp", "Settings")
        try:
            keyring.delete_password("LLMChatApp", "api_key")
            keyring.delete_password("LLMChatApp", "api_key_nvidia")
            keyring.delete_password("LLMChatApp", "api_key_google")
        except Exception:
            pass 
            
        settings.remove("api_key") 
        settings.remove("active_provider_id")
        settings.remove("current_model_id")
        settings.sync()

        self.llm_client.api_key = None
        self.llm_client.google_api_key = None
        self.llm_client.client = None
        self.llm_client.genai_configured = False
        self.llm_client.current_model = None

        self.clear_chat()
        self.clear_attachments()
        self.set_connected_status(False)
        self.set_chat_enabled(False)

        self.model_btn.setText("Select Model ▼")
        self.model_desc_label.setText("")
        self.model_desc_label.setVisible(False)
        self.model_btn.setEnabled(False)
        self.input_field.clear()
        
        # Hide Tray Icon during unauthenticated phase
        self.tray_icon.hide()

        self.add_system_message("✅ Logged out successfully.")

        # 3. NEW: Force login popup, close app if they hit 'X' or cancel
        success = self.open_settings()
        if not success:
            QTimer.singleShot(0, QApplication.instance().quit)

    def keyPressEvent(self, event):
        # Check for Ctrl+D (Clear Chat)
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
            self.clear_chat()
            event.accept()
            return
        
        # Check for Ctrl+Shift+C (Copy Last Response)
        if (event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) 
            and event.key() == Qt.Key.Key_C):
            self.copy_last_response()
            event.accept()
            return
        
        # F11 Fullscreen
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showMaximized() 
            else:
                self.showFullScreen() 
            event.accept()
            return
        
        # Escape from Fullscreen
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showMaximized()      
            event.accept()
            return
        
        else:
            super().keyPressEvent(event)

    def on_thinking_chunk(self, chunk: str):
        text = self.chat_display.toPlainText()
        if "🧠 Thinking..." not in text:
            if self.current_response_text == "":
                self.remove_typing_indicator()
            thinking_color = self.get_thinking_color()
            self.chat_display.append(f"<i style='color: {thinking_color};'>🧠 Thinking...</i>")
            if self.stream_start_position is None:
                self.stream_start_position = self.chat_display.textCursor().position()

        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.scroll_to_bottom()

    def setup_chat_styles(self):
        self.chat_display.setStyleSheet(self.get_chat_styles())

    def format_ai_response(self, text: str) -> str:
        return self.formatter.format_ai_response(text)
        
    def show_model_manager(self):
        from ui.model_manager import ModelManagerDialog

        # Check if fetch is running
        if ModelManagerDialog._fetch_in_progress:
            QMessageBox.warning(
                self,
                "Fetch in Progress",
                "Model fetch is already running in background.\n\n"
                "Check 'Log' menu for real-time updates.\n"
                "Please wait for it to complete."
            )
            return

        dialog = ModelManagerDialog(theme=self.theme_manager.current_theme, parent=self)
        dialog.exec()

    def show_storage_manager(self):
        from ui.storage_manager_dialog import StorageManagerDialog
        dialog = StorageManagerDialog(theme=self.theme_manager.current_theme, parent=self)
        dialog.exec()

    def open_storage_location(self):
        from utils.storage_config import StorageManager
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        root = StorageManager.get_instance().get_storage_root()
        if root.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))



    def start_new_chat(self):
        """Saves current chat to DB, then resets for a fresh session."""
        if self.chat_history:
            # Generate title
            title = "New Conversation"
            for msg in self.chat_history:
                if msg['role'] == 'user':
                    title = msg['content'][:30].strip() + "..."
                    break
            
            # Save to SQLite
            self.conversation_manager.save_conversation(
                self.chat_history, 
                title=title, 
                conv_id=self.current_conv_id
            )
            self.refresh_history_list()

        self.chat_history = []
        self.chat_html_history = []
        self.current_conv_id = None
        self.chat_display.clear()
        self.ui.chat_history_list.clearSelection()
        self.statusBar().showMessage("New conversation started.", 5000)

    def auto_save_current_chat(self):
        """Silently saves the current state to SQLite. Updates title on first exchange."""
        if not self.chat_history:
            return

        # 1. Generate/Refresh Title if needed
        title = "New Conversation"
        for msg in self.chat_history:
            if msg['role'] == 'user':
                title = msg['content'][:30].strip() + "..."
                break

        # 2. Save to DB
        is_new = (self.current_conv_id is None)
        self.current_conv_id = self.conversation_manager.save_conversation(
            self.chat_history,
            title=title,
            conv_id=self.current_conv_id,
            model_id=self.ui.model_btn.text(),
            messages_html=json.dumps(self.chat_html_history) # Save cached HTML chunks
        )

        # 3. Refresh sidebar only if it's a new entry to show the title
        if is_new:
            self.refresh_history_list()

    def refresh_history_list(self):
        """Loads all conversations from SQLite into the sidebar."""
        self.ui.chat_history_list.clear()
        
        conversations = self.conversation_manager.get_all_conversations()
        for conv_id, title, timestamp in conversations:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, conv_id)
            # Add tooltip with timestamp
            item.setToolTip(f"Saved: {timestamp}")
            self.ui.chat_history_list.addItem(item)

    def load_selected_history(self, item):
        """Loads the selected SQLite conversation into the chat display."""
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        if conv_id is None:
            return

        self.current_conv_id = conv_id
        try:
            data = self.conversation_manager.load_conversation(conv_id)
            if data and "messages" in data:
                self.chat_history = data["messages"]
                self.chat_display.clear()
                
                # Check for cached HTML first (much faster)
                cached_html_json = data.get("messages_html")
                if cached_html_json:
                    try:
                        self.chat_html_history = json.loads(cached_html_json)
                        for html_chunk in self.chat_html_history:
                            self.chat_display.append(html_chunk)
                    except Exception:
                        # Fallback to re-rendering
                        self.chat_html_history = []
                        for msg in self.chat_history:
                            if msg['role'] == 'user':
                                self.add_user_message(msg['content'])
                            else:
                                self.add_assistant_message(msg['content'])
                else:
                    # Re-render all messages if no cache exists
                    self.chat_html_history = []
                    for msg in self.chat_history:
                        if msg['role'] == 'user':
                            self.add_user_message(msg['content'])
                        else:
                            self.add_assistant_message(msg['content'])
                
                self.statusBar().showMessage(f"Loaded: {item.text()}", 5000)
                self.scroll_to_bottom()
        except Exception as e:
            self.statusBar().showMessage(f"Error loading history: {e}", 5000)

    def clear_all_history(self):
        """Intelligently deletes selected items, current chat, or everything in SQLite."""
        selected_items = self.ui.chat_history_list.selectedItems()
        
        if selected_items:
            count = len(selected_items)
            reply = QMessageBox.question(
                self, "Delete Selected",
                f"Delete the {count} selected conversation(s)?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.chat_history = []
                self.current_conv_id = None
                for item in selected_items:
                    conv_id = item.data(Qt.ItemDataRole.UserRole)
                    if conv_id is not None:
                        self.conversation_manager.delete_conversation(conv_id)
                self.start_new_chat()
                self.refresh_history_list()

        elif self.current_conv_id:
            reply = QMessageBox.question(
                self, "Delete Current Chat",
                "Delete the conversation currently on screen?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.conversation_manager.delete_conversation(self.current_conv_id)
                self.start_new_chat()
                self.refresh_history_list()
        
        else:
            reply = QMessageBox.question(
                self, "Clear All History",
                "Are you sure you want to delete ALL conversations?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.conversation_manager.clear_all()
                self.start_new_chat()
                self.refresh_history_list()

    def show_history_context_menu(self, pos):
        """Shows a right-click menu to delete a specific conversation."""
        item = self.ui.chat_history_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ Delete Conversation")
        
        action = menu.exec(self.ui.chat_history_list.mapToGlobal(pos))
        if action == delete_action:
            self.delete_specific_history(item)

    def delete_specific_history(self, item):
        """Deletes a single JSON file and removes it from the list."""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path:
            return

        reply = QMessageBox.question(
            self, "Delete Conversation",
            f"Delete '{item.text()}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Clear memory if we are deleting the active chat
                self.chat_history = []
                
                Path(file_path).unlink()
                self.refresh_history_list()
                self.start_new_chat()
                self.statusBar().showMessage("Conversation deleted.", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete file: {e}")

