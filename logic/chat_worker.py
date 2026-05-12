# logic/chat_worker.py
from PySide6.QtCore import QThread, Signal
from logic.llm_client import LLMClient
import time

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

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
                if not self.client.google_client or not GENAI_AVAILABLE:
                    self.error_occurred.emit("Google API key not configured.")
                    return
                self._run_google_loop()
            else:
                if not self.client.client:
                    self.error_occurred.emit("Active API provider client not configured.")
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
        
        # Tracking analytics for context safety filtering
        p_tokens_native = 0
        c_tokens_native = 0

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
                # Modern SDK strictly requires 'user' and 'model' keys.
                fixed_role = "model" if role == "assistant" else "user"
                
                # STRICT ALTERNATION FIX (Audit ID 019):
                # If consecutive messages have the same role, concatenate their text instead of appending new block
                if mapped_history and mapped_history[-1]["role"] == fixed_role:
                    mapped_history[-1]["parts"][0]["text"] += "\n\n" + content
                else:
                    mapped_history.append({"role": fixed_role, "parts": [{"text": content}]})

        # 2. Isolate latest message as active prompt to feed the model
        if not mapped_history:
            raise ValueError("Cannot generate response without message history.")
            
        active_prompt = mapped_history.pop()["parts"][0]["text"]
        
        # Estimate pre-request prompt tokens in case dynamic tracking is missing downstream
        prompt_chars = len(system_instructions) + len(active_prompt)
        for m in mapped_history:
            for part in m.get("parts", []):
                prompt_chars += len(part.get("text", ""))
        p_tokens_fallback = int(prompt_chars / 3.8) # standardized conservative estimation
        
        # 3. Prepare Generation Config
        config = types.GenerateContentConfig(
            system_instruction=system_instructions.strip() if system_instructions else None,
            temperature=self.temperature,
            max_output_tokens=self.max_tokens
        )
        
        
        # 4. 🛠️ BOUNDARY CONSOLIDATION FIX (Audit ID 027 Patch):
        # Google Gemini mandates strict alternating role schema. If the sanitized history 
        # ends on a 'user' node, passing the next message (also user) crashes the backend.
        if mapped_history and mapped_history[-1]["role"] == "user":
             # Pop trailing user item from history and prefix directly to current prompt
             last_history_item = mapped_history.pop()
             last_content = last_history_item["parts"][0]["text"]
             active_prompt = f"{last_content}\n\n{active_prompt}"

        # 5. Initialize Chat Session with existing history
        chat = self.client.google_client.chats.create(
            model=self.client.current_model,
            history=mapped_history,
            config=config
        )
        
        # 5. Determine Request Pathway
        if self.stream:
            response = chat.send_message_stream(active_prompt)
        else:
            response = chat.send_message(active_prompt)

        # 6. Response Loop
        if self.stream:
            for chunk in response:
                if self.isInterruptionRequested(): break
                
                # Attempt to harvest native token usages from the chunk if populated by the backend
                meta = getattr(chunk, 'usage_metadata', None)
                if meta:
                    p_tokens_native = getattr(meta, 'prompt_token_count', 0) or p_tokens_native
                    c_tokens_native = getattr(meta, 'candidates_token_count', 0) or getattr(meta, 'total_token_count', 0) - p_tokens_native

                try:
                    txt = chunk.text
                except (ValueError, Exception) as e:
                    err_str = str(e).lower()
                    # Check for standard Google API blocking signatures
                    if "blocked" in err_str or "safety" in err_str or "finish_reason" in err_str:
                        warning_msg = "\n\n*(⚠️ [System Notice]: Response halted by provider safety filters)*"
                        full_response += warning_msg
                        self.stream_chunk.emit(warning_msg)
                        break # Gracefully stop pulling from stream without crashing worker
                    raise e # Re-raise if it's a real connection failure

                if txt:
                    if first_chunk_time is None:
                        first_chunk_time = time.perf_counter()
                    
                    full_response += txt
                    chunk_count += len(txt.split()) # rough word count estimation
                    self.stream_chunk.emit(txt)

            if not self.isInterruptionRequested():
                # Align final metrics feeding into safety triggers
                final_p = p_tokens_native if p_tokens_native > 0 else p_tokens_fallback
                final_c = c_tokens_native if c_tokens_native > 0 else int(len(full_response) / 3.8)
                
                self.response_received.emit(full_response)
                self._finalize_metrics(start_time, first_chunk_time, chunk_count, p_tokens=final_p, c_tokens=final_c)
        else:
            # Synchronous block with safety shielding
            try:
                final_text = response.text
                self.response_received.emit(final_text)
                
                # Trigger metric calculation for synchronous completions too to keep context manager synced
                meta = getattr(response, 'usage_metadata', None)
                sp = getattr(meta, 'prompt_token_count', p_tokens_fallback) if meta else p_tokens_fallback
                sc = getattr(meta, 'candidates_token_count', int(len(final_text) / 3.8)) if meta else int(len(final_text) / 3.8)
                self._finalize_metrics(start_time, time.perf_counter(), len(final_text.split()), p_tokens=sp, c_tokens=sc)
                
            except (ValueError, Exception) as e:
                if "blocked" in str(e).lower() or "safety" in str(e).lower():
                    self.response_received.emit("*(⚠️ [System Notice]: Response halted by provider safety filters)*")
                else:
                    raise e


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
            final_text = response.choices[0].message.content
            self.response_received.emit(final_text)
            
            # Metric Harvesting for batch request (Audit ID 027 Safety Sync)
            usage = getattr(response, 'usage', None)
            if usage:
                 self._finalize_metrics(start_time, time.perf_counter(), len(final_text.split()), usage.prompt_tokens, usage.completion_tokens)

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