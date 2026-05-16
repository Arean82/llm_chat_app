# logic/api_manager.py
from PySide6.QtCore import QObject, Signal
from logic.api_server import APIServer
import queue

class ApiManager(QObject):
    """
    Manages the lifecycle of the local Flask API server and bridges requests 
    between the background Flask thread and the main GUI thread.
    """
    # Signal to pass requests to the main thread: (params_dict, response_queue)
    api_request_signal = Signal(dict, object)

    def __init__(self, main_window):
        super().__init__()
        self.window = main_window
        self.api_server = None
        
        # Connect the signal to the handler which executes on the GUI thread
        self.api_request_signal.connect(self.handle_api_request)

    def toggle_api_server(self, checked: bool):
        """Start or stop the server based on menu action state."""
        if checked:
            self.start_api_server()
        else:
            self.stop_api_server()

    def start_api_server(self):
        """Initialize and start the background Flask server."""
        if self.api_server and self.api_server.running:
            return

        # Initialize APIServer with BOTH static and streaming bridge callbacks (Fixes Audit 038)
        self.api_server = APIServer(self.window.llm_client, self.api_send_message, self.api_stream_callback)
        
        success, message = self.api_server.start()
        
        if success:
            self.window.api_server_action.setChecked(True)
            self.window.api_server_action.setText("Universal API Server (Running)")
            self.window.chat_view.add_system_message("🌐 API Server started on port 5000")
        else:
            self.window.api_server_action.setChecked(False)
            self.window.chat_view.add_system_message(f"❌ Failed to start API Server: {message}")

    def stop_api_server(self):
        """Stop the background Flask server."""
        if self.api_server:
            self.api_server.stop()
            self.api_server = None
            
        self.window.api_server_action.setChecked(False)
        self.window.api_server_action.setText("🌐 Universal API Server")
        if hasattr(self.window, 'chat_view') and self.window.chat_view:
            try:
                self.window.chat_view.add_system_message("🌐 API Server stopped")
            except: pass

    def api_send_message(self, user_message: str, messages_list: list = None, **kwargs):
        """
        CALLBACK called by the background Flask thread.
        This method safely bridges the call to the main thread using a Signal.
        """
        response_queue = queue.Queue()
        params = {
            "message": user_message,
            "messages_list": messages_list
        }
        params.update(kwargs)
        
        # Emit signal to trigger handle_api_request on the main thread
        self.api_request_signal.emit(params, response_queue)
        
        # Wait for the main thread to finish processing and put the result in the queue
        try:
            return response_queue.get(timeout=60)
        except queue.Empty:
            return "Error: Request timed out in GUI thread"

    def api_stream_callback(self, user_message: str, system_message: str = "", temperature: float = 0.7, max_tokens: int = 4096, messages_list: list = None):
        """
        NEW: Generator callback triggered by Flask for true streaming responses.
        Routes chunks continuously from a dedicated thread-safe streaming queue.
        """
        stream_queue = queue.Queue()
        params = {
            "message": user_message,
            "messages_list": messages_list,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_message": system_message,
            "stream_queue": stream_queue # Trigger flag for handler
        }
        
        # Signal to main thread, no return blocking response_queue needed here.
        self.api_request_signal.emit(params, None)
        
        # Loop until finished sentinel None is received
        while True:
            try:
                chunk = stream_queue.get(timeout=60)
                if chunk is None: 
                    break
                if isinstance(chunk, str) and chunk.startswith("API_STREAM_ERROR:"):
                    yield f"\n[Error: {chunk.replace('API_STREAM_ERROR:', '')}]"
                    break
                yield chunk
            except queue.Empty:
                yield "\n[Stream Timeout Exception]"
                break

    def handle_api_request(self, params: dict, response_queue: queue.Queue):
        """
        HANDLER executed on the Main GUI Thread.
        Processes data payloads safely detached from active human GUI interaction state.
        """
        user_message = params.get("message", "")
        messages_list = params.get("messages_list", None)
        temperature = params.get("temperature", None)
        max_tokens = params.get("max_tokens", None)
        stream_queue = params.get("stream_queue", None) # Resolves callback target
        
        # FIX Audit ID 039: NO LONGER setPlainText() in input field.
        # This completely isolates the background automated calls from the current active user session.
        
        self.window.chat_view.send_message(
            api_response_queue=response_queue, 
            custom_messages=messages_list,
            custom_temp=temperature,
            custom_max_tokens=max_tokens,
            override_prompt=user_message,  # Native isolated injection
            api_stream_queue=stream_queue  # Native streaming bridge
        )
