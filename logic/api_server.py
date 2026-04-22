from flask import Flask, request, jsonify, Response, stream_with_context
from threading import Thread
import time
import json

class APIServer:
    def __init__(self, llm_client, send_message_callback, stream_callback=None):
        self.app = Flask(__name__)
        self.llm_client = llm_client
        self.send_message_callback = send_message_callback
        self.stream_callback = stream_callback
        self.port = 5000
        self.server_thread = None
        self.running = False
        self.conversation_history = {}  # Store history per session
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
            stream = data.get('stream', False)
            temperature = data.get('temperature', 0.7)
            max_tokens = data.get('max_tokens', 4096)
            session_id = data.get('session_id', 'default')
            
            # Extract messages
            user_message = ""
            system_message = ""
            for msg in messages:
                if msg.get('role') == 'system':
                    system_message = msg.get('content', '')
                elif msg.get('role') == 'user':
                    user_message = msg.get('content', '')
            
            if not user_message:
                return jsonify({"error": "No user message found"}), 400
            
            # Store conversation history
            if session_id not in self.conversation_history:
                self.conversation_history[session_id] = []
            
            # Add user message to history
            self.conversation_history[session_id].append({"role": "user", "content": user_message})
            
            if stream:
                def generate():
                    full_response = ""
                    for chunk in self.stream_response(user_message, system_message, temperature, max_tokens):
                        full_response += chunk
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"
                    
                    # Store assistant response in history
                    self.conversation_history[session_id].append({"role": "assistant", "content": full_response})
                    yield "data: [DONE]\n\n"
                
                return Response(generate(), mimetype='text/event-stream')
            else:
                # Call the app's send function with parameters
                response = self.send_message_callback(
                    user_message, 
                    system_message=system_message,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Store assistant response in history
                self.conversation_history[session_id].append({"role": "assistant", "content": response})
                
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
        
        @self.app.route('/v1/chat/history/<session_id>', methods=['DELETE'])
        def clear_history(session_id):
            if session_id in self.conversation_history:
                del self.conversation_history[session_id]
            return jsonify({"status": "cleared"})
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "running", "model": self.llm_client.current_model})
    
    def stream_response(self, user_message, system_message="", temperature=0.7, max_tokens=4096):
        """Generator for streaming responses"""
        if self.stream_callback:
            for chunk in self.stream_callback(user_message, system_message, temperature, max_tokens):
                yield chunk
        else:
            # Fallback to non-streaming
            response = self.send_message_callback(user_message, system_message, temperature, max_tokens)
            yield response
    
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
        return True
    
    def get_status(self):
        return {"running": self.running, "port": self.port, "model": self.llm_client.current_model}