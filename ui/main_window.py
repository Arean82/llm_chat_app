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
        
        # WIDGETS
        self.chat_display = self.ui.chat_display
        self.input_field = self.ui.input_field
        self.send_btn = self.ui.send_btn
        self.model_btn = self.ui.model_btn
        self.model_desc_label = self.ui.model_desc_label  # <--- ADDED
        self.auth_btn = self.ui.auth_btn
        self.upload_btn = self.ui.upload_btn 
        self.theme_toggle_btn = self.ui.theme_toggle_btn

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
        self.current_theme = "dark"  # "dark" or "light"

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

    # ---------------------------------------------------------
    # THEME SYSTEM
    # ---------------------------------------------------------

    def apply_theme(self, theme: str):
        """Apply dark or light theme to the entire window."""
        self.current_theme = theme
        QSettings("LLMChatApp", "Settings").setValue("theme", theme)

        # Set theme attribute on QMainWindow for QSS selectors
        self.setProperty("theme", theme)
        self.style().unpolish(self)
        self.style().polish(self)

        # Load the QSS file
        qss_file = Path(__file__).parent.parent / "styles" / "styles.qss"
        if qss_file.exists():
            with open(qss_file, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

        # Update toggle button icon
        if theme == "dark":
            self.theme_toggle_btn.setText("🌙")
        else:
            self.theme_toggle_btn.setText("☀️")

        # Apply menu bar theme
        self.apply_menu_bar_theme(theme)

        # Apply auth button theme (it has dynamic styles)
        self.refresh_auth_button_style()

        # Apply send button theme based on current state
        if self.is_generating:
            self.set_send_button_generating()
        else:
            self.set_send_button_idle()

    def toggle_theme(self):
        """Switch between dark and light theme."""
        if self.current_theme == "dark":
            self.apply_theme("light")
        else:
            self.apply_theme("dark")

    def apply_menu_bar_theme(self, theme: str):
        if theme == "dark":
            self.menuBar().setStyleSheet("""
                QMenuBar { background-color: #1e1e1e; color: #d4d4d4; }
                QMenuBar::item:selected { background-color: #0078d4; }
                QMenu { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; }
                QMenu::item:selected { background-color: #0078d4; }
            """)
        else:
            self.menuBar().setStyleSheet("""
                QMenuBar { background-color: #ffffff; color: #333333; border-bottom: 1px solid #e0e0e0; }
                QMenuBar::item:selected { background-color: #0078d4; color: white; }
                QMenu { background-color: #ffffff; color: #333333; border: 1px solid #e0e0e0; }
                QMenu::item:selected { background-color: #0078d4; color: white; }
            """)

    def refresh_auth_button_style(self):
        """Re-apply auth button style based on current theme and login state."""
        if self.llm_client.has_api_key():
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

    def get_code_block_style(self):
        """Return inline style for code blocks based on current theme."""
        if self.current_theme == "dark":
            return 'background-color: #1e1e1e; border-left: 3px solid #0078d4; padding: 10px; border-radius: 5px; overflow-x: auto;'
        else:
            return 'background-color: #f5f5f5; border-left: 3px solid #0078d4; padding: 10px; border-radius: 5px; overflow-x: auto;'

    def get_code_text_style(self):
        """Return inline style for code text based on current theme."""
        if self.current_theme == "dark":
            return "font-family: Consolas, monospace; color: #d4d4d4;"
        else:
            return "font-family: Consolas, monospace; color: #333333;"

    def get_system_message_color(self):
        if self.current_theme == "dark":
            return "#ffd700"
        else:
            return "#0078d4"

    def get_terminate_color(self):
        if self.current_theme == "dark":
            return "#ff9800"
        else:
            return "#e65100"

    def get_thinking_color(self):
        if self.current_theme == "dark":
            return "#888"
        else:
            return "#888888"

    def get_chat_styles(self):
        """Return full chat display stylesheet based on current theme."""
        if self.current_theme == "dark":
            return """
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
            """
        else:
            return """
                QTextEdit {
                    background-color: #ffffff;
                    color: #333333;
                    border: none;
                    padding: 20px;
                    font-size: 15px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                p { margin: 8px 0; line-height: 1.6; }
                b, strong { color: #000000; font-weight: 600; }
                i, em { color: #666666; }
                ul, ol { margin-left: 20px; margin-top: 5px; margin-bottom: 5px; }
                li { margin-bottom: 4px; }
                blockquote {
                    border-left: 4px solid #0078d4;
                    background-color: #f5f5f5;
                    padding: 10px 15px;
                    margin: 10px 0;
                    border-radius: 0 5px 5px 0;
                    color: #555555;
                }
                table {
                    border-collapse: collapse;
                    margin: 10px 0;
                    width: 100%;
                    background-color: #ffffff;
                    border-radius: 5px;
                    overflow: hidden;
                    border: 1px solid #e0e0e0;
                }
                th, td {
                    border: 1px solid #e0e0e0;
                    padding: 8px 12px;
                    text-align: left;
                }
                th { background-color: #f5f5f5; color: #333333; font-weight: bold; }
                code:not(pre code) {
                    background-color: #f0f0f0;
                    color: #d63384;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 13px;
                }   
                b { font-size: 14px; }
            """

    def get_metrics_border_color(self):
        if self.current_theme == "dark":
            return "#3c3c3c"
        else:
            return "#e0e0e0"

    # ---------------------------------------------------------
    # END THEME SYSTEM
    # ---------------------------------------------------------

    def setup_menu_bar(self):
        """Build menu bar purely in Python"""
        menubar = self.menuBar()
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
        self.upload_btn.clicked.connect(self.handle_upload)
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        
    def load_models(self):
        pass

    # ---------------------------------------------------------
    # FIRST-RUN LOGIC & POPUP HANDLERS
    # ---------------------------------------------------------

    def load_settings(self):
        settings = QSettings("LLMChatApp", "Settings")
        api_key = settings.value("api_key", "")
        model_id = settings.value("current_model_id", "")
        saved_theme = settings.value("theme", "dark")
        
        # Apply saved theme FIRST
        self.apply_theme(saved_theme)

        has_key = bool(api_key)
        has_model = bool(model_id)
        
        if has_key:
            self.llm_client.set_api_key(api_key) 
            self.refresh_auth_button_style()
        
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
            return True
        else:
            return False

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
        models_file = Path(__file__).parent.parent / "resources" / "models.json"
        if models_file.exists():
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for m in data.get("models", []):
                    if m['id'] == model_id:
                        return m['name']
        return model_id 

    def update_model_ui(self, model_id):
        """Updates the model button text and the description label."""
        models_file = Path(__file__).parent.parent / "resources" / "models.json"
        name = model_id
        desc = ""
        
        if models_file.exists():
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for m in data.get("models", []):
                    if m['id'] == model_id:
                        name = m.get('name', model_id)
                        desc = m.get('description', '')
                        break

        # Update button
        self.model_btn.setText(f"🤖 {name} ▼")
        
        # Update description label
        if desc:
            self.model_desc_label.setText(desc)
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

    def send_message(self):
        user_message = self.input_field.text().strip()
        
        if not user_message and not self.attached_files:
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
        
        self.input_field.setEnabled(False)
        self.add_typing_indicator()
        self.current_response_text = "" 
        
        self.current_worker = ChatWorker(self.llm_client, self.chat_history)        
        self.current_worker.stream_chunk.connect(self.on_stream_chunk)
        self.current_worker.thinking_chunk.connect(self.on_thinking_chunk)
        self.current_worker.response_received.connect(self.on_response_complete)
        self.current_worker.error_occurred.connect(self.on_error)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.metrics_received.connect(self.on_metrics_received)
        self.current_worker.start()
        self.set_send_button_generating()

    def add_user_message(self, message: str):
        self.chat_display.append(f"<b>You:</b> {self.escape_html(message)}")
        self.scroll_to_bottom()
        
    def add_assistant_message(self, message: str):
        import markdown
        html = markdown.markdown(message, extensions=['extra', 'codehilite', 'fenced_code'])
        html = html.replace('<pre>', f'<pre style="{self.get_code_block_style()}">')
        html = html.replace('<code>', f'<code style="{self.get_code_text_style()}">')
        self.chat_display.append(f"<b>🤖 Assistant:</b><br>{html}")
        self.scroll_to_bottom()
        
    def add_system_message(self, message: str):
        color = self.get_system_message_color()
        self.chat_display.append(f"<i style='color: {color};'>ℹ️ {self.escape_html(message)}</i>")
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
            html = html.replace('<pre>', f'<pre style="{self.get_code_block_style()}">')
            html = html.replace('<code>', f'<code style="{self.get_code_text_style()}">')

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
        self.clear_attachments()        
        worker = self.current_worker
        self.current_worker = None  
        
        if worker and worker.isRunning():
            worker.terminate()
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
        if self.current_theme == "dark":
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
            current_model = self.llm_client.current_model or ""
            self.conversation_manager.save_conversation(self.chat_history, file_path, current_model)
            self.add_system_message(f"Conversation saved to {file_path}")
            
    def load_conversation(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Conversation", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            data = self.conversation_manager.load_conversation(file_path)
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
        border_color = "#e0e0e0" if self.current_theme == "light" else "#3c3c3c"
        about_text = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <h2 style="color: #0078d4; margin-bottom: 5px;">LLM Chat App</h2>
            <p><b>Version:</b> 3.0.0<br>
            <b>Developer:</b> Arean Narrayan</p>
            
            <hr style="border: 1px solid {border_color}; margin: 10px 0;">
            
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
            
            <hr style="border: 1px solid {border_color}; margin: 10px 0;">
            
            <p style="font-size: 11px; color: #666666;">
            Powered by <b>NVIDIA NIM</b> (Free Tier: 40 requests/min)<br>
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
        api_key = settings.value("api_key", "")
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
                    return
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

        settings = QSettings("LLMChatApp", "Settings")
        settings.remove("api_key")
        settings.remove("current_model_id")
        settings.sync()

        self.llm_client.api_key = None
        self.llm_client.client = None
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
        import markdown
        html = markdown.markdown(text, extensions=['extra', 'fenced_code'])
        pattern = r'<pre><code(?:\s+class="language-(\w+)")?>(.*?)</code></pre>'

        if self.current_theme == "dark":
            code_bg = "#1e1e1e"
            code_text = "#d4d4d4"
            header_bg = "#2d2d2d"
            header_text = "#858585"
            header_border = "#404040"
            outer_border = "#404040"
        else:
            code_bg = "#f5f5f5"
            code_text = "#333333"
            header_bg = "#e8e8e8"
            header_text = "#666666"
            header_border = "#e0e0e0"
            outer_border = "#e0e0e0"

        def replacer(match):
            lang = match.group(1) or "code"
            code_content = match.group(2)
            return f'''
            <div style="background-color: {code_bg}; border-radius: 8px; margin: 12px 0; overflow: hidden; border: 1px solid {outer_border}; font-family: Consolas, 'Courier New', monospace;">
                <div style="background-color: {header_bg}; padding: 8px 15px; color: {header_text}; font-size: 12px; font-family: 'Segoe UI', Arial, sans-serif; border-bottom: 1px solid {header_border};">
                    {lang.upper()}
                </div>
                <pre style="margin: 0; padding: 15px; background-color: {code_bg}; overflow-x: auto; color: {code_text}; font-size: 14px; line-height: 1.5;"><code>{code_content}</code></pre>
            </div>
            '''
        formatted_html = re.sub(pattern, replacer, html, flags=re.DOTALL)
        return formatted_html