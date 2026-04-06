# ui/main_window.py
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QSplitter, QApplication,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QSettings, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor, QIcon, QAction

from logic.llm_client import LLMClient
from logic.chat_worker import ChatWorker
from logic.conversation_manager import ConversationManager
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.conversation_manager = ConversationManager()
        self.chat_history = []  # Store conversation history
        self.current_worker = None
        self.current_conversation_id = None
        
        self.init_ui()
        self.setup_menu()
        self.load_settings()
        self.load_models()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("LLM Chat App - NVIDIA NIM")
        self.setMinimumSize(1000, 700)
        
        # Set window icon
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "app_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # ========== LEFT SIDEBAR ==========
        sidebar = self.create_sidebar()
        
        # ========== RIGHT CHAT AREA ==========
        chat_area = self.create_chat_area()
        
        # Add to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(chat_area, stretch=4)
        
    def create_sidebar(self):
        """Create the left sidebar with model list"""
        sidebar = QWidget()
        sidebar.setMaximumWidth(280)
        sidebar.setMinimumWidth(250)
        sidebar.setObjectName("sidebar")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🤖 LLM Chat")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Model selection label
        model_label = QLabel("Available Models")
        model_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(model_label)
        
        # Model list
        self.model_list = QListWidget()
        self.model_list.setMaximumHeight(400)
        self.model_list.itemClicked.connect(self.on_model_selected)
        layout.addWidget(self.model_list)
        
        # Current model display
        self.current_model_label = QLabel("Current: None")
        self.current_model_label.setWordWrap(True)
        self.current_model_label.setObjectName("current-model")
        layout.addWidget(self.current_model_label)
        
        layout.addStretch()
        
        # Settings button
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(self.settings_btn)
        
        # Status indicator
        self.status_label = QLabel("🔴 Not connected")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)
        
        return sidebar
        
    def create_chat_area(self):
        """Create the main chat area"""
        chat_area = QWidget()
        chat_area.setObjectName("chat-area")
        
        layout = QVBoxLayout(chat_area)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        self.chat_display.setObjectName("chat-display")
        layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask me anything about coding...")
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setObjectName("input-field")
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setObjectName("send-btn")
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        return chat_area
        
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
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
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        clear_action = QAction("Clear Chat", self)
        clear_action.triggered.connect(self.clear_chat)
        view_menu.addAction(clear_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def load_models(self):
        """Load available models into the list"""
        models = self.llm_client.get_available_models()
        for model in models:
            item = QListWidgetItem(f"{model['name']}\n{model['description']}")
            item.setData(Qt.ItemDataRole.UserRole, model['id'])
            item.setToolTip(model['description'])
            self.model_list.addItem(item)
            
        # Select first model by default
        if self.model_list.count() > 0:
            self.model_list.setCurrentRow(0)
            first_model_id = self.model_list.item(0).data(Qt.ItemDataRole.UserRole)
            self.llm_client.set_model(first_model_id)
            first_name = self.model_list.item(0).text().split('\n')[0]
            self.current_model_label.setText(f"Current: {first_name}")
            
    def on_model_selected(self, item):
        """Handle model selection from list"""
        model_id = item.data(Qt.ItemDataRole.UserRole)
        self.llm_client.set_model(model_id)
        model_name = item.text().split('\n')[0]
        self.current_model_label.setText(f"Current: {model_name}")
        self.add_system_message(f"Switched to model: {model_name}")
        
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            api_key = dialog.get_api_key()
            if api_key:
                self.llm_client.set_api_key(api_key)
                self.set_connected_status(True)
                settings = QSettings("LLMChatApp", "Settings")
                settings.setValue("api_key", api_key)
                
    def load_settings(self):
        """Load saved settings"""
        settings = QSettings("LLMChatApp", "Settings")
        api_key = settings.value("api_key", "")
        if api_key:
            self.llm_client.set_api_key(api_key)
            self.set_connected_status(True)
        else:
            self.open_settings()
            
    def set_connected_status(self, connected: bool):
        """Update connection status indicator"""
        if connected:
            self.status_label.setText("🟢 Connected to NVIDIA NIM")
            self.status_label.setProperty("connected", True)
            self.send_btn.setEnabled(True)
            self.input_field.setEnabled(True)
        else:
            self.status_label.setText("🔴 Not connected - Check Settings")
            self.status_label.setProperty("connected", False)
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            
        # Refresh stylesheet for status label
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
            
    def send_message(self):
        """Send user message to LLM"""
        user_message = self.input_field.text().strip()
        if not user_message:
            return
            
        if not self.llm_client.has_api_key():
            QMessageBox.warning(self, "No API Key", "Please configure your API key in Settings.")
            self.open_settings()
            return
            
        # Clear input
        self.input_field.clear()
        
        # Add user message to display
        self.add_user_message(user_message)
        
        # Add to history
        self.chat_history.append({"role": "user", "content": user_message})
        
        # Disable input while processing
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Show typing indicator
        self.add_typing_indicator()
        
        # Start worker thread
        self.current_worker = ChatWorker(self.llm_client, self.chat_history)
        self.current_worker.stream_chunk.connect(self.on_stream_chunk)
        self.current_worker.response_received.connect(self.on_response_complete)
        self.current_worker.error_occurred.connect(self.on_error)
        self.current_worker.finished.connect(self.on_worker_finished)
        self.current_worker.start()
        
    def add_user_message(self, message: str):
        """Add user message to chat display"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        
        self.chat_display.insertHtml(f"""
            <div class="message user-message">
                <div class="message-bubble">
                    <b>You</b><br>{self.escape_html(message)}
                </div>
            </div>
        """)
        self.scroll_to_bottom()
        
    def add_assistant_message(self, message: str):
        """Add assistant message to chat display"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        
        self.chat_display.insertHtml(f"""
            <div class="message assistant-message">
                <div class="message-bubble">
                    <b>🤖 Assistant</b><br>{self.format_code_blocks(message)}
                </div>
            </div>
        """)
        self.scroll_to_bottom()
        
    def add_system_message(self, message: str):
        """Add system message to chat display"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        
        self.chat_display.insertHtml(f"""
            <div class="system-message">
                ℹ️ {self.escape_html(message)}
            </div>
        """)
        self.scroll_to_bottom()
        
    def add_typing_indicator(self):
        """Show typing indicator"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        
        self.chat_display.insertHtml("""
            <div id="typing-indicator" class="typing-indicator">
                <div class="message-bubble">
                    <b>🤖 Assistant</b><br><i>Typing...</i>
                </div>
            </div>
        """)
        self.scroll_to_bottom()
        
    def remove_typing_indicator(self):
        """Remove typing indicator"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
        if "Typing..." in cursor.selectedText():
            cursor.removeSelectedText()
        
    def on_stream_chunk(self, chunk: str):
        """Handle streaming response chunk"""
        if self.chat_display.toPlainText().endswith("Typing..."):
            self.remove_typing_indicator()
        
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.scroll_to_bottom()
        
    def on_response_complete(self, full_response: str):
        """Handle complete response"""
        self.chat_history.append({"role": "assistant", "content": full_response})
        
    def on_error(self, error_message: str):
        """Handle API error"""
        self.remove_typing_indicator()
        self.add_system_message(f"Error: {error_message}")
        
    def on_worker_finished(self):
        """Re-enable input after response completes"""
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.current_worker = None
        
    def scroll_to_bottom(self):
        """Scroll chat display to bottom"""
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def new_conversation(self):
        """Start a new conversation"""
        if self.chat_history:
            reply = QMessageBox.question(
                self, "New Conversation",
                "Start a new conversation? Current chat will be cleared.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.clear_chat()
                
    def clear_chat(self):
        """Clear the current chat"""
        self.chat_display.clear()
        self.chat_history = []
        self.current_conversation_id = None
        self.add_system_message("New conversation started")
        
    def save_conversation(self):
        """Save current conversation to file"""
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
        """Load a saved conversation"""
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
        """Show about dialog"""
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
        """Format code blocks with basic HTML"""
        import re
        text = self.escape_html(text)
        
        # Replace ```code``` with styled blocks
        pattern = r'```(\w*)\n(.*?)```'
        replacement = r'<pre class="code-block"><code>\2</code></pre>'
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)
        
        # Replace inline code
        text = re.sub(r'`(.*?)`', r'<code class="inline-code">\1</code>', text)
        
        # Convert newlines to <br>
        text = text.replace('\n', '<br>')
        
        return text
        
    def escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }
        return "".join(html_escape_table.get(c, c) for c in text)