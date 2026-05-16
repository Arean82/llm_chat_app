# workers/description_generator.py

from PySide6.QtCore import QThread, Signal
from openai import OpenAI
from workers.update_logger import get_logger
import json
from utils.path_utils import get_models_path

class DescriptionGeneratorWorker(QThread):
    progress = Signal(int, int, str, str)
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, api_key: str, generator_model: str, models_to_update: list, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.generator_model = generator_model
        self.models_to_update = models_to_update
        from utils.constants import OPENAI_BASE_URL
        self.base_url = OPENAI_BASE_URL
        self.logger = get_logger()
        
    def run(self):
        try:
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=30.0
            )
            
            total = len(self.models_to_update)
            self.logger.add_log(f"Starting description generation using {self.generator_model}", "INFO")
            
            for i, model in enumerate(self.models_to_update):
                if self.isInterruptionRequested():
                    self.logger.add_log("Generation cancelled by user", "WARNING")
                    break
                
                model_id = model['id']
                model_name = model.get('name', model_id.split('/')[-1])
                
                self.progress.emit(i + 1, total, model_id, "Generating...")
                self.logger.add_log(f"[{i+1}/{total}] Generating description for {model_name}...", "INFO")
                
                try:
                    response = client.chat.completions.create(
                        model=self.generator_model,
                        messages=[
                            {"role": "system", "content": "You are a technical writer. Output ONLY one short sentence (15-30 words). Be specific."},
                            {"role": "user", "content": f"Write a one-sentence description of the AI model '{model_name}'. What is it best at? Mention its key strength (coding, reasoning, multilingual, vision, math, etc.)."}
                        ],
                        max_tokens=80,
                        temperature=0.3,
                        timeout=15.0
                    )
                    
                    description = response.choices[0].message.content.strip()
                    description = description.strip('"\'')
                    
                    if description and len(description) > 10:
                        model['description'] = description
                        self.logger.add_log(f"✓ {model_name} - description generated", "SUCCESS")
                    else:
                        model['description'] = "No description available"
                        self.logger.add_log(f"⚠ {model_name} - generated empty description", "WARNING")
                    
                except Exception as e:
                    model['description'] = "No description available"
                    self.logger.add_log(f"✗ {model_name} - failed: {str(e)[:80]}", "WARNING")
                
                self.progress.emit(i + 1, total, model_id, "Saved")
                
                if i < total - 1:
                    self.msleep(200)  # Rate limit safety
            
            # Save to file
            models_file = get_models_path()
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update descriptions
            updated_lookup = {m['id']: m for m in self.models_to_update}
            for i, model in enumerate(data['models']):
                if model['id'] in updated_lookup:
                    data['models'][i]['description'] = updated_lookup[model['id']]['description']
            
            with open(models_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            self.logger.add_log(f"Description generation complete! Updated {len(self.models_to_update)} models", "SUCCESS")
            self.finished.emit()
            
        except Exception as e:
            self.logger.add_log(f"Generation error: {str(e)}", "ERROR")
            self.error.emit(str(e))