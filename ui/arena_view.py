# ui/arena_view.py
import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QFileDialog
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
        
        # Default Model A to current active chat selection
        self.model_a_id = self.llm_client.current_model
        
        # Response Memory Cache for Exporter
        self.current_prompt = ""
        self.response_a = ""
        self.response_b = ""

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

        # Initial Model A Display
        if self.model_a_id:
            self.ui.model_btn_a.setText(f"🔥 {self.model_a_id}")
            self.ui.model_btn_a.setStyleSheet("font: bold 12px; background: #0078d4; color: white; border-radius: 6px; padding: 6px;")

        # UI Element Connections
        self.ui.theme_toggle_btn.clicked.connect(self.window.toggle_theme)
        self.ui.warning_btn.clicked.connect(self.show_ecosystem_warning)
        self.check_ecosystems()
        
        self.ui.input_field.installEventFilter(self.window)

    def check_ecosystems(self):
        """Checks if multiple ecosystems are configured; shows warning if not."""
        import keyring
        connected_count = 0
        # Check primary ecosystems
        if keyring.get_password("LLMChatApp", "api_key_nvidia") or keyring.get_password("LLMChatApp", "api_key"):
            connected_count += 1
        if keyring.get_password("LLMChatApp", "api_key_google"):
            connected_count += 1
            
        # If still 0 or 1, check the new Hub's custom providers
        if connected_count < 2:
             from utils.path_utils import get_app_settings
             import json
             custom = json.loads(get_app_settings().value("custom_providers", "[]"))
             for p in custom:
                 eco_key = p['ecosystem'].lower().replace(' ', '_')
                 if keyring.get_password("LLMChatApp", f"api_key_{p['sdk']}_{eco_key}"):
                     connected_count += 1
        
        if connected_count < 2:
            self.ui.warning_btn.show()
            self.ui.warning_btn.setText("⚠️ Benchmark limited - Click for details")
        else:
            self.ui.warning_btn.hide()

    def show_ecosystem_warning(self):
        msg = ("Only 1 ecosystem is available.\n\n"
               "For a true cross-provider duel (e.g. NVIDIA vs Google), you need at least 2.\n\n"
               "To add an ecosystem, go to Settings > Credential Manager.")
        QMessageBox.information(self, "Arena Warning", msg)

    def select_model(self, slot):
        from ui.model_popup import ModelPopupClass
        # We utilize our standard popup but force 'Show All' mode for Arena duels!
        d = ModelPopupClass(parent=self.window, force_show_all=True)
        if d.exec():
            mid = d.get_selected_model_id()
            if mid:
                is_blind = self.ui.blind_mode_check.isChecked()
                if slot == "A":
                    self.model_a_id = mid
                    display_text = "🎭 MODEL A" if is_blind else f"🔥 {mid}"
                    self.ui.model_btn_a.setText(display_text)
                    self.ui.model_btn_a.setStyleSheet("font: bold 12px; background: #0078d4; color: white; border-radius: 6px; padding: 6px;")
                else:
                    self.model_b_id = mid
                    display_text = "🎭 MODEL B" if is_blind else f"❄️ {mid}"
                    self.ui.model_btn_b.setText(display_text)
                    self.ui.model_btn_b.setStyleSheet("font: bold 12px; background: #9c27b0; color: white; border-radius: 6px; padding: 6px;")

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

        # --- SECURITY GATE: Verify Credentials for both competitors ---
        temp_a = self.clone_client(self.model_a_id)
        temp_b = self.clone_client(self.model_b_id)
        if not temp_a.has_api_key() or not temp_b.has_api_key():
             QMessageBox.warning(self, "Authentication Required", 
                 "One or both of the selected models require API keys that are not configured.\n\n"
                 "Please set up your credentials in the Settings dialog.")
             self.window.open_settings()
             return
            
        self.is_generating = True
        self.ui.send_btn.setText("⏹️ STOP DUEL")
        self.ui.send_btn.setStyleSheet("font: bold 14px; background-color: #333; color: white; border-radius: 6px;")
        
        self.ui.input_field.clear()
        
        # Prepare Visual Clear
        self.chat_a.clear()
        self.chat_b.clear()
        self.ui.vote_a_btn.hide()
        self.ui.vote_b_btn.hide()
        
        # Reset interface glow by restoring theme-compliant base stylesheets
        base_styles = self.theme_manager.get_chat_styles()
        self.chat_a.setStyleSheet(base_styles)
        self.chat_b.setStyleSheet(base_styles)
        
        self.chat_a.append(f"<b>Prompt:</b> {self.formatter.escape_html(prompt)}<hr>")
        self.chat_b.append(f"<b>Prompt:</b> {self.formatter.escape_html(prompt)}<hr>")
        
        # Cache session for reporting engine
        self.current_prompt = prompt
        self.response_a = ""
        self.response_b = ""
        
        # Load dynamic generation override settings consistent with standard chat behavior
        from utils.path_utils import get_app_settings
        settings = get_app_settings()
        use_defaults = settings.value("gen_use_defaults", "false") == "true"
        
        if use_defaults:
            a_temp = None
            a_tokens = None
        else:
            a_temp = float(settings.value("gen_temperature", 0.7))
            a_tokens = int(settings.value("gen_max_tokens", 4096))
            
        # Construct standard payload leveraging unified system instructions if active
        from utils.helpers import get_active_system_instructions
        payload = []
        sys_instr = get_active_system_instructions()
        if sys_instr:
            payload.append({"role": "system", "content": sys_instr})
        payload.append({"role": "user", "content": prompt})
        
        # 1. Launch Worker A
        client_a = self.clone_client(self.model_a_id)
        self.worker_a = ChatWorker(client_a, payload, temperature=a_temp, max_tokens=a_tokens)
        self.ui.stats_a.setText("⚡ Starting Stream A...")
        self.worker_a.stream_chunk.connect(lambda txt: self.on_chunk(self.chat_a, txt))
        self.worker_a.response_received.connect(self._store_response_a)
        self.worker_a.metrics_received.connect(lambda m: self.ui.stats_a.setText(f"🏎️ {m['tps']} tok/s | {m['ttft']}s"))
        self.worker_a.finished.connect(self.check_all_finished)
        self.worker_a.start()

        # 2. Launch Worker B
        client_b = self.clone_client(self.model_b_id)
        self.worker_b = ChatWorker(client_b, payload, temperature=a_temp, max_tokens=a_tokens)
        self.ui.stats_b.setText("⚡ Starting Stream B...")
        self.worker_b.stream_chunk.connect(lambda txt: self.on_chunk(self.chat_b, txt))
        self.worker_b.response_received.connect(self._store_response_b)
        self.worker_b.metrics_received.connect(lambda m: self.ui.stats_b.setText(f"🏎️ {m['tps']} tok/s | {m['ttft']}s"))
        self.worker_b.finished.connect(self.check_all_finished)
        self.worker_b.start()

    def clone_client(self, mid):
        """Helper to manufacture independent client instances tailored to the specific targeted model provider."""
        from logic.llm_client import LLMClient
        from utils.path_utils import get_app_settings
        import keyring
        import json
        
        c = LLMClient()
        c.set_model(mid)
        provider = c.get_current_provider()
        
        # 1. Always copy the Google API key (Google SDK ignores base_url logic)
        if self.llm_client.google_api_key: 
            c.set_google_api_key(self.llm_client.google_api_key)
            
        # 2. Target the exact provider silo from existing user credentials
        if provider != "google":
             settings = get_app_settings()
             
             # Normalization for matching
             def normalize(p):
                 return str(p).lower().replace(" ", "").replace("_", "").replace("-", "")
             
             p_norm = normalize(provider)
             
             # Attempt to find the SDK and URL for this provider in custom_providers
             custom = json.loads(settings.value("custom_providers", "[]"))
             target_url = None
             target_key = None
             
             # Priority A: Check the new Hub structure
             for cp in custom:
                 if normalize(cp['ecosystem']) == p_norm:
                     target_url = cp['url']
                     eco_key = cp['ecosystem'].lower().replace(' ', '_')
                     target_key = keyring.get_password("LLMChatApp", f"api_key_{cp['sdk']}_{eco_key}")
                     break
             
             # Priority B: Fallback to standard silos if not in custom Hub
             if not target_url:
                 target_url = settings.value(f"url_{provider}") or settings.value("base_url")
             
             if not target_key:
                 target_key = keyring.get_password("LLMChatApp", f"api_key_{provider}")
                 
             # Priority C: Global Fallbacks
             if not target_key:
                 target_key = keyring.get_password("LLMChatApp", "api_key") or keyring.get_password("LLMChatApp", "api_key_nvidia")
             
             if target_url: c.set_base_url(target_url)
             if target_key: c.set_api_key(target_key)
             
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
            self.ui.send_btn.setStyleSheet("font: bold 14px; background-color: #d32f2f; color: white; border-radius: 6px;")
            # Reveal voting nodes upon completion
            self.ui.vote_a_btn.show()
            self.ui.vote_b_btn.show()

            # --- RENDER RICH MARKDOWN HTML FOR BOTH RESPONSES ---
            # Overwrite raw stream buffer with beautifully styled, complete Markdown components
            if self.response_a:
                html_a = self.formatter.format_ai_response(self.response_a)
                self.chat_a.clear()
                self.chat_a.append(f"<b>Prompt:</b> {self.formatter.escape_html(self.current_prompt)}<hr>")
                self.chat_a.insertHtml(html_a)
            
            if self.response_b:
                html_b = self.formatter.format_ai_response(self.response_b)
                self.chat_b.clear()
                self.chat_b.append(f"<b>Prompt:</b> {self.formatter.escape_html(self.current_prompt)}<hr>")
                self.chat_b.insertHtml(html_b)

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
        
        # PROPOSED: Automated Reporting Feature Injection
        save_btn = celebration.addButton("💾 Save Report (.md)", QMessageBox.ActionRole)
        celebration.addButton("Close", QMessageBox.AcceptRole)
        
        celebration.exec()
        
        if celebration.clickedButton() == save_btn:
             self.export_duel_report(winning_model, loser_model)
        
        # Reset interface glow ensuring theme compliance (do not clear existing chat stylesheets)
        base_styles = self.theme_manager.get_chat_styles()
        if winner_slot == "A":
             self.chat_a.setStyleSheet(base_styles + "\nQTextEdit { border: 3px solid #2ecc71; border-radius: 8px; }")
             self.chat_b.setStyleSheet(base_styles + "\nQTextEdit { border: 1px solid #ccc; border-radius: 8px; opacity: 0.5; }")
        else:
             self.chat_b.setStyleSheet(base_styles + "\nQTextEdit { border: 3px solid #2ecc71; border-radius: 8px; }")
             self.chat_a.setStyleSheet(base_styles + "\nQTextEdit { border: 1px solid #ccc; border-radius: 8px; opacity: 0.5; }")

    def stop_duel(self):
        if self.worker_a and self.worker_a.isRunning(): self.worker_a.terminate()
        if self.worker_b and self.worker_b.isRunning(): self.worker_b.terminate()
        self.is_generating = False
        self.check_all_finished()
        self.ui.stats_a.setText("Stopped.")
        self.ui.stats_b.setText("Stopped.")

    # ---------------------------------------------------------
    # PRIVATE REPORTERS & CACHE HELPERS
    # ---------------------------------------------------------
    def _store_response_a(self, text): self.response_a = text
    def _store_response_b(self, text): self.response_b = text

    def export_duel_report(self, winner, loser):
        """Manufactures and prompts to save an archival Markdown verdict record."""
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Duel Report", f"duel_report_{stamp}.md", 
            "Markdown Files (*.md);;All Files (*)"
        )
        if not file_path: return
        
        w_text = self.response_a if winner == self.model_a_id else self.response_b
        l_text = self.response_b if winner == self.model_a_id else self.response_a
        
        report_body = f"""# ⚔️ AI Duel Verdict Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 Input Prompt
> {self.current_prompt}

---

## 🏆 WINNER: {winner}
{w_text}

---

## 🥈 RUNNER-UP: {loser}
{l_text}

---
*This automated benchmark report was manufactured locally via the LLM Chat App Arena.*
"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_body)
            QMessageBox.information(self, "Report Saved", "The markdown verdict report has been securely archived.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failure", f"Failed to write report file:\n{str(e)}")

