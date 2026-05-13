# workers/local_model_detector.py
# Non-blocking Sweep engine designed to auto-detect and register local self-hosted LLMs (Ollama/LM Studio).

import requests
from PySide6.QtCore import QThread, Signal
from openai import OpenAI

class LocalModelDetector(QThread):
    """
    Background scanner sweep probing standard local endpoints for active LLM runners.
    Automatically pulls model tags and updates the unified provider model catalog.
    """
    # Emits: (provider_name, number_of_models_synced)
    detection_completed = Signal(str, int)

    def __init__(self):
        super().__init__()
        self.targets = [
            {
                "name": "Ollama",
                "url": "http://127.0.0.1:11434",
                "api_base": "http://127.0.0.1:11434/v1",
                "default_desc": "Local Llama-based model hosted via Ollama Engine."
            },
            {
                "name": "LM Studio",
                "url": "http://localhost:1234",
                "api_base": "http://localhost:1234/v1",
                "default_desc": "Locally hosted model served via LM Studio workstation."
            }
        ]

    def run(self):
        """Sequential thread executor executing safe sweeps with strict timeout bounds."""
        for target in self.targets:
            try:
                # Cheap GET request to verify process presence without hanging startup
                resp = requests.get(target["url"], timeout=1.5)
                
                # Ollama roots return 200 "Ollama is running"
                # LM Studio roots return index payload or 200/404 depending on version, 
                # but connection establishment itself confirms daemon is online.
                if resp.status_code in [200, 404]:
                    self._sync_models(target)
            except (requests.exceptions.RequestException, ConnectionError):
                # Target engine is offline/inactive, continue sweep silently
                continue

    def _sync_models(self, target):
        """Interrogates target engine model bank and hydration cache."""
        provider_id = target["name"].lower().replace(" ", "")
        try:
            # Leverage compatibility translation layer
            client = OpenAI(
                base_url=target["api_base"],
                api_key="none", # Local instances rarely implement vault custody
                timeout=4.0
            )
            
            response = client.models.list()
            remote_models = response.data
            
            if not remote_models:
                return

            new_models = []
            for item in remote_models:
                m_id = item.id
                new_models.append({
                    "id": m_id,
                    "name": self._format_name(m_id),
                    "description": target["default_desc"],
                    "developer": target["name"],
                    "free": True,
                    "provider": provider_id
                })

            if new_models:
                # Direct commit using serialized loader bridge
                from logic.model_io import load_all_models, save_all_models
                
                # Hydrate current pool
                active_catalog = load_all_models()
                
                # Evict legacy duplicates previously associated with this provider shard
                filtered = [m for m in active_catalog if m.get("provider") != provider_id]
                
                # Merge and persist
                filtered.extend(new_models)
                save_all_models(filtered)
                
                # Announce telemetry sync to UI controller
                self.detection_completed.emit(target["name"], len(new_models))

        except Exception as e:
            print(f"[Local Sweep Log] Interrogation fault on {target['name']}: {e}")

    def _format_name(self, model_id: str) -> str:
        """Transforms raw slug identifiers into clean, readable presentation titles."""
        # Strip off dynamic pathing
        name = model_id.split('/')[-1] if '/' in model_id else model_id
        # Clean common technical taggings and version colons
        name = name.replace(':latest', '').replace(':instruct', '')
        name = name.replace('-instruct', '').replace('-chat', '').replace('-preview', '')
        name = name.replace(':', ' ').replace('-', ' ').replace('_', ' ')
        
        # Format properly capitalized titles
        words = name.split()
        return ' '.join(word.capitalize() for word in words)
