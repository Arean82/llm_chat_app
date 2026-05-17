# headless/models.py
# CLI-based model management for headless execution.
# Allows listing and updating models directly from the terminal.

import json
from logic.model_io import load_all_models, save_all_models
from logic.llm_client import LLMClient
from workers.model_fetch_worker import ModelFetchWorker

class HeadlessModels:
    """
    Handles CLI-based model operations.
    """
    
    @staticmethod
    def list_models():
        """
        Prints a table of currently available models in the manifest.
        """
        models = load_all_models()
        if not models:
            print("[!] No models found in manifest. Run an update first.")
            return
            
        print("\n" + "="*80)
        print(f"{'ID':<40} | {'DEVELOPER':<15} | {'FREE'}")
        print("-"*80)
        for m in models:
            free_status = "Yes" if m.get("free") else "No"
            print(f"{m.get('id', 'N/A'):<40} | {m.get('developer', 'N/A'):<15} | {free_status}")
        print("="*80 + "\n")

    @staticmethod
    def update_models(client: LLMClient):
        """
        Triggers a synchronous model fetch and updates the manifest.
        """
        print(f"[*] Fetching models for {client.base_url}...")
        
        # We reuse the ModelFetchWorker logic but run it synchronously for CLI
        worker = ModelFetchWorker(client.api_key, client.base_url)
        
        # Capture the finished signal results (ModelFetchWorker emits Signal(list))
        models_list = []
        worker.finished.connect(lambda res: models_list.extend(res))
        
        try:
            worker.run()
            if models_list:
                p_id = client.get_current_provider()
                for m in models_list:
                    m['provider'] = p_id
                save_all_models(models_list)
                print(f"[SUCCESS] Model manifest updated successfully. Saved {len(models_list)} models to models_{p_id}.json.")
                return True
            else:
                print("[!] No models returned from provider.")
                return False
        except Exception as e:
            print(f"[!] Update Failed: {e}")
            return False

    @staticmethod
    def select_model(model_id: str):
        """
        Sets the active model ID in the settings.
        """
        from utils.path_utils import get_app_settings
        models = load_all_models()
        if any(m.get("id") == model_id for m in models):
            settings = get_app_settings()
            settings.setValue("current_model_id", model_id)
            settings.sync()
            print(f"[+] Active model set to: {model_id}")
            return True
        else:
            print(f"[!] Error: Model '{model_id}' not found in manifest.")
            return False
