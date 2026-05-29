# workers/paid_model_fetch_worker.py

from PySide6.QtCore import QThread, Signal
from openai import OpenAI
from server.workers.update_logger import get_logger
import json
from server.utils.path_utils import get_models_path

class PaidModelFetchWorker(QThread):
    progress = Signal(int, int, str, str)
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, llm_client, parent=None):
        super().__init__(parent)
        self.api_key = llm_client.api_key
        self.base_url = llm_client.base_url
        self.logger = get_logger()
        
    def run(self):
        try:
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=15.0
            )
            
            response = client.models.list()
            all_models = response.data
            total = len(all_models)
            
            self.logger.add_log(f"Found {total} total models. Filtering paid models...", "INFO")
            
            paid_models = []
            
            # Determine active provider name
            from server.utils.path_utils import get_app_settings
            active_p = get_app_settings().value("active_provider_id", "nvidia").lower()
            
            for i, model in enumerate(all_models):
                model_id = model.id
                self.progress.emit(i + 1, total, model_id, "Checking...")
                
                # Check if this is likely a paid model
                free_providers = ['meta', 'google', 'microsoft', 'mistralai', 'deepseek-ai', 'z-ai']
                provider = model_id.split('/')[0] if '/' in model_id else ''
                
                is_free_provider = provider in free_providers
                
                if not is_free_provider:
                    # Dynamic reflective developer matching
                    model_id_lower = model_id.lower()
                    if '/' in model_id:
                        developer = model_id.split('/')[0]
                    elif "deepseek" in model_id_lower:
                        developer = "DeepSeek"
                    elif "nvidia" in model_id_lower:
                        developer = "NVIDIA"
                    elif "openai" in model_id_lower or "gpt" in model_id_lower:
                        developer = "OpenAI"
                    elif "google" in model_id_lower or "gemini" in model_id_lower:
                        developer = "Google"
                    elif "meta" in model_id_lower or "llama" in model_id_lower:
                        developer = "Meta"
                    elif "mistral" in model_id_lower or "mixtral" in model_id_lower:
                        developer = "Mistral"
                    elif "claude" in model_id_lower or "anthropic" in model_id_lower:
                        developer = "Anthropic"
                    else:
                        developer = active_p.capitalize()
                        
                    paid_models.append({
                        "id": model_id,
                        "name": self._format_name(model_id),
                        "description": "",
                        "developer": developer.capitalize(),
                        "free": False,
                        "provider": active_p
                    })
                    self.logger.add_log(f"💰 {model_id} - identified as paid model", "INFO")
                
                if i < total - 1:
                    self.msleep(100)
            
            # Load existing models cleanly
            from server.logic.model_io import load_all_models, save_all_models
            existing_models = load_all_models()
            
            # Merge: Keep existing free/other models, add new paid models
            existing_ids = {m["id"] for m in existing_models}
            new_paid_models = [m for m in paid_models if m["id"] not in existing_ids]
            
            merged_models = existing_models + new_paid_models
            
            # Save merged list split cleanly by provider
            save_all_models(merged_models)
            
            self.logger.add_log(f"Paid fetch complete! Added {len(new_paid_models)} new paid models", "SUCCESS")
            self.logger.add_log(f"Total models now: {len(merged_models)} (Free + Paid)", "INFO")
            self.finished.emit()
            
        except Exception as e:
            self.logger.add_log(f"Paid fetch error: {str(e)}", "ERROR")
            self.error.emit(str(e))
    
    def _format_name(self, model_id: str) -> str:
        if '/' in model_id:
            name = model_id.split('/')[-1]
        else:
            name = model_id
        name = name.replace('-', ' ').replace('_', ' ')
        words = name.split()
        return ' '.join(word.capitalize() for word in words)
