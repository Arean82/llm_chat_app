# ui/chat_view.py
import time
import json
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QFileDialog, QApplication, QListWidgetItem, QAbstractItemView, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QTextCursor

from logic.chat_worker import ChatWorker
from logic.conversation_manager import ConversationManager
from utils.path_utils import get_resource_path, get_app_settings
from utils.model_config import get_context_limit
from utils.constants import RESPONSE_BUFFER_CHARS

from ui.shared_widgets import MessageData, ChatDisplay

class ChatViewWidget(QWidget):
    def __init__(self, parent_window, llm_client, theme_manager, formatter):
        super().__init__(parent_window)
        self.window = parent_window # Reference to main shell
        self.llm_client = llm_client
        self.theme_manager = theme_manager
        self.formatter = formatter
        
        # Internal State
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
        self.chat_html_history = [] 

        # Load layout
        loader = QUiLoader()
        ui_file = get_resource_path("ui_designer/chat_mode.ui")
        self.ui = loader.load(str(ui_file), self)
        
        # Set standard layout wrapping the loaded widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        
        # 1. Inject custom ChatDisplay just like before
        old_chat = self.ui.chat_display
        self.chat_display = ChatDisplay()
        display_layout = self.ui.chat_display_layout
        display_layout.replaceWidget(old_chat, self.chat_display)
        old_chat.setParent(None)
        old_chat.deleteLater()

        # Connect localized widgets
        self.input_field = self.ui.input_field
        self.send_btn = self.ui.send_btn
        self.model_btn = self.ui.model_btn
        self.model_desc_label = self.ui.model_desc_label
        self.auth_btn = self.ui.auth_btn
        self.upload_btn = self.ui.upload_btn
        self.theme_toggle_btn = self.ui.theme_toggle_btn
        self.connection_status_btn = self.ui.connection_status_btn

        # Event filters from parent can be installed or replicated locally
        self.input_field.installEventFilter(self.window) # Let main window handle key hooks

        # Setup Connections
        self.send_btn.clicked.connect(self.handle_send_stop_toggle)
        self.model_btn.clicked.connect(self.window.show_model_popup)
        self.auth_btn.clicked.connect(self.window.handle_auth_button)
        self.upload_btn.clicked.connect(self.handle_upload)
        self.theme_toggle_btn.clicked.connect(self.window.toggle_theme)
        
        # Sidebar
        self.ui.new_chat_btn.clicked.connect(self.start_new_chat)
        self.ui.delete_all_btn.clicked.connect(self.clear_all_history)
        self.ui.chat_history_list.itemClicked.connect(self.load_selected_history)
        self.ui.chat_history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.chat_history_list.customContextMenuRequested.connect(self.show_history_context_menu)
        self.ui.chat_history_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.refresh_history_list()
        self.set_send_button_idle()

    # =========================================================
    # REFACTORED CHAT LOGIC METHODS FROM MAIN_WINDOW
    # =========================================================
    
    def set_chat_enabled(self, enabled):
        self.input_field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

    def update_model_ui(self, model_id):
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

        self.model_btn.setText(f"🤖 {name} ▼")
        if desc:
            self.model_desc_label.setText(desc)
            self.model_desc_label.setWordWrap(True)
            self.model_desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.model_desc_label.setVisible(True)
        else:
            self.model_desc_label.setVisible(False)

    def handle_upload(self):
        if self.is_generating: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Attach File", "", 
            "Code & Text Files (*.py *.js *.txt *.md *.json *.csv *.xml *.html *.css *.yaml *.yml);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_name = Path(file_path).name
                self.attached_files.append({'name': file_name, 'content': content})
                self.add_system_message(f"📎 Attached: {file_name}")
            except Exception as e:
                self.add_system_message(f"❌ Failed to read file: {str(e)}")

    def clear_attachments(self):
        self.attached_files = []
        self.input_field.setPlaceholderText("")

    def send_message(self, api_response_queue=None, custom_messages=None, custom_temp=None, custom_max_tokens=None):
        user_message = self.input_field.toPlainText().strip()
        if not user_message and not self.attached_files:
            return

        if not self.window.is_connected:
            QMessageBox.warning(self, "No Internet Connection", "Cannot send message.")
            return

        if not self.llm_client.has_api_key():
            self.window.open_settings()
            return
            
        if not self.llm_client.current_model:
            self.window.show_model_popup()
            return

        self.response_start_time = time.perf_counter()  
        self.input_field.clear()
        
        final_prompt = user_message
        if self.attached_files:
            attachment_blocks = [f"--- File: {f['name']} ---\n```\n{f['content']}\n```" for f in self.attached_files]
            combined_text = "\n\n".join(attachment_blocks)
            final_prompt = f"{combined_text}\n\nUser Request: {user_message}" if user_message else f"{combined_text}\n\nPlease review the attached file(s)."
            self.clear_attachments()

        self.add_user_message(user_message if user_message else "📎 Sent attached file(s).")
        self.chat_history.append({"role": "user", "content": final_prompt})
        
        # Context Buffer / Compression Check
        TOKEN_BUFFER = 2000
        estimated_new_tokens = len(final_prompt) // 3
        current_total_estimate = self.total_tokens + estimated_new_tokens
        token_limit = get_context_limit(self.llm_client.current_model)
        usage_percent = (current_total_estimate / token_limit) * 100
        
        if (token_limit - current_total_estimate) < TOKEN_BUFFER or usage_percent > 85:
             self.attempt_adaptive_compression(api_response_queue, custom_messages, custom_temp, custom_max_tokens)
        else:
             self._continue_send_message(api_response_queue, custom_messages, custom_temp, custom_max_tokens)

    def attempt_adaptive_compression(self, api_queue, c_msgs, c_temp, c_max):
        self.add_system_message("⚡ *Context Optimization Activated...*")
        self.input_field.setEnabled(False)
        self.add_typing_indicator()

        base_history = [m for m in self.chat_history if m.get('role') != 'system']
        if len(base_history) < 3:
             self.remove_typing_indicator()
             self._continue_send_message(api_queue, c_msgs, c_temp, c_max)
             return

        pack_count = max(2, int(len(base_history) * 0.60))
        candidates = base_history[:pack_count]
        blueprint = [{"role": "system", "content": "Synthesize the following conversation into ONE highly dense technical paragraph."}]
        for entry in candidates:
             blueprint.append({"role": "user", "content": f"[{entry.get('role', 'user').upper()}]: {entry.get('content', '')}"})
        blueprint.append({"role": "user", "content": "Execute synthesis."})

        self.compactor_thread = ChatWorker(self.llm_client, blueprint, temperature=0.2, max_tokens=500)
        self.compactor_thread.stream = False

        def on_compaction_resolved(text_summary):
             self.remove_typing_indicator()
             pruned = 0
             remaining = []
             for m in self.chat_history:
                  if m.get('role') != 'system' and pruned < pack_count:
                       pruned += 1
                       continue
                  remaining.append(m)
             self.chat_history = remaining
             self.chat_history.insert(0, {"role": "system", "content": f"📊 CONSOLIDATED MEMORY RECAP: {text_summary.strip()}"})
             self.total_tokens = sum(len(m.get('content', '')) // 3 for m in self.chat_history)
             self.add_system_message("✨ *Context Optimized.*")
             self._continue_send_message(api_queue, c_msgs, c_temp, c_max)

        def on_compaction_fault(error_string):
             self.remove_typing_indicator()
             self.add_system_message(f"⚠️ *Optimization Bypassed.*")
             self._continue_send_message(api_queue, c_msgs, c_temp, c_max)

        self.compactor_thread.response_received.connect(on_compaction_resolved)
        self.compactor_thread.error_occurred.connect(on_compaction_fault)
        self.compactor_thread.start()

    def _continue_send_message(self, api_queue=None, custom_msgs=None, c_temp=None, c_max=None):
        self.input_field.setEnabled(False)
        self.add_typing_indicator()
        self.current_response_text = "" 
        
        settings = get_app_settings()
        use_defaults = settings.value("gen_use_defaults", "false") == "true"
        
        if use_defaults and c_temp is None and c_max is None:
            a_temp = None
            a_tokens = None
        else:
            a_temp = c_temp if c_temp is not None else float(settings.value("gen_temperature", 0.7))
            a_tokens = c_max if c_max is not None else int(settings.value("gen_max_tokens", 4096))
        
        api_payload = custom_msgs if custom_msgs is not None else self.get_messages_for_api()
        
        self.current_worker = ChatWorker(self.llm_client, api_payload, temperature=a_temp, max_tokens=a_tokens)    
        self.current_worker.stream_chunk.connect(self.on_stream_chunk)
        self.current_worker.thinking_chunk.connect(self.on_thinking_chunk)
        self.current_worker.response_received.connect(self.on_response_complete)
        self.current_worker.error_occurred.connect(self.on_error)

        if api_queue:
            self.current_worker.response_received.connect(lambda resp: api_queue.put(resp))
            self.current_worker.error_occurred.connect(lambda err: api_queue.put(f"Error: {err}"))

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
        html_content = self.formatter.format_ai_response(message)
        html = f"<b>Assistant:</b><br>{html_content}"
        self.chat_display.append(html)
        self.chat_html_history.append(html)
        self.scroll_to_bottom()

    def add_system_message(self, message: str):
        if not hasattr(self, 'chat_display'): return
        color = self.theme_manager.get_system_message_color()
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
        if not self.window.is_connected:
            self.window.is_connected = True
            self.window.update_connection_icon()

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

    def on_thinking_chunk(self, chunk: str):
        text = self.chat_display.toPlainText()
        if "🧠 Thinking..." not in text:
            if self.current_response_text == "":
                self.remove_typing_indicator()
            thinking_color = self.theme_manager.get_thinking_color()
            self.chat_display.append(f"<i style='color: {thinking_color};'>🧠 Thinking...</i>")
            if self.stream_start_position is None:
                self.stream_start_position = self.chat_display.textCursor().position()

        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertPlainText(chunk)
        self.scroll_to_bottom()

    def on_response_complete(self, full_response: str):
        self.chat_history.append({"role": "assistant", "content": full_response})
        if self.stream_start_position is not None:
            cursor = self.chat_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.setPosition(self.stream_start_position, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            html_content = self.formatter.format_ai_response(full_response)
            self.chat_display.insertHtml(f"<br>{html_content}<br>")
            copy_buttons = self.theme_manager.get_copy_button_html()
            self.chat_display.insertHtml(copy_buttons)
            self.chat_html_history.append(f"<b>Assistant:</b><br>{html_content}<br>{copy_buttons}")
            self.stream_start_position = None
            
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.movePosition(QTextCursor.StartOfBlock)
            block = cursor.block()
            block.setUserData(MessageData(full_response))
        else:
            self.chat_display.append("<b>Assistant:</b> ") 
            html = self.formatter.format_ai_response(full_response)
            self.chat_display.insertHtml(html)

        self.auto_save_current_chat()
        self.chat_display.insertHtml(self.theme_manager.get_copy_button_html())
        self.current_response_text = ""
        if self.response_start_time:
            elapsed = time.perf_counter() - self.response_start_time
            self.chat_display.append(f"<div style='color: #888888; font-size: 12px; text-align: right;'>⏱️ {elapsed:.2f}s</div>")
        self.scroll_to_bottom()

    def on_metrics_received(self, metrics: dict):
        border_color = self.theme_manager.get_metrics_border_color()
        metrics_html = f"<div style='display: flex; gap: 15px; justify-content: flex-end; color: #888888; font-size: 11px; margin-top: 8px; border-top: 1px solid {border_color};'><span>⚡ TTFT: {metrics['ttft']}s</span><span>🚀 Speed: {metrics['tps']} tok/s</span><span>📝 Tokens: {metrics['prompt_tokens']} in / {metrics['completion_tokens']} out</span></div>"
        self.chat_display.append(metrics_html)
        self.total_tokens = metrics['prompt_tokens'] + metrics['completion_tokens']
        self.scroll_to_bottom()

    def on_error(self, error_message: str):
        self.remove_typing_indicator()
        err = error_message.lower()
        if "timeout" in err or "connection" in err or "network" in err:
            self.add_system_message("🌐 Network issue. Check connection.")
            self.window.force_disconnected_state()
        else:
            self.add_system_message(f"❌ Error: {error_message}")

        if self.is_generating:
            if self.chat_history and self.chat_history[-1]["role"] == "user": self.chat_history.pop()
            self.is_generating = False
            self.current_worker = None
            self.set_send_button_idle()

    def on_worker_finished(self):
        self.set_send_button_idle()
        self.input_field.setFocus()
        self.current_worker = None

    def stop_generation(self):
        self.clear_attachments()        
        w = self.current_worker
        self.current_worker = None  
        if w and w.isRunning():
            w.requestInterruption()
            w.quit()
            w.wait(3000)
            if w.isRunning(): w.terminate()
            
        self.remove_typing_indicator()
        self.chat_display.append(f"<br><i style='color: {self.theme_manager.get_terminate_color()};'>⏹️ Terminated</i><br>")
        if self.current_response_text:
            self.chat_history.append({"role": "assistant", "content": self.current_response_text})
        
        self.set_send_button_idle()
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def handle_send_stop_toggle(self):
        if self.is_generating: self.stop_generation()
        else: self.send_message()

    def set_send_button_idle(self):
        self.is_generating = False 
        self.send_btn.setText("Send")
        self.send_btn.setStyleSheet("""QPushButton { background-color: #0078d4; border-radius: 8px; padding: 12px; color: white; font-weight: bold; }""")
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)

    def set_send_button_generating(self):
        self.is_generating = True
        self.send_btn.setText("Stop")
        self.send_btn.setStyleSheet("""QPushButton { background-color: #d32f2f; border-radius: 8px; padding: 12px; color: white; font-weight: bold; }""")
        self.send_btn.setEnabled(True)

    def scroll_to_bottom(self):
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_chat(self):
        self.chat_display.clear()
        self.chat_history = []
        self.chat_html_history = []
        self.total_tokens = 0
        self.current_response_text = ""
        self.current_conv_id = None
        self.add_system_message("New conversation started")

    def start_new_chat(self):
        if self.chat_history:
            self.auto_save_current_chat()
        self.clear_chat()
        self.ui.chat_history_list.clearSelection()

    def get_messages_for_api(self):
        messages = []
        for msg in self.chat_history:
            if msg.get('role') == 'system':
                if "CONSOLIDATED MEMORY RECAP" in str(msg.get('content', '')):
                    messages.append(msg)
            else: messages.append(msg)
        
        library = []
        file_path = get_resource_path("resources/user_prompts.json")
        if Path(file_path).exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    library = json.load(f)
            except: pass

        active = [f"- {i.get('text', '')}" for i in library if i.get('checked', False) and i.get('text')]
        if active: messages.insert(0, {"role": "system", "content": "Instructions:\n" + "\n".join(active)})
        
        return [{"role": m['role'], "content": m['content'].strip()} for m in messages if m.get('content', '').strip()]

    def auto_save_current_chat(self):
        if not self.chat_history: return
        title = "New Conversation"
        for m in self.chat_history:
            if m['role'] == 'user':
                title = m['content'][:30] + "..."
                break
        is_new = (self.current_conv_id is None)
        self.current_conv_id = self.conversation_manager.save_conversation(
            self.chat_history, title=title, conv_id=self.current_conv_id,
            model_id=self.model_btn.text(), messages_html=json.dumps(self.chat_html_history)
        )
        if is_new: self.refresh_history_list()

    def refresh_history_list(self):
        self.ui.chat_history_list.clear()
        conversations = self.conversation_manager.get_all_conversations()
        for c_id, title, timestamp in conversations:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, c_id)
            item.setToolTip(f"Saved: {timestamp}")
            self.ui.chat_history_list.addItem(item)

    def load_selected_history(self, item):
        c_id = item.data(Qt.ItemDataRole.UserRole)
        if not c_id: return
        self.current_conv_id = c_id
        try:
            data = self.conversation_manager.load_conversation(c_id)
            if data and "messages" in data:
                self.chat_history = data["messages"]
                self.chat_display.clear()
                cached_html = data.get("messages_html")
                if cached_html:
                    try:
                        self.chat_html_history = json.loads(cached_html)
                        for chunk in self.chat_html_history: self.chat_display.append(chunk)
                    except: pass
                else:
                     for msg in self.chat_history:
                         if msg['role'] == 'user': self.add_user_message(msg['content'])
                         else: self.add_assistant_message(msg['content'])
                self.scroll_to_bottom()
        except: pass

    def clear_all_history(self):
        reply = QMessageBox.question(self, "Delete All", "Are you sure you want to delete ALL conversations?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.conversation_manager.clear_all()
            self.start_new_chat()
            self.refresh_history_list()

    def show_history_context_menu(self, pos):
        item = self.ui.chat_history_list.itemAt(pos)
        if not item: return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ Delete")
        if menu.exec(self.ui.chat_history_list.mapToGlobal(pos)) == delete_action:
            self.delete_specific_history(item)

    def delete_specific_history(self, item):
        c_id = item.data(Qt.ItemDataRole.UserRole)
        if not c_id: return
        reply = QMessageBox.question(self, "Delete", f"Delete '{item.text()}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.conversation_manager.delete_conversation(c_id)
            self.refresh_history_list()
            self.start_new_chat()
