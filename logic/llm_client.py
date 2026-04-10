# logic/llm_client.py
# This module defines the LLMClient class, which manages interactions with the NVIDIA LLM API.

import json
from pathlib import Path
from openai import OpenAI


class LLMClient:
    def __init__(self):
        self.api_key = None
        self.current_model = None
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.client = None
        
    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=60.0
        )
        
    def set_model(self, model_id: str):
        self.current_model = model_id
        
    def get_available_models(self):
        from utils.path_utils import get_models_path
        models_file = get_models_path()
        with open(models_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data["models"]
    
    def has_api_key(self) -> bool:
        return self.api_key is not None and self.api_key != ""