# logic/chat_worker.py
# RESTORED TO V6.1 STATE: Pure GUI Signal-based Worker.
from PySide6.QtCore import QThread, Signal
import time

class ChatWorker(QThread):
    stream_chunk = Signal(str)
    thinking_chunk = Signal(str)
    response_received = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()
    metrics_received = Signal(dict)

    def __init__(self, client, messages, temperature=0.7, max_tokens=4096, web_search_query=None, rag_engine=None, parent=None):
        super().__init__(parent)
        self.client = client
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.web_search_query = web_search_query
        self.rag_engine = rag_engine
        self.stream = True
        self._is_running = True

    def run(self):
        try:
            # 1. RAG/Context Augmentation (If Query provided)
            if self.web_search_query and self.rag_engine:
                try:
                    # In v6.1, we might inject a system note about retrieved context
                    context = self.rag_engine.search(self.web_search_query)
                    if context:
                        self.messages.insert(0, {"role": "system", "content": f"Context for research: {context}"})
                except Exception as e:
                    print(f"[Worker] RAG Augmentation failed: {e}")

            # 2. Provider Routing
            provider = self.client.get_current_provider()
            if provider == "google":
                self._run_google_loop()
            else:
                self._run_openai_loop()
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()

    def _run_google_loop(self):
        start_time = time.perf_counter()
        first_chunk_time = None
        chunk_count = 0
        full_response = ""
        
        from google.genai import types
        import base64

        system_instructions = ""
        mapped_history = []

        for msg in self.messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "system":
                system_instructions += (content if isinstance(content, str) else "") + "\n"
            else:
                fixed_role = "model" if role == "assistant" else "user"
                current_parts = []
                if isinstance(content, list):
                     for obj in content:
                          if obj.get('type') == 'text': current_parts.append(obj.get('text', ''))
                          elif obj.get('type') == 'image':
                               bin_blob = base64.b64decode(obj.get('data', ''))
                               current_parts.append(types.Part.from_bytes(data=bin_blob, mime_type=obj.get('mime')))
                else: current_parts = [content]
                
                if mapped_history and mapped_history[-1]["role"] == fixed_role:
                    mapped_history[-1]["parts"].extend(current_parts)
                else:
                    mapped_history.append({"role": fixed_role, "parts": current_parts})

        if not mapped_history: return
        active_node = mapped_history.pop()
        active_prompt = active_node["parts"]
        
        config = types.GenerateContentConfig(
            system_instruction=system_instructions.strip() if system_instructions else None,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens
        )
        
        if mapped_history and mapped_history[-1]["role"] == "user":
             last_item = mapped_history.pop()
             active_prompt = last_item["parts"] + active_prompt

        chat = self.client.google_client.chats.create(
            model=self.client.current_model,
            history=mapped_history,
            config=config
        )
        
        print(f"[Worker] Sending Google GenAI request for model: {self.client.current_model}")
        response = chat.send_message_stream(active_prompt) if self.stream else chat.send_message(active_prompt)

        if self.stream:
            for chunk in response:
                if not self._is_running: break
                try:
                    txt = chunk.text
                    if txt:
                        if first_chunk_time is None: first_chunk_time = time.perf_counter()
                        full_response += txt
                        chunk_count += len(txt.split())
                        self.stream_chunk.emit(txt)
                except Exception as e:
                    if "blocked" in str(e).lower():
                        self.stream_chunk.emit("\n\n*(⚠️ Blocked by Safety Filters)*")
                        break
                    raise e
            if self._is_running:
                self.response_received.emit(full_response)
                self._finalize_metrics(start_time, first_chunk_time, chunk_count)
        else:
            self.response_received.emit(response.text)

    def _run_openai_loop(self):
        start_time = time.perf_counter()
        first_chunk_time = None
        chunk_count = 0
        finalized_msgs = []
        for msg in self.messages:
            c = msg.get("content", "")
            if isinstance(c, list):
                open_ai_c = []
                for part in c:
                    if part.get('type') == 'text': open_ai_c.append({"type": "text", "text": part.get('text', '')})
                    elif part.get('type') == 'image':
                        url = f"data:{part.get('mime')};base64,{part.get('data')}"
                        open_ai_c.append({"type": "image_url", "image_url": {"url": url}})
                finalized_msgs.append({"role": msg["role"], "content": open_ai_c})
            else: finalized_msgs.append(msg)

        print(f"[Worker] Sending request to {self.client.base_url} for model: {self.client.current_model}")
        response = self.client.client.chat.completions.create(
            model=self.client.current_model,
            messages=finalized_msgs,
            stream=self.stream,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        if self.stream:
            full_response = ""
            for chunk in response:
                if not self._is_running: break
                if not getattr(chunk, "choices", None): continue
                if not chunk.choices: continue
                content = chunk.choices[0].delta.content
                if content:
                    if first_chunk_time is None: first_chunk_time = time.perf_counter()
                    full_response += content
                    chunk_count += 1
                    self.stream_chunk.emit(content)
            if self._is_running:
                self.response_received.emit(full_response)
                self._finalize_metrics(start_time, first_chunk_time, chunk_count)
        else:
            self.response_received.emit(response.choices[0].message.content)

    def _finalize_metrics(self, start, first_chunk, count):
        if first_chunk:
            end = time.perf_counter()
            self.metrics_received.emit({
                "ttft": round(first_chunk - start, 2),
                "tps": round(count / (end - first_chunk), 1) if (end - first_chunk) > 0 else 0,
                "prompt_tokens": 0,
                "completion_tokens": count
            })

    def stop(self):
        self._is_running = False