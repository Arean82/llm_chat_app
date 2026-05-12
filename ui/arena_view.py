# ui/arena_view.py
import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader

from logic.chat_worker import ChatWorker
from utils.path_utils import get_resource_path
from ui.shared_widgets import ChatDisplay # shared widget type

class ArenaViewWidget(QWidget):
    def __init__(self, window, llm_client, theme_manager, formatter):
        super().__init__(window)
        self.window = window
        self.llm_client = llm_client
        self.theme_manager = theme_manager
        self.formatter = formatter

        # Parallel Session State
        self.model_a_id = None
        self.model_b_id = None
        self.worker_a = None
        self.worker_b = None
        self.is_generating = False

        # Load & Assemble
        loader = QUiLoader()
        ui_path = get_resource_path("ui_designer/arena_mode.ui")
        self.ui = loader.load(str(ui_path), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)

        # Inject shared rich text browsers
        self.chat_a = ChatDisplay()
        self.ui.chat_display_layout_a.replaceWidget(self.ui.chat_display_a, self.chat_a)
        self.ui.chat_display_a.setParent(None)
        
        self.chat_b = ChatDisplay()
        self.ui.chat_display_layout_b.replaceWidget(self.ui.chat_display_b, self.chat_b)
        self.ui.chat_display_b.setParent(None)

        # Link Elements
        self.ui.model_btn_a.clicked.connect(lambda: self.select_model("A"))
        self.ui.model_btn_b.clicked.connect(lambda: self.select_model("B"))
        self.ui.send_btn.clicked.connect(self.handle_duel_action)

        # Gamification Connectors
        self.ui.vote_a_btn.clicked.connect(lambda: self.elect_winner("A"))
        self.ui.vote_b_btn.clicked.connect(lambda: self.elect_winner("B"))
        self.ui.blind_mode_check.stateChanged.connect(self.toggle_blind_mode)
        
        # Initially hide voting until generation ends
        self.ui.vote_a_btn.hide()
        self.ui.vote_b_btn.hide()

        self.ui.auth_btn.clicked.connect(self.window.handle_auth_button)
        self.ui.theme_toggle_btn.clicked.connect(self.window.toggle_theme)
        
        self.ui.input_field.installEventFilter(self.window)

    def select_model(self, slot):
        from ui.model_popup import ModelPopupClass
        # We utilize our standard popup but route selection to custom slot!
        d = ModelPopupClass(parent=self.window)
        if d.exec():
            mid = d.get_selected_model_id()
            if mid:
                is_blind = self.ui.blind_mode_check.isChecked()
                if slot == "A":
                    self.model_a_id = mid
                    display_text = "🎭 MODEL A" if is_blind else f"🔥 {mid}"
                    self.ui.model_btn_a.setText(display_text)
                    self.ui.model_btn_a.setStyleSheet("font: bold 12px; background: #0078d4; color: white; border-radius: 8px;")
                else:
                    self.model_b_id = mid
                    display_text = "🎭 MODEL B" if is_blind else f"❄️ {mid}"
                    self.ui.model_btn_b.setText(display_text)
                    self.ui.model_btn_b.setStyleSheet("font: bold 12px; background: #9c27b0; color: white; border-radius: 8px;")

    def toggle_blind_mode(self):
        is_blind = self.ui.blind_mode_check.isChecked()
        if self.model_a_id:
            self.ui.model_btn_a.setText("🎭 MODEL A" if is_blind else f"🔥 {self.model_a_id}")
        if self.model_b_id:
            self.ui.model_btn_b.setText("🎭 MODEL B" if is_blind else f"❄️ {self.model_b_id}")

    def handle_duel_action(self):
        if self.is_generating:
            self.stop_duel()
        else:
            self.initiate_duel()

    def initiate_duel(self):
        prompt = self.ui.input_field.toPlainText().strip()
        if not prompt: return
        if not self.model_a_id or not self.model_b_id:
            QMessageBox.warning(self, "Models Missing", "Please select BOTH models before initiating a duel!")
            return
            
        self.is_generating = True
        self.ui.send_btn.setText("⏹️ STOP DUEL")
        self.ui.send_btn.setStyleSheet("font: bold 14px; background-color: #333; color: white;")
        
        self.ui.input_field.clear()
        
        # Prepare Visual Clear
        self.chat_a.clear()
        self.chat_b.clear()
        self.ui.vote_a_btn.hide()
        self.ui.vote_b_btn.hide()
        
        self.chat_a.append(f"<b>Prompt:</b> {prompt}<hr>")
        self.chat_b.append(f"<b>Prompt:</b> {prompt}<hr>")
        
        # Parallel Workers Spawn
        payload = [{"role": "user", "content": prompt}]
        
        # 1. Launch Worker A
        client_a = self.clone_client(self.model_a_id)
        self.worker_a = ChatWorker(client_a, payload)
        self.ui.stats_a.setText("⚡ Starting Stream A...")
        self.worker_a.stream_chunk.connect(lambda txt: self.on_chunk(self.chat_a, txt))
        self.worker_a.metrics_received.connect(lambda m: self.ui.stats_a.setText(f"🏎️ {m['tps']} tok/s | {m['ttft']}s"))
        self.worker_a.finished.connect(self.check_all_finished)
        self.worker_a.start()

        # 2. Launch Worker B
        client_b = self.clone_client(self.model_b_id)
        self.worker_b = ChatWorker(client_b, payload)
        self.ui.stats_b.setText("⚡ Starting Stream B...")
        self.worker_b.stream_chunk.connect(lambda txt: self.on_chunk(self.chat_b, txt))
        self.worker_b.metrics_received.connect(lambda m: self.ui.stats_b.setText(f"🏎️ {m['tps']} tok/s | {m['ttft']}s"))
        self.worker_b.finished.connect(self.check_all_finished)
        self.worker_b.start()

    def clone_client(self, mid):
        """Helper to manufacture independent client instances to prevent threading state collide."""
        from logic.llm_client import LLMClient
        c = LLMClient()
        # Sync current loaded active credentials from central vault
        if self.llm_client.api_key: c.set_api_key(self.llm_client.api_key)
        if self.llm_client.google_api_key: c.set_google_api_key(self.llm_client.google_api_key)
        c.set_model(mid)
        return c

    def on_chunk(self, chat, text):
        cursor = chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        chat.setTextCursor(cursor)
        chat.insertPlainText(text)
        scrollbar = chat.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def check_all_finished(self):
        # If both report inactive, reset button
        a_done = not self.worker_a or not self.worker_a.isRunning()
        b_done = not self.worker_b or not self.worker_b.isRunning()
        if a_done and b_done:
            self.is_generating = False
            self.ui.send_btn.setText("⚔️ DUEL")
            self.ui.send_btn.setStyleSheet("font: bold 14px; background-color: #d32f2f; color: white; border-radius: 8px;")
            # Reveal voting nodes upon completion
            self.ui.vote_a_btn.show()
            self.ui.vote_b_btn.show()

    def elect_winner(self, winner_slot):
        # Reveal names instantly upon vote casting!
        self.ui.blind_mode_check.setChecked(False)
        self.toggle_blind_mode()
        
        winning_model = self.model_a_id if winner_slot == "A" else self.model_b_id
        loser_model = self.model_b_id if winner_slot == "A" else self.model_a_id
        
        celebration = QMessageBox(self)
        celebration.setWindowTitle("🏆 The Verdict is In!")
        celebration.setText(f"<h2>🏆 WINNER: {winning_model}</h2>")
        celebration.setInformativeText(f"You have officially crowned {winning_model} over {loser_model} in this duel!")
        celebration.exec()
        
        # Reset interface glow
        if winner_slot == "A":
             self.chat_a.setStyleSheet("border: 3px solid #2ecc71; border-radius: 8px;")
             self.chat_b.setStyleSheet("border: 1px solid #ccc; border-radius: 8px; opacity: 0.5;")
        else:
             self.chat_b.setStyleSheet("border: 3px solid #2ecc71; border-radius: 8px;")
             self.chat_a.setStyleSheet("border: 1px solid #ccc; border-radius: 8px; opacity: 0.5;")

    def stop_duel(self):
        if self.worker_a and self.worker_a.isRunning(): self.worker_a.terminate()
        if self.worker_b and self.worker_b.isRunning(): self.worker_b.terminate()
        self.is_generating = False
        self.check_all_finished()
        self.ui.stats_a.setText("Stopped.")
        self.ui.stats_b.setText("Stopped.")
