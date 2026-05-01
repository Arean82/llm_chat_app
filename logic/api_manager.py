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

        # Initialize APIServer with self.api_send_message as the bridge callback
        self.api_server = APIServer(self.window.llm_client, self.api_send_message)
        
        success, message = self.api_server.start()
        
        if success:
            self.window.api_server_action.setChecked(True)
            self.window.api_server_action.setText("Universal API Server (Running)")
            self.window.add_system_message("🌐 API Server started on port 5000")
        else:
            self.window.api_server_action.setChecked(False)
            self.window.add_system_message(f"❌ Failed to start API Server: {message}")

    def stop_api_server(self):
        """Stop the background Flask server."""
        if self.api_server:
            self.api_server.stop()
            self.api_server = None
            
        self.window.api_server_action.setChecked(False)
        self.window.api_server_action.setText("🌐 Universal API Server")
        self.window.add_system_message("🌐 API Server stopped")

    def api_send_message(self, user_message: str, **kwargs):
        """
        CALLBACK called by the background Flask thread.
        This method safely bridges the call to the main thread using a Signal.
        """
        response_queue = queue.Queue()
        params = {"message": user_message}
        params.update(kwargs)
        
        # Emit signal to trigger handle_api_request on the main thread
        self.api_request_signal.emit(params, response_queue)
        
        # Wait for the main thread to finish processing and put the result in the queue
        try:
            return response_queue.get(timeout=60)
        except queue.Empty:
            return "Error: Request timed out in GUI thread"

    def handle_api_request(self, params: dict, response_queue: queue.Queue):
        """
        HANDLER executed on the Main GUI Thread.
        Updates the UI and triggers the standard message sending logic.
        """
        user_message = params.get("message", "")
        
        # 1. Update the input field in the UI
        self.window.input_field.setPlainText(user_message)
        
        # 2. Trigger the standard send_message logic.
        # We pass the response_queue so the AI response can be sent back to the API.
        self.window.send_message(api_response_queue=response_queue)
