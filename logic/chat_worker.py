from PySide6.QtCore import QThread, Signal
from logic.llm_client import LLMClient


class ChatWorker(QThread):
    response_received = Signal(str)
    stream_chunk = Signal(str)
    thinking_chunk = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()
    
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
                
            response = self.client.client.chat.completions.create(
                model=self.client.current_model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=4096,
                stream=self.stream
            )
            
            if self.stream:
                full_response = ""
                for chunk in response:
                    if self.isInterruptionRequested():
                        break
                    
                    if not getattr(chunk, "choices", None):
                        continue
                    
                    reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                    if reasoning:
                        self.thinking_chunk.emit(reasoning)
                    
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        self.stream_chunk.emit(content)
                        
                if not self.isInterruptionRequested():
                    self.response_received.emit(full_response)
            else:
                self.response_received.emit(response.choices[0].message.content)
                
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error_occurred.emit(f"API Error: {str(e)}")
        finally:
            self.finished.emit()