# workers/model_fetch_worker.py
from PySide6.QtCore import QThread, Signal
from openai import OpenAI
from workers.update_logger import get_logger

class ModelFetchWorker(QThread):
    progress = Signal(int, int, str, str)
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.working_count = 0
        self.logger = get_logger()
        
    def run(self):
        try:
            self.logger.add_log("Connecting to NVIDIA API...", "INFO")
            
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=15.0
            )
            
            response = client.models.list()
            all_models = response.data
            total = len(all_models)
            
            self.logger.add_log(f"Found {total} total models. Testing each...", "INFO")
            
            working_models = []
            
            for i, model in enumerate(all_models):
                if self.isInterruptionRequested():
                    self.logger.add_log("Fetch cancelled by user", "WARNING")
                    break
                
                model_id = model.id
                self.progress.emit(i + 1, total, model_id, "Testing...")
                
                try:
                    # Test if model works for chat
                    test_response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": "Hi"}],
                        max_tokens=5,
                        timeout=5.0
                    )
                    
                    self.logger.add_log(f"✓ {model_id} - testing passed", "INFO")
                    
                    # Generate description
                    self.progress.emit(i + 1, total, model_id, "Generating description...")
                    self.logger.add_log(f"  Generating description for {model_id}...", "INFO")
                    
                    desc_response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "You are a technical writer. Respond with ONLY one short sentence (15-30 words)."},
                            {"role": "user", "content": f"Describe yourself ({model_id}) in one sentence. What are you best at?"}
                        ],
                        max_tokens=60,
                        temperature=0.3,
                        timeout=10.0
                    )
                    
                    description = desc_response.choices[0].message.content.strip()
                    description = description.strip('"\'')
                    
                    working_models.append({
                        "id": model_id,
                        "name": self._format_name(model_id),
                        "description": description if description else "No description available",
                        "developer": model_id.split('/')[0] if '/' in model_id else "NVIDIA",
                        "free": True,
                    })
                    
                    self.working_count += 1
                    self.logger.add_log(f"✓ {model_id} - description generated ({self.working_count}/{total})", "SUCCESS")
                    
                except Exception as e:
                    self.logger.add_log(f"✗ {model_id} - failed: {str(e)[:50]}", "WARNING")
                    continue
                
                # Rate limit safety
                if i < total - 1:
                    self.msleep(200)
            
            self.logger.add_log(f"Fetch complete! Found {self.working_count} working chat models", "SUCCESS")
            self.finished.emit(working_models)
            
        except Exception as e:
            self.logger.add_log(f"Fetch error: {str(e)}", "ERROR")
            self.error.emit(str(e))
    
    def _format_name(self, model_id: str) -> str:
        if '/' in model_id:
            name = model_id.split('/')[-1]
        else:
            name = model_id
        name = name.replace('-', ' ').replace('_', ' ')
        words = name.split()
        return ' '.join(word.capitalize() for word in words)