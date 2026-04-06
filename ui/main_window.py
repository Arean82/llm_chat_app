# ui/main_window.py
import sys
import os
from pathlib import Path

import markdown

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction
from PySide6.QtUiTools import QUiLoader

from logic.llm_client import LLMClient
from logic.chat_worker import ChatWorker
from logic.conversation_manager import ConversationManager
from ui.settings_dialog import SettingsDialogClass

from PySide6.QtWidgets import QSizePolicy 

class MainWindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        
        print("MainWindowClass.__init__ starting...")
        
        loader = QUiLoader()
        ui_file = Path(__file__).parent.parent / "ui_designer" / "main_window.ui"
        
        print(f"Looking for UI file at: {ui_file}")
        
        if not ui_file.exists():
            print(f"ERROR: UI file not found at {ui_file}")
            self.setup_fallback_ui()
            return
        
        print("Loading UI file...")
        
        self.ui = loader.load(str(ui_file))
        
        if self.ui is None:
            print("ERROR: Failed to load UI file")
            self.setup_fallback_ui()
            return
        
        print("UI loaded successfully")
        
        self.ui.setParent(self)
        
        required_widgets = ['chat_display', 'input_field', 'send_btn', 'settings_btn', 'model_list', 'current_model_label', 'status_label']
        for widget_name in required_widgets:
            if hasattr(self.ui, widget_name):
                print(f"✓ Found widget: {widget_name}")
            else:
                print(f"✗ MISSING widget: {widget_name}")
        
        self.chat_display = self.ui.chat_display
        self.input_field = self.ui.input_field
        self.send_btn = self.ui.send_btn
        self.settings_btn = self.ui.settings_btn
        self.model_list = self.ui.model_list
        self.current_model_label = self.ui.current_model_label
        self.status_label = self.ui.status_label
        
        self.llm_client = LLMClient()
        self.conversation_manager = ConversationManager()
        self.chat_history = []
        self.current_worker = None
        self.current_response_text = ""  # Store streaming response
        
        self.setup_menu_bar()
        self.setup_connections()
        self.load_settings()
        self.load_models()
        
        self.setup_fullscreen()

        print("MainWindowClass.__init__ completed")
        
    def setup_fallback_ui(self):
        print("Setting up fallback UI...")
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        label = QLabel("UI file failed to load. Check console for errors.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        self.setCentralWidget(central_widget)
        self.setWindowTitle("Error - UI File Not Found")
        
    def setup_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        new_action = QAction("New Conversation", self)
        new_action.triggered.connect(self.new_conversation)
        file_menu.addAction(new_action)

        save_action = QAction("Save Conversation", self)
        save_action.triggered.connect(self.save_conversation)
        file_menu.addAction(save_action)

        load_action = QAction("Load Conversation", self)
        load_action.triggered.connect(self.load_conversation)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("Edit")

        clear_action = QAction("Clear Chat", self)
        clear_action.triggered.connect(self.clear_chat)
        edit_menu.addAction(clear_action)

        account_menu = menubar.addMenu("Account")

        settings_action = QAction("⚙️ Settings", self)
        settings_action.triggered.connect(self.open_settings)
        account_menu.addAction(settings_action)

        account_menu.addSeparator()

        logout_action = QAction("🚪 Logout", self)
        logout_action.triggered.connect(self.logout)
        account_menu.addAction(logout_action)

        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_connections(self):
        self.send_btn.clicked.connect(self.send_message)
        self.input_field.returnPressed.connect(self.send_message)
        self.settings_btn.clicked.connect(self.open_settings)
        self.model_list.itemClicked.connect(self.on_model_selected)
        
    def load_models(self):
        models = self.llm_client.get_available_models()
        for model in models:
            self.model_list.addItem(f"{model['name']}\n{model['description']}")
            item = self.model_list.item(self.model_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, model['id'])
            
        if self.model_list.count() > 0:
            self.model_list.setCurrentRow(0)
            first_model_id = self.model_list.item(0).data(Qt.ItemDataRole.UserRole)
            self.llm_client.set_model(first_model_id)
            first_name = self.model_list.item(0).text().split('\n')[0]
            self.current_model_label.setText(f"Current: {first_name}")
            
    def on_model_selected(self, item):
        model_id = item.data(Qt.ItemDataRole.UserRole)
        self.llm_client.set_model(model_id)
        model_name = item.text().split('\n')[0]
        self.current_model_label.setText(f"Current: {model_name}")
        self.add_system_message(f"Switched to model: {model_name}")
        
    def open_settings(self):
        dialog = SettingsDialogClass(self)
        if dialog.exec():
            api_key = dialog.get_api_key()
            if api_key:
                self.llm_client.set_api_key(api_key)
                self.set_connected_status(True)
                settings = QSettings("LLMChatApp", "Settings")
                settings.setValue("api_key", api_key)
                
    def load_settings(self):
        settings = QSettings("LLMChatApp", "Settings")
        api_key = settings.value("api_key", "")
        if api_key:
            self.llm_client.set_api_key(api_key)
            self.set_connected_status(True)
        else:
            self.set_connected_status(False)
            self.add_system_message("⚠️ No API key found. Click Settings to configure.")
            
    def set_connected_status(self, connected: bool):
        """Update connection status indicator"""
        if connected:
            self.status_label.setText("🟢 Connected to NVIDIA NIM")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    margin-top: 10px;
                    color: #4caf50;
                    background-color: #2d2d2d;
                    border-radius: 5px;
                    font-weight: bold;
                    border: 1px solid #3c3c3c;
                }
            """)
            self.send_btn.setEnabled(True)
            self.input_field.setEnabled(True)
        else:
            self.status_label.setText("🔴 Not connected - Check Settings")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    margin-top: 10px;
                    color: #f44336;
                    background-color: #2d2d2d;
                    border-radius: 5px;
                    font-weight: bold;
                    border: 1px solid #3c3c3c;
                }
            """)
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            
    def send_message(self):
        user_message = self.input_field.text().strip()
        if not user_message:
            return
            
        if not self.llm_client.has_api_key():
            QMessageBox.warning(self, "No API Key", "Please configure your API key in Settings.")
            self.open_settings()
            return
            
        self.input_field.clear()
        self.add_user_message(user_message)
        self.chat_history.append({"role": "user", "content": user_message})
        
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        
        self.add_typing_indicator()
        
        self.current_response_text = ""  # Reset for new response
        
        self.current_worker = ChatWorker(self.llm_client, self.chat_history)
        self.current_worker.stream_chunk.connect(self.on_stream_chunk)
        self.current_worker.thinking_chunk.connect(self.on_thinking_chunk)
        self.current_worker.response_received.connect(self.on_response_complete)
        self.current_worker.error_occurred.connect(self.on_error)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()
        
    def add_user_message(self, message: str):
        self.chat_display.append(f"<b>You:</b> {self.escape_html(message)}")
        self.scroll_to_bottom()
        
    def add_assistant_message(self, message: str):
        # Convert markdown to HTML with code block support
        html = markdown.markdown(message, extensions=['extra', 'codehilite', 'fenced_code'])
        
        # Add custom styling for code blocks
        html = html.replace('<pre>', '<pre style="background-color: #1e1e1e; border-left: 3px solid #0078d4; padding: 10px; border-radius: 5px; overflow-x: auto;">')
        html = html.replace('<code>', '<code style="font-family: Consolas, monospace; color: #d4d4d4;">')
        
        self.chat_display.append(f"<b>🤖 Assistant:</b><br>{html}")
        self.scroll_to_bottom()
        
    def add_system_message(self, message: str):
        self.chat_display.append(f"<i style='color: #ffd700;'>ℹ️ {self.escape_html(message)}</i>")
        self.scroll_to_bottom()
        
    def add_typing_indicator(self):
        self.chat_display.append("<i>🤖 Assistant is typing...</i>")
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
        # Remove typing indicator if this is the first chunk
        if self.current_response_text == "":
            self.remove_typing_indicator()
            # Add assistant label
            self.chat_display.append("<b>🤖 Assistant:</b> ")
        
        # Accumulate the response
        self.current_response_text += chunk
        
        # Show plain text during streaming
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.scroll_to_bottom()
        
    def on_response_complete(self, full_response: str):
        self.chat_history.append({"role": "assistant", "content": full_response})

        # Find and remove the streaming plain text
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.movePosition(cursor.MoveOperation.StartOfLine, cursor.MoveMode.KeepAnchor)

        selected_text = cursor.selectedText()
        if "🤖 Assistant:" not in selected_text:
            cursor.movePosition(cursor.MoveOperation.Up, cursor.MoveMode.KeepAnchor)
            selected_text = cursor.selectedText()

        if "🤖 Assistant:" in selected_text or "Assistant:" in selected_text:
            cursor.removeSelectedText()
            cursor.deletePreviousChar()

            # Convert markdown to HTML with code block support
            html = markdown.markdown(full_response, extensions=['extra', 'codehilite', 'fenced_code'])

            # Add custom styling for code blocks
            html = html.replace('<pre>', '<pre style="background-color: #1e1e1e; border-left: 3px solid #0078d4; padding: 10px; border-radius: 5px; overflow-x: auto;">')
            html = html.replace('<code>', '<code style="font-family: Consolas, monospace; color: #d4d4d4;">')

            self.chat_display.insertHtml(f"<b>🤖 Assistant:</b><br>{html}<br>")

        self.current_response_text = ""
        self.scroll_to_bottom()

    def on_error(self, error_message: str):
        self.remove_typing_indicator()
        self.add_system_message(f"Error: {error_message}")
        
    def on_worker_finished(self):
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.current_worker = None
        
    def scroll_to_bottom(self):
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
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
        self.current_response_text = ""
        self.add_system_message("New conversation started")
        
    def save_conversation(self):
        if not self.chat_history:
            QMessageBox.information(self, "Nothing to Save", "No conversation to save.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Conversation", "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.conversation_manager.save_conversation(self.chat_history, file_path)
            self.add_system_message(f"Conversation saved to {file_path}")
            
    def load_conversation(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Conversation", "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            conversation = self.conversation_manager.load_conversation(file_path)
            if conversation:
                self.clear_chat()
                self.chat_history = conversation
                for msg in conversation:
                    if msg["role"] == "user":
                        self.add_user_message(msg["content"])
                    elif msg["role"] == "assistant":
                        self.add_assistant_message(msg["content"])
                self.add_system_message(f"Conversation loaded from {file_path}")
                
    def show_about(self):
        QMessageBox.about(
            self, "About LLM Chat App",
            "LLM Chat App\n\n"
            "A desktop chat application using NVIDIA NIM free API.\n\n"
            "Features:\n"
            "- Multiple LLM models\n"
            "- Streaming responses\n"
            "- Code highlighting\n"
            "- Conversation save/load\n\n"
            "Free tier: 40 requests/minute, unlimited tokens"
        )
        
    def format_code_blocks(self, text: str) -> str:
        return self.escape_html(text)
        
    def escape_html(self, text: str) -> str:
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }
        return "".join(html_escape_table.get(c, c) for c in text)
    
    def setup_fullscreen(self):
        """Set window to fullscreen and make it responsive"""
        self.showMaximized()
        self.ui.chat_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ui.chat_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        if hasattr(self.ui, 'logout_btn'):
            self.ui.logout_btn.clicked.connect(self.logout)

        if hasattr(self.ui, 'actionSettings'):
            self.ui.actionSettings.triggered.connect(self.open_settings)
        if hasattr(self.ui, 'actionLogout'):
            self.ui.actionLogout.triggered.connect(self.logout)

    def logout(self):
        """Remove API key and reset connection"""
        reply = QMessageBox.question(
            self, "Logout", 
            "Are you sure you want to logout? This will remove your saved API key.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            settings = QSettings("LLMChatApp", "Settings")
            settings.remove("api_key")

            self.llm_client.api_key = None
            self.llm_client.client = None

            self.clear_chat()
            self.set_connected_status(False)
            self.add_system_message("✅ Logged out successfully. API key removed.")
            self.input_field.clear()

            QMessageBox.information(
                self, "Logout Successful",
                "You have been logged out. Your API key has been removed.\n\n"
                "Click Settings to enter a new API key."
            )

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
                self.showMaximized()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showMaximized()
        else:
            super().keyPressEvent(event)

    def on_thinking_chunk(self, chunk: str):
        """Handle thinking/reasoning content from models like Kimi K2 Thinking"""
        # Check if we already have a thinking section
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        # Check if we need to add a thinking header
        text = self.chat_display.toPlainText()
        if "🧠 Thinking..." not in text and not self.current_response_text:
            self.chat_display.append("<i style='color: #888;'>🧠 Thinking...</i>")
            self.chat_display.append("<i style='color: #666; margin-left: 20px;'>")

        # Insert thinking content
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.scroll_to_bottom()

