from flask import Flask, request, jsonify
from threading import Thread
import time

class APIServer:
    def __init__(self, llm_client, send_message_callback):
        self.app = Flask(__name__)
        self.llm_client = llm_client
        self.send_message_callback = send_message_callback
        self.port = 5000
        self.server_thread = None
        self.running = False
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.route('/v1/models', methods=['GET'])
        def list_models():
            return jsonify({
                "data": [{
                    "id": self.llm_client.current_model or "unknown",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "llm-chat-app"
                }]
            })
        
        @self.app.route('/v1/chat/completions', methods=['POST'])
        def chat_completion():
            data = request.json
            messages = data.get('messages', [])
            
            # Extract user message
            user_message = ""
            for msg in messages:
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    break
            
            if not user_message:
                return jsonify({"error": "No user message found"}), 400
            
            # Call the app's send function
            response = self.send_message_callback(user_message)
            
            return jsonify({
                "id": "chatcmpl-" + str(int(time.time())),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": self.llm_client.current_model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            })
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "running", "model": self.llm_client.current_model})
    
    def start(self):
        if self.running:
            return False
        
        def run():
            self.app.run(host='localhost', port=self.port, debug=False, use_reloader=False)
        
        self.server_thread = Thread(target=run, daemon=True)
        self.server_thread.start()
        self.running = True
        return True
    
    def stop(self):
        self.running = False
        # Note: Flask doesn't easily stop, but daemon thread will die on app exit
        return True
    
    def get_status(self):
        return {"running": self.running, "port": self.port, "model": self.llm_client.current_model}