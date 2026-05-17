# logic/headless_engine.py
# Dedicated background engine for Headless/SaaS execution.
# Decoupled from GUI via Callback Patterns.

from headless.worker import HeadlessWorker
from logic.llm_client import LLMClient
from logic.model_io import load_all_models

class HeadlessEngine:
    """
    Manages background chat requests for headless execution.
    Acts as the 'Handler' for the ApiManager.
    """

    @staticmethod
    def ensure_initialized(client: LLMClient):
        """
        CLI-based initialization gate. Ensures keys and models are ready.
        Strictly decoupled from GUI dependencies.
        """
        if not client.is_globally_authenticated():
            from headless.auth import HeadlessAuth
            if not HeadlessAuth.run_login_flow(client):
                raise RuntimeError("API key configuration failed or was cancelled.")

        # Automated Model Manifest Sync (CLI)
        from headless.models import HeadlessModels
        if not load_all_models():
             print("[*] Manifest empty. Performing initial fetch...")
             HeadlessModels.update_models(client)
    
    @staticmethod
    def request_handler(params):
        """
        Processes API chat requests by spawning background HeadlessWorkers.
        Mimics the logic found in MainWindow but without UI dependencies.
        """
        # Use the hydrated client passed from the ApiManager
        client = params.get("client")
        if not client:
            # Fallback (though ApiManager should always provide it)
            client = LLMClient()
            client.hydrate()
        
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
