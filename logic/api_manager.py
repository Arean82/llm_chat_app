# logic/api_manager.py
# RESTORED TO V6.1 STATE: GUI-compatible API Manager.
from logic.api_server import APIServer
import queue

class ApiManager:
    """
    Manages the lifecycle of the local Flask API server.
    Ensures compatibility with both GUI and Headless via hybrid init.
    """
    def __init__(self, parent_or_client, request_handler_callback=None, status_callback=None):
        # Hybrid Init: Handle being called from MainWindow(self) or Headless(client)
        from logic.llm_client import LLMClient
        if isinstance(parent_or_client, LLMClient):
            self.llm_client = parent_or_client
            self.parent = None
        else:
            self.parent = parent_or_client
            # In GUI mode, we often grab the client from the parent if needed later
            self.llm_client = getattr(parent_or_client, 'llm_client', None)
            
        self.request_handler = request_handler_callback
        self.status_callback = status_callback
        self.api_server = None

    def start_api_server(self):
        """Initialize and start the background Flask server."""
        if self.api_server and self.api_server.running:
            return

        # Ensure we have a client before starting
        if not self.llm_client and self.parent:
            self.llm_client = getattr(self.parent, 'llm_client', None)

        self.api_server = APIServer(
            self.llm_client, 
            self.api_send_message, 
            self.api_stream_callback
        )
        
        success, message = self.api_server.start()
        
        # Notify GUI or Headless status
        if self.status_callback:
            self.status_callback(success, message)
        elif self.parent and hasattr(self.parent, 'on_api_status_changed'):
            self.parent.on_api_status_changed(success, message)

    def toggle_api_server(self):
        """Toggle the server state (convenience method for GUI)."""
        if self.api_server and self.api_server.running:
            self.stop_api_server()
        else:
            self.start_api_server()

    def stop_api_server(self):
        """Stop the background Flask server."""
        success = True
        message = "API Server Stopped."
        if self.api_server:
            success, message = self.api_server.stop()
            self.api_server = None
        
        if self.status_callback:
            self.status_callback(success, message)
        elif self.parent and hasattr(self.parent, 'on_api_status_changed'):
            self.parent.on_api_status_changed(success, message)

    def api_send_message(self, user_message: str, messages_list: list = None, **kwargs):
        """Logic bridge for static requests."""
        # Use explicit handler or fall back to GUI-style dispatch
        handler = self.request_handler
        if handler:
            response_queue = queue.Queue()
            params = {
                "message": user_message,
                "messages_list": messages_list,
                "api_response_queue": response_queue,
                "client": self.llm_client
            }
            params.update(kwargs)
            handler(params)
            try:
                return response_queue.get(timeout=60)
            except queue.Empty:
                return "Error: Request timed out"
        return "Error: No handler"

    def api_stream_callback(self, user_message: str, **kwargs):
        """Logic bridge for streaming responses."""
        handler = self.request_handler
        if handler:
            stream_queue = queue.Queue()
            params = {
                "message": user_message,
                "stream_queue": stream_queue,
                "client": self.llm_client
            }
            params.update(kwargs)
            handler(params)
            while True:
                try:
                    chunk = stream_queue.get(timeout=60)
                    if chunk is None: break
                    yield chunk
                except queue.Empty:
                    yield "\n[Stream Timeout]"
                    break
        else:
            yield "Error: No handler"
