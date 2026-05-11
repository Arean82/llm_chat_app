# logic/chat_worker.py
from PySide6.QtCore import QThread, Signal
from logic.llm_client import LLMClient
import time

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class ChatWorker(QThread):
    response_received = Signal(str)
    stream_chunk = Signal(str)
    thinking_chunk = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()
    metrics_received = Signal(dict)
    
    def __init__(self, client: LLMClient, messages: list, temperature=0.7, max_tokens=4096):
        super().__init__()
        self.client = client
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = True
        
    def run(self):
        try:
            provider = self.client.get_current_provider()
            
            # 🛠️ Verify provider presence
            if provider == "google":
                if not self.client.google_api_key or not genai:
                    self.error_occurred.emit("Google API key not configured.")
                    return
                self._run_google_loop()
            else:
                if not self.client.client:
                    self.error_occurred.emit("NVIDIA API key not configured.")
                    return
                self._run_openai_loop()
                
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error_occurred.emit(f"Connection Fault: {str(e)}")
        finally:
            self.finished.emit()

    def _run_google_loop(self):
        """Dedicated high-performance loop for Google Generative AI native streaming."""
        start_time = time.perf_counter()
        first_chunk_time = None
        chunk_count = 0
        full_response = ""

        # 1. Prepare Content & Conversation History
        system_instructions = ""
        mapped_history = []
        
        # Extract system instructions separately (Gemini enforces system at constructor level)
        for msg in self.messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            
            if role == "system":
                system_instructions += content + "\n"
            else:
                # Gemini strictly requires 'user' and 'model' keys. Convert 'assistant' to 'model'.
                fixed_role = "model" if role == "assistant" else "user"
                mapped_history.append({"role": fixed_role, "parts": [content]})

        # 2. Isolate latest message as active prompt to feed the model
        if not mapped_history:
            raise ValueError("Cannot generate response without message history.")
            
        active_prompt = mapped_history.pop()["parts"][0]
        
        # 3. Initialize Model
        model = genai.GenerativeModel(
            model_name=self.client.current_model,
            system_instruction=system_instructions.strip() if system_instructions else None
        )
        
        # Dynamic Config mapping
        gen_config = {}
        if self.temperature is not None: gen_config["temperature"] = self.temperature
        if self.max_tokens is not None: gen_config["max_output_tokens"] = self.max_tokens
        
        # 4. Start Chat Session & Send Request
        chat = model.start_chat(history=mapped_history)
        response = chat.send_message(
            active_prompt,
            stream=self.stream,
            generation_config=genai.types.GenerationConfig(**gen_config) if gen_config else None
        )

        # 5. Stream Loop
        if self.stream:
            for chunk in response:
                if self.isInterruptionRequested(): break
                
                txt = chunk.text
                if txt:
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                    
                    full_response += txt
                    chunk_count += len(txt.split()) # rough token count estimation
                    self.stream_chunk.emit(txt)

            if not self.isInterruptionRequested():
                self.response_received.emit(full_response)
                self._finalize_metrics(start_time, first_chunk_time, chunk_count)
        else:
            # Synchronous block
            self.response_received.emit(response.text)


    def _run_openai_loop(self):
        """Legacy hardened loop optimized for NVIDIA's OpenAI compatible API endpoints."""
        start_time = time.perf_counter()
        first_chunk_time = None
        chunk_count = 0
        prompt_tokens = 0
        completion_tokens = 0
        
        base_params = {
            "model": self.client.current_model,
            "stream": self.stream
        }
        if self.temperature is not None: base_params["temperature"] = self.temperature
        if self.max_tokens is not None: base_params["max_tokens"] = self.max_tokens
        
        try:
            req_params = base_params.copy()
            req_params["messages"] = self.messages
            req_params["stream_options"] = {"include_usage": True}
            response = self.client.client.chat.completions.create(**req_params)
        except Exception as e:
            error_str = str(e).lower()
            if "stream_options" in error_str or "422" in error_str:
                req_params = base_params.copy()
                req_params["messages"] = self.messages
                response = self.client.client.chat.completions.create(**req_params)
            elif "system role" in error_str or "system_role" in error_str:
                # Fallback handling for models that don't support system roles
                new_msgs = []
                sys_buf = ""
                for m in self.messages:
                    if m["role"] == "system": sys_buf += m["content"] + "\n\n"
                    elif m["role"] == "user" and sys_buf:
                        new_msgs.append({"role": "user", "content": f"{sys_buf}{m['content']}"})
                        sys_buf = ""
                    else: new_msgs.append(m)
                req_params = base_params.copy()
                req_params["messages"] = new_msgs
                response = self.client.client.chat.completions.create(**req_params)
            else:
                raise e

        if self.stream:
            full_response = ""
            for chunk in response:
                if self.isInterruptionRequested(): break
                
                if hasattr(chunk, 'usage') and chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens

                if not getattr(chunk, "choices", None): continue
                
                reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                if reasoning:
                    self.thinking_chunk.emit(reasoning)
                
                content = chunk.choices[0].delta.content
                if content:
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                    full_response += content
                    chunk_count += 1
                    self.stream_chunk.emit(content)
                    
            if not self.isInterruptionRequested():
                self.response_received.emit(full_response)
                self._finalize_metrics(start_time, first_chunk_time, chunk_count, prompt_tokens, completion_tokens)
        else:
            self.response_received.emit(response.choices[0].message.content)

    def _finalize_metrics(self, start, first_chunk, count, p_tokens=0, c_tokens=0):
        if first_chunk:
            end = time.perf_counter()
            ttft = first_chunk - start
            gen_time = end - first_chunk
            tps = count / gen_time if gen_time > 0 else 0
            self.metrics_received.emit({
                "ttft": round(ttft, 2),
                "tps": round(tps, 1),
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens
            })