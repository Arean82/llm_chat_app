# logic/llm_client.py
import json
from pathlib import Path
from openai import OpenAI


class LLMClient:
    """Manages NVIDIA NIM API connection with model switching"""
    
    def __init__(self):
        self.api_key = None
        self.current_model = "meta/llama-3.3-70b-instruct"
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.client = None
        
    def set_api_key(self, api_key: str):
        """Set API key and initialize client"""
        self.api_key = api_key
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=60.0
        )
        
    def set_model(self, model_id: str):
        """Switch the active model"""
        self.current_model = model_id
        
    def get_available_models(self):
        """Load available models from JSON file"""
        models_file = Path(__file__).parent.parent / "resources" / "models.json"
        with open(models_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data["models"]
    
    def has_api_key(self) -> bool:
        """Check if API key is configured"""
        return self.api_key is not None and self.api_key != ""
        
    def get_client(self):
        """Get the OpenAI client"""
        return self.client