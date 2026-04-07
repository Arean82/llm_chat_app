# logic/chat_worker.py
from PySide6.QtCore import QThread, Signal
from logic.llm_client import LLMClient
import time

class ChatWorker(QThread):
    response_received = Signal(str)
    stream_chunk = Signal(str)
    thinking_chunk = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()
    metrics_received = Signal(dict)  # <-- NEW SIGNAL for metrics
    
    def __init__(self, client: LLMClient, messages: list):
        super().__init__()
        self.client = client
        self.messages = messages
        self.stream = True
        
    def run(self):
        try:
            if not self.client.client:
                self.error_occurred.emit("API key not configured.")
                return
                
            start_time = time.perf_counter()
            first_chunk_time = None
            chunk_count = 0
            prompt_tokens = 0
            completion_tokens = 0
            
            # NVIDIA NIM supports standard OpenAI stream_options
            response = self.client.client.chat.completions.create(
                model=self.client.current_model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=4096,
                stream=self.stream,
                stream_options={"include_usage": True}  # TRIGGERS TOKEN COUNTS
            )
            
            if self.stream:
                full_response = ""
                for chunk in response:
                    if self.isInterruptionRequested():
                        break
                    
                    # 1. Check for usage data in the final chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        prompt_tokens = chunk.usage.prompt_tokens
                        completion_tokens = chunk.usage.completion_tokens

                    if not getattr(chunk, "choices", None):
                        continue
                    
                    reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                    if reasoning:
                        self.thinking_chunk.emit(reasoning)
                    
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        chunk_count += 1
                        
                        # Record exact time of first token
                        if first_chunk_time is None:
                            first_chunk_time = time.perf_counter()
                            
                        self.stream_chunk.emit(content)
                        
                if not self.isInterruptionRequested():
                    self.response_received.emit(full_response)
                    
                    # 2. Calculate Metrics
                    if first_chunk_time:
                        end_time = time.perf_counter()
                        ttft = first_chunk_time - start_time
                        generation_time = end_time - first_chunk_time
                        # Rough TPS estimation (1 chunk ≈ 1 token usually)
                        tps = chunk_count / generation_time if generation_time > 0 else 0
                        
                        self.metrics_received.emit({
                            "ttft": round(ttft, 2),
                            "tps": round(tps, 1),
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens
                        })
            else:
                self.response_received.emit(response.choices[0].message.content)
                
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error_occurred.emit(f"API Error: {str(e)}")
        finally:
            self.finished.emit()