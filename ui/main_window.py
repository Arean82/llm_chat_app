# ui/main_window.py
# Main application window for LLM Chat App

import sys
import os
from pathlib import Path
import re

import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QLabel, QVBoxLayout, QWidget, QApplication
from PySide6.QtCore import QEvent, QTimer, Qt, QSettings
from PySide6.QtGui import QAction
from PySide6.QtUiTools import QUiLoader

from logic.llm_client import LLMClient
from logic.chat_worker import ChatWorker
from logic.conversation_manager import ConversationManager
# Note: settings_dialog is imported inside open_settings() to avoid circular issues if needed

from PySide6.QtWidgets import QSizePolicy 

class MainWindowClass(QMainWindow):
    def __init__(self):
        super().__init__()
        
        print("MainWindowClass.__init__ starting...")
        
        loader = QUiLoader()
        ui_file = Path(__file__).parent.parent / "ui_designer" / "main_window.ui"
        
        if not ui_file.exists():
            self.setup_fallback_ui()
            return

        self.setWindowTitle("LLM Chat Application")

        self.ui = loader.load(str(ui_file))
        if self.ui is None:
            self.setup_fallback_ui()
            return
        
        self.setCentralWidget(self.ui)
        
        # NEW WIDGETS (No more sidebar/status_label)
        self.chat_display = self.ui.chat_display
        self.input_field = self.ui.input_field
        self.send_btn = self.ui.send_btn
        self.model_btn = self.ui.model_btn
        self.auth_btn = self.ui.auth_btn

        # STATE VARIABLES
        self.llm_client = LLMClient()
        self.conversation_manager = ConversationManager()
        self.chat_history = []
        self.current_worker = None
        self.current_response_text = ""
        self.response_start_time = None
        self.is_generating = False
        self.stream_start_position = None
        
        # SETUP
        self.setup_menu_bar()   
        self.setup_connections()
        self.load_settings()    # Triggers first-run popups
        
        print("MainWindowClass.__init__ completed")

    def setup_fallback_ui(self):
        print("Setting up fallback UI...")
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        label = QLabel("UI file failed to load.")
        layout.addWidget(label)
        self.setCentralWidget(central_widget)

    def setup_menu_bar(self):
        """Build menu bar purely in Python"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background-color: #1e1e1e; color: #d4d4d4; }
            QMenuBar::item:selected { background-color: #0078d4; }
            QMenu { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; }
            QMenu::item:selected { background-color: #0078d4; }
        """)
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Conversation", self.new_conversation)
        file_menu.addSeparator()
        file_menu.addAction("Save Conversation", self.save_conversation)
        file_menu.addAction("Load Conversation", self.load_conversation)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Readme", self.show_readme)
        help_menu.addAction("License", self.show_license)
        help_menu.addSeparator()
        help_menu.addAction("About", self.show_about)
        
    def setup_connections(self):
        self.send_btn.clicked.connect(self.handle_send_stop_toggle)
        self.input_field.returnPressed.connect(self.send_message)
        self.model_btn.clicked.connect(self.show_model_popup)
        self.auth_btn.clicked.connect(self.handle_auth_button)
        
    def load_models(self):
        pass # Models handled by popup now

    # ---------------------------------------------------------
    # NEW: FIRST-RUN LOGIC & POPUP HANDLERS
    # ---------------------------------------------------------

    def load_settings(self):
        settings = QSettings("LLMChatApp", "Settings")
        api_key = settings.value("api_key", "")
        model_id = settings.value("current_model_id", "")
        
        has_key = bool(api_key)
        has_model = bool(model_id)
        
        # FORCE button state on startup
        if has_key:
            self.llm_client.set_api_key(api_key) 
            self.auth_btn.setText("Logout")
            self.auth_btn.setStyleSheet("""
                QPushButton { background-color: #d32f2f; border: none; border-radius: 5px; padding: 8px 20px; color: white; font-weight: bold; }
                QPushButton:hover { background-color: #b71c1c; }
            """)
        else:
            self.auth_btn.setText("Login")
            self.auth_btn.setStyleSheet("""
                QPushButton { background-color: #0078d4; border: none; border-radius: 5px; padding: 8px 20px; color: white; font-weight: bold; }
                QPushButton:hover { background-color: #106ebe; }
            """)
        
        if has_model:
            model_name = self.get_model_name_by_id(model_id)
            self.model_btn.setText(f"🤖 {model_name} ▼")
            self.model_btn.setEnabled(True)
            self.llm_client.set_model(model_id)
        else:
            self.model_btn.setText("Select Model ▼")
            self.model_btn.setEnabled(False)
            
        self.set_chat_enabled(has_key and has_model)
        
    def handle_auth_button(self):
        if self.llm_client.has_api_key():
            self.logout()
        else:
            self.open_settings()

    def open_settings(self):
        from ui.login_dialog import SettingsDialogClass
        dialog = SettingsDialogClass(self)
        if dialog.exec():
            api_key = dialog.get_api_key()
            if api_key:
                self.llm_client.set_api_key(api_key)
                self.set_connected_status(True)
                QSettings("LLMChatApp", "Settings").setValue("api_key", api_key)
                
                if not QSettings("LLMChatApp", "Settings").value("current_model_id"):
                    QTimer.singleShot(100, self.show_model_popup)
                else:
                    self.set_chat_enabled(True)
                    self.model_btn.setEnabled(True)
            return True   #  User clicked Save
        else:
            return False  #  User clicked Cancel/X

    def show_model_popup(self):
        from ui.model_popup import ModelPopupClass
        
        current_id = QSettings("LLMChatApp", "Settings").value("current_model_id", "")
        dialog = ModelPopupClass(current_model_id=current_id, parent=self)
        
        if dialog.exec():
            selected_id = dialog.get_selected_model_id()
            if selected_id:
                self.llm_client.set_model(selected_id)
                model_name = self.get_model_name_by_id(selected_id)
                self.model_btn.setText(f"🤖 {model_name} ▼")
                self.model_btn.setEnabled(True)
                self.set_chat_enabled(self.llm_client.has_api_key())
                self.add_system_message(f"Switched to model: {model_name}")

    def get_model_name_by_id(self, model_id):
        models_file = Path(__file__).parent.parent / "resources" / "models.json"
        if models_file.exists():
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for m in data.get("models", []):
                    if m['id'] == model_id:
                        return m['name']
        return model_id 

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
    # CHAT & STREAMING LOGIC
    # ---------------------------------------------------------

    def send_message(self):
        user_message = self.input_field.text().strip()
        if not user_message:
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
        self.add_user_message(user_message)
        self.chat_history.append({"role": "user", "content": user_message})
        
        self.input_field.setEnabled(False)
        self.add_typing_indicator()
        self.current_response_text = "" 
        
        self.current_worker = ChatWorker(self.llm_client, self.chat_history)
        self.current_worker.stream_chunk.connect(self.on_stream_chunk)
        self.current_worker.thinking_chunk.connect(self.on_thinking_chunk)
        self.current_worker.response_received.connect(self.on_response_complete)
        self.current_worker.error_occurred.connect(self.on_error)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()
        self.set_send_button_generating()

    def add_user_message(self, message: str):
        self.chat_display.append(f"<b>You:</b> {self.escape_html(message)}")
        self.scroll_to_bottom()
        
    def add_assistant_message(self, message: str):
        import markdown
        html = markdown.markdown(message, extensions=['extra', 'codehilite', 'fenced_code'])
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
        if self.current_response_text == "":
            self.remove_typing_indicator()
            self.chat_display.append("<b>🤖 Assistant:</b> ")
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

            html = markdown.markdown(full_response, extensions=['extra', 'codehilite', 'fenced_code'])
            html = html.replace('<pre>', '<pre style="background-color: #1e1e1e; border-left: 3px solid #0078d4; padding: 10px; border-radius: 5px; overflow-x: auto;">')
            html = html.replace('<code>', '<code style="font-family: Consolas, monospace; color: #d4d4d4;">')

            self.chat_display.insertHtml(f"<br>{html}<br>")
            self.stream_start_position = None
        else:
            self.add_assistant_message(full_response)

        self.current_response_text = ""
        if self.response_start_time:
            elapsed = time.perf_counter() - self.response_start_time
            self.chat_display.append(
                f"<div style='color: #888888; font-size: 12px; margin-top: 5px; text-align: right;'>"
                f"⏱️ {elapsed:.2f}s</div>"
            )
        self.scroll_to_bottom()

    def on_error(self, error_message: str):
        self.remove_typing_indicator()
        self.add_system_message(f"Error: {error_message}")
        
    def on_worker_finished(self):
        self.set_send_button_idle()
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.current_worker = None
        
    def scroll_to_bottom(self):
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ---------------------------------------------------------
    # STOP GENERATION & TOGGLE
    # ---------------------------------------------------------

    def stop_generation(self):
        worker = self.current_worker
        self.current_worker = None  
        
        if worker and worker.isRunning():
            worker.terminate()
            worker.wait()
            
        self.remove_typing_indicator()
        
        if self.response_start_time:
            elapsed = time.perf_counter() - self.response_start_time
            self.chat_display.append(
                f"<i style='color: #ff9800;'>⏹️ Generation terminated by user ({elapsed:.2f}s)</i><br>"
            )
        elif self.current_response_text:
            self.chat_display.append("<br><i style='color: #ff9800;'>⏹️ Generation terminated by user.</i><br>")
        else:
            self.chat_display.append("<br><i style='color: #ff9800;'>⏹️ Generation terminated by user.</i><br>")
        
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
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 8px;
                padding: 12px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
            QPushButton:disabled { background-color: #3c3c3c; color: #888; }
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
        self.current_response_text = ""
        self.stream_start_position = None
        self.response_start_time = None
        self.add_system_message("New conversation started")
        
    def save_conversation(self):
        if not self.chat_history:
            QMessageBox.information(self, "Nothing to Save", "No conversation to save.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Conversation", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.conversation_manager.save_conversation(self.chat_history, file_path)
            self.add_system_message(f"Conversation saved to {file_path}")
            
    def load_conversation(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Conversation", "", "JSON Files (*.json);;All Files (*)")
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
        about_text = """
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <h2 style="color: #0078d4; margin-bottom: 5px;">LLM Chat App</h2>
            <p><b>Version:</b> 3.0.0<br>
            <b>Developer:</b> Arean Narrayan</p>
            
            <hr style="border: 1px solid #eee; margin: 10px 0;">
            
            <p>A sleek, modern desktop application designed to seamlessly connect you 
            with cutting-edge Large Language Models via the NVIDIA NIM API.</p>
            
            <p><b>Key Features:</b></p>
            <ul>
                <li>Real-time streaming responses</li>
                <li>Seamlessly switch between multiple state-of-the-art AI models</li>
                <li>Rich text and code syntax rendering (Markdown)</li>
                <li>Save and load conversation histories locally</li>
                <li>Clean, adaptive user interface</li>
            </ul>
            
            <hr style="border: 1px solid #eee; margin: 10px 0;">
            
            <p style="font-size: 11px; color: #666;">
            Powered by <b>NVIDIA NIM</b> (Free Tier: 40 requests/min)<br>
            Built with <b>Python</b> & <b>PySide6</b></p>
        </div>
        """
        
        QMessageBox.about(self, "About LLM Chat App", about_text)

    def show_readme(self):
        from ui.file_viewer import FileViewerDialog
        # is_markdown=True, wider and taller window
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
        # is_markdown=False, smaller standard window
        dialog = FileViewerDialog(
            title="License", 
            file_names=["LICENSE", "LICENSE.txt", "License"], 
            is_markdown=False, 
            size=(630, 410), 
            parent=self
        )
        dialog.exec()

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

    def changeEvent(self, event):
        """Lock the window to maximized state"""
        if event.type() == QEvent.Type.WindowStateChange:
            is_maximized = self.windowState() & Qt.WindowState.WindowMaximized
            is_fullscreen = self.windowState() & Qt.WindowState.WindowFullScreen
            if not is_maximized and not is_fullscreen:
                QTimer.singleShot(0, self.showMaximized)
        super().changeEvent(event)

    def showEvent(self, event):
        """Show popups AFTER the main window is fully rendered"""
        super().showEvent(event)
        
        # Only run this logic the very first time the window opens
        if hasattr(self, '_initial_popups_shown'):
            return
            
        self._initial_popups_shown = True
        
        settings = QSettings("LLMChatApp", "Settings")
        api_key = settings.value("api_key", "")
        model_id = settings.value("current_model_id", "")
        
        if not api_key:
            success = self.open_settings()      # Opens Login popup
            if not success:
                QTimer.singleShot(0, QApplication.instance().quit)
                return
        elif not model_id:
            self.show_model_popup()   # Opens Model popup
        else:
            self.add_system_message("Ready to chat.")

    def logout(self):
        reply = QMessageBox.question(
            self, "Logout", 
            "Are you sure you want to logout? This will clear your session.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            settings = QSettings("LLMChatApp", "Settings")
            settings.remove("api_key")
            settings.remove("current_model_id")

            self.llm_client.api_key = None
            self.llm_client.client = None
            self.llm_client.current_model = None

            self.clear_chat()
            
            # FORCE button to Login
            self.auth_btn.setText("Login")
            self.auth_btn.setStyleSheet("""
                QPushButton { background-color: #0078d4; border: none; border-radius: 5px; padding: 8px 20px; color: white; font-weight: bold; }
                QPushButton:hover { background-color: #106ebe; }
            """)
            self.auth_btn.update()
            self.auth_btn.repaint()

            self.set_chat_enabled(False)
            self.model_btn.setText("Select Model ▼")
            self.model_btn.setEnabled(False)
            self.input_field.clear()

            self.add_system_message("✅ Logged out successfully.")
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showMaximized() 
            else:
                self.showFullScreen() 
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showMaximized()      
        else:
            super().keyPressEvent(event)

    def on_thinking_chunk(self, chunk: str):
        text = self.chat_display.toPlainText()
        if "🧠 Thinking..." not in text:
            if self.current_response_text == "":
                self.remove_typing_indicator()
            self.chat_display.append("<i style='color: #888;'>🧠 Thinking...</i>")
            if self.stream_start_position is None:
                self.stream_start_position = self.chat_display.textCursor().position()

        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.scroll_to_bottom()

    def setup_chat_styles(self):
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: none;
                padding: 20px;
                font-size: 15px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            p { margin: 8px 0; line-height: 1.6; }
            b, strong { color: #ffffff; font-weight: 600; }
            i, em { color: #b0b0b0; }
            ul, ol { margin-left: 20px; margin-top: 5px; margin-bottom: 5px; }
            li { margin-bottom: 4px; }
            blockquote {
                border-left: 4px solid #0078d4;
                background-color: #252526;
                padding: 10px 15px;
                margin: 10px 0;
                border-radius: 0 5px 5px 0;
                color: #cccccc;
            }
            table {
                border-collapse: collapse;
                margin: 10px 0;
                width: 100%;
                background-color: #252526;
                border-radius: 5px;
                overflow: hidden;
            }
            th, td {
                border: 1px solid #404040;
                padding: 8px 12px;
                text-align: left;
            }
            th { background-color: #2d2d2d; color: #ffffff; font-weight: bold; }
            code:not(pre code) {
                background-color: #2d2d2d;
                color: #ce9178;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 13px;
            }   
            b { font-size: 14px; }
        """)

    def format_ai_response(self, text: str) -> str:
        import markdown
        html = markdown.markdown(text, extensions=['extra', 'fenced_code'])
        pattern = r'<pre><code(?:\s+class="language-(\w+)")?>(.*?)</code></pre>'

        def replacer(match):
            lang = match.group(1) or "code"
            code_content = match.group(2)
            return f'''
            <div style="background-color: #1e1e1e; border-radius: 8px; margin: 12px 0; overflow: hidden; border: 1px solid #404040; font-family: Consolas, 'Courier New', monospace;">
                <div style="background-color: #2d2d2d; padding: 8px 15px; color: #858585; font-size: 12px; font-family: 'Segoe UI', Arial, sans-serif; border-bottom: 1px solid #404040;">
                    {lang.upper()}
                </div>
                <pre style="margin: 0; padding: 15px; background-color: #1e1e1e; overflow-x: auto; color: #d4d4d4; font-size: 14px; line-height: 1.5;"><code>{code_content}</code></pre>
            </div>
            '''
        formatted_html = re.sub(pattern, replacer, html, flags=re.DOTALL)
        return formatted_html

