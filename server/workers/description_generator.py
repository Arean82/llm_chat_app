# workers/description_generator.py
# Background worker that uses the active hydrated model to generate rich descriptions for newly fetched models.

import json
from PySide6.QtCore import QThread, Signal
from server.workers.update_logger import get_logger
from server.utils.path_utils import get_models_path

class DescriptionGeneratorWorker(QThread):
    progress = Signal(int, int, str, str)
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, llm_client, generator_model: str, models_to_update: list, parent=None):
        super().__init__(parent)
        self.llm_client = llm_client
        self.generator_model = generator_model
        self.models_to_update = models_to_update
        self.logger = get_logger()
        
    def run(self):
        try:
            total = len(self.models_to_update)
            self.logger.add_log(f"Starting description generation using model: {self.generator_model}", "INFO")
            
            # Save the original model temporarily
            orig_model = self.llm_client.current_model
            # Switch to the generator model
            self.llm_client.set_model(self.generator_model)
            
            for i, model in enumerate(self.models_to_update):
                if self.isInterruptionRequested():
                    self.logger.add_log("Generation cancelled by user", "WARNING")
                    break
                
                model_id = model['id']
                model_name = model.get('name', model_id.split('/')[-1])
                
                self.progress.emit(i + 1, total, model_id, "Generating...")
                self.logger.add_log(f"[{i+1}/{total}] Generating description for {model_name}...", "INFO")
                
                try:
                    system_msg = "You are a technical writer. Output ONLY one short sentence (15-30 words). Be specific."
                    user_msg = f"Write a one-sentence description of the AI model '{model_name}'. What is it best at? Mention its key strength (coding, reasoning, multilingual, vision, math, etc.)."
                    
                    description = self.llm_client._run_completion_internal(
                        system_msg=system_msg,
                        user_msg=user_msg,
                        max_tokens=80,
                        temperature=0.3
                    )
                    description = description.strip().strip('"\'')
                    
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
            
            # Restore the original model
            self.llm_client.set_model(orig_model)
            
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
