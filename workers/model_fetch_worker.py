# workers/model_fetch_worker.py
# This file runs in a background thread to fetch, test, and generate descriptions for NVIDIA NIM models.

from PySide6.QtCore import QThread, Signal
from openai import OpenAI
from workers.update_logger import get_logger

class ModelFetchWorker(QThread):
    progress = Signal(int, int, str, str)
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, api_key: str, base_url: str, parent=None):
        super().__init__(parent)
        from utils.constants import OPENAI_BASE_URL
        self.api_key = api_key
        self.base_url = base_url if base_url else OPENAI_BASE_URL
        self.working_count = 0
        self.logger = get_logger()
        # Removed hardcoded futuristic models causing fetch lockout.
        # Every model will describe itself dynamically during loop iteration.
        
    def run(self):
        try:
            self.logger.add_log("Connecting to Universal API...", "INFO")
            
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=15.0
            )
            
            # Automated reflective description builder (Audit ID 030 Patch)
            self.logger.add_log("Initialization successful.", "INFO")
            
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
                    
                    # Generate description using dedicated model
                    self.progress.emit(i + 1, total, model_id, "Generating description...")
                    self.logger.add_log(f"  Generating description for {model_id}...", "INFO")
                    
                    # Extract model name for better description
                    model_name = model_id.split('/')[-1] if '/' in model_id else model_id
                    developer = model_id.split('/')[0] if '/' in model_id else "NVIDIA"
                    
                    desc_response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "You are a technical writer. Output ONLY one short sentence (15-30 words). Be specific and factual."},
                            {"role": "user", "content": f"Write a one-sentence description of the AI model '{model_name}' from {developer}. What is it best at? Mention its key strength (coding, reasoning, multilingual, vision, math, etc.)."}
                        ],
                        max_tokens=80,
                        temperature=0.3,
                        timeout=10.0
                    )
                    
                    description = desc_response.choices[0].message.content.strip()
                    description = description.strip('"\'')
                    
                    # Clean up common issues
                    if description.startswith("Here is a one-sentence description") or description.startswith("Here's"):
                        # Try one more time with stricter prompt
                        desc_response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": "Output ONLY the description. No prefixes, no explanations."},
                                {"role": "user", "content": f"Describe {model_name} in 15-30 words."}
                            ],
                            max_tokens=80,
                            temperature=0.2,
                            timeout=10.0
                        )
                        description = desc_response.choices[0].message.content.strip()
                        description = description.strip('"\'')
                    
                    if not description or len(description) < 10:
                        description = f"{model_name} from {developer} - AI model for general purpose tasks."
                    
                    working_models.append({
                        "id": model_id,
                        "name": self._format_name(model_id),
                        "description": description,
                        "developer": developer.capitalize(),
                        "free": True,
                        "context_length": getattr(model, 'max_model_len', None),
                        "type": "chat"
                    })
                    
                    self.working_count += 1
                    self.logger.add_log(f"✓ {model_id} - description generated ({self.working_count}/{total})", "SUCCESS")
                    
                except Exception as e:
                    error_msg = str(e)
                    model_id_lower = model_id.lower()
                    developer = model_id.split('/')[0] if '/' in model_id else "NVIDIA"
                    model_name = model_id.split('/')[-1] if '/' in model_id else model_id
                    
                    # Classify if this is a specialized non-chat model we want to keep
                    is_specialized = False
                    model_type = "other"
                    description = ""
                    
                    if "embed" in model_id_lower:
                        is_specialized = True
                        model_type = "embedding"
                        description = f"Embedding model from {developer.capitalize()} for high-density vector representations and similarity tasks."
                    elif "rerank" in model_id_lower:
                        is_specialized = True
                        model_type = "reranking"
                        description = f"Reranker model from {developer.capitalize()} for high-accuracy semantic relevance refinement."
                    elif any(k in model_id_lower for k in ["audio", "voice", "canary", "stt", "tts", "speech"]):
                        is_specialized = True
                        model_type = "audio"
                        description = f"Audio/Voice processing model from {developer.capitalize()} for speech-to-text, translation, or voice synthesis."
                    elif any(k in model_id_lower for k in ["diffusion", "image", "sd", "paint", "kosmos"]):
                        is_specialized = True
                        model_type = "image"
                        description = f"Visual generative model from {developer.capitalize()} for image and multi-modal synthesis."
                    elif any(k in model_id_lower for k in ["guard", "nemoguard", "shield"]):
                        is_specialized = True
                        model_type = "guardrail"
                        description = f"Safety and content guardrail model from {developer.capitalize()}."
                        
                    if is_specialized:
                        working_models.append({
                            "id": model_id,
                            "name": self._format_name(model_id),
                            "description": description,
                            "developer": developer.capitalize(),
                            "free": True,
                            "context_length": getattr(model, 'max_model_len', None),
                            "type": model_type
                        })
                        self.working_count += 1
                        self.logger.add_log(f"✓ {model_id} - identified as {model_type} model ({self.working_count}/{total})", "SUCCESS")
                    else:
                        if len(error_msg) > 100:
                            error_msg = error_msg[:100] + "..."
                        self.logger.add_log(f"✗ {model_id} - skipped/failed: {error_msg}", "WARNING")
                    continue
                
                # Rate limit safety
                if i < total - 1:
                    self.msleep(200)
            
            self.logger.add_log(f"Fetch complete! Found {self.working_count} total models", "SUCCESS")
            self.finished.emit(working_models)
            
        except Exception as e:
            self.logger.add_log(f"Fetch error: {str(e)}", "ERROR")
            self.error.emit(str(e))
    
    def _format_name(self, model_id: str) -> str:
        if '/' in model_id:
            name = model_id.split('/')[-1]
        else:
            name = model_id
        # Remove common suffixes
        name = name.replace('-instruct', '').replace('-chat', '').replace('-preview', '')
        name = name.replace('-', ' ').replace('_', ' ')
        # Capitalize properly
        words = name.split()
        formatted = ' '.join(word.capitalize() for word in words)
        return formatted
    
    
