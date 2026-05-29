# logic/headless_worker.py
# DEDICATED Headless Engine Worker (Zero Qt/PySide6 dependencies)
import threading
import time

class HeadlessWorker(threading.Thread):
    def __init__(self, client, messages, temperature=0.7, max_tokens=4096, 
                 on_chunk=None, on_response=None, on_error=None, on_finished=None):
        super().__init__()
        self.client = client
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.on_chunk = on_chunk
        self.on_response = on_response
        self.on_error = on_error
        self.on_finished = on_finished
        self.stream = True
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            provider = self.client.get_current_provider()
            if provider == "google":
                self._run_google_loop()
            else:
                self._run_openai_loop()
        except Exception as e:
            if not self._stop_event.is_set():
                if self.on_error: self.on_error(str(e))
        finally:
            if self.on_finished: self.on_finished()

    def _run_google_loop(self):
        from google.genai import types
        import base64
        
        full_response = ""
        system_instructions = ""
        mapped_history = []

        for msg in self.messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "system":
                system_instructions += (content if isinstance(content, str) else "") + "\n"
            else:
                fixed_role = "model" if role == "assistant" else "user"
                current_parts = [content] # Simplification for headless for now
                if mapped_history and mapped_history[-1]["role"] == fixed_role:
                    mapped_history[-1]["parts"].extend(current_parts)
                else:
                    mapped_history.append({"role": fixed_role, "parts": current_parts})

        chat = self.client.google_client.chats.create(
            model=self.client.current_model,
            history=mapped_history,
            config=types.GenerateContentConfig(
                system_instruction=system_instructions.strip() if system_instructions else None,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )
        )
        
        response = chat.send_message_stream(mapped_history.pop()["parts"]) # Simplified
        for chunk in response:
            if self._stop_event.is_set(): break
            txt = chunk.text
            if txt:
                full_response += txt
                if self.on_chunk: self.on_chunk(txt)
        if not self._stop_event.is_set() and self.on_response:
            self.on_response(full_response)

    def _run_openai_loop(self):
        response = self.client.client.chat.completions.create(
            model=self.client.current_model,
            messages=self.messages,
            stream=self.stream,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        full_response = ""
        for chunk in response:
            if self._stop_event.is_set(): break
            if chunk.choices and chunk.choices[0].delta.content:
                txt = chunk.choices[0].delta.content
                full_response += txt
                if self.on_chunk: self.on_chunk(txt)
        if not self._stop_event.is_set() and self.on_response:
            self.on_response(full_response)
