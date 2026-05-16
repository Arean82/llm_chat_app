# logic/headless_engine.py
# Dedicated background engine for Headless/SaaS execution.
# Decoupled from GUI via Callback Patterns.

from headless.worker import HeadlessWorker
from logic.llm_client import LLMClient

class HeadlessEngine:
    """
    Manages background chat requests for headless execution.
    Acts as the 'Handler' for the ApiManager.
    """
    
    @staticmethod
    def request_handler(params):
        """
        Processes API chat requests by spawning background HeadlessWorkers.
        Mimics the logic found in MainWindow but without UI dependencies.
        """
        client = LLMClient()
        
        # Extract parameters
        user_msg = params.get("message")
        history = params.get("messages_list", [])
        temp = params.get("temperature", 0.7)
        tokens = params.get("max_tokens", 4096)
        
        # Response queues for API communication
        resp_queue = params.get("api_response_queue")
        stream_queue = params.get("stream_queue")

        # Spawn a dedicated HeadlessWorker (zero Qt dependencies)
        worker = HeadlessWorker(
            client, history + [{"role": "user", "content": user_msg}],
            temperature=temp, max_tokens=tokens,
            on_chunk=lambda c: stream_queue.put(c) if stream_queue else None,
            on_response=lambda r: resp_queue.put(r) if resp_queue else None,
            on_finished=lambda: stream_queue.put(None) if stream_queue else None
        )
        worker.start()
