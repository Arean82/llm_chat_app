# workers/paid_model_fetch_worker.py

from PySide6.QtCore import QThread, Signal
from openai import OpenAI
from workers.update_logger import get_logger
import json
from utils.path_utils import get_models_path

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
            
            for i, model in enumerate(all_models):
                model_id = model.id
                self.progress.emit(i + 1, total, model_id, "Checking...")
                
                # Check if this is likely a paid model
                # Paid models are those NOT from free providers
                free_providers = ['meta', 'google', 'microsoft', 'mistralai', 'deepseek-ai', 'z-ai']
                provider = model_id.split('/')[0] if '/' in model_id else ''
                
                is_free_provider = provider in free_providers
                
                if not is_free_provider:
                    # This is likely a paid model
                    paid_models.append({
                        "id": model_id,
                        "name": self._format_name(model_id),
                        "description": "",
                        "developer": provider.capitalize() if provider else "NVIDIA",
                        "free": False,  # Mark as paid
                    })
                    self.logger.add_log(f"💰 {model_id} - identified as paid model", "INFO")
                
                if i < total - 1:
                    self.msleep(100)
            
            # Load existing models
            models_file = get_models_path()
            if models_file.exists():
                with open(models_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_models = data.get("models", [])
            else:
                existing_models = []
            
            # Merge: Keep existing free models, add new paid models
            existing_ids = {m["id"] for m in existing_models}
            new_paid_models = [m for m in paid_models if m["id"] not in existing_ids]
            
            merged_models = existing_models + new_paid_models
            
            # Save merged list
            data = {"models": merged_models}
            with open(models_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
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
