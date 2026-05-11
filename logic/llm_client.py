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
        
    def set_base_url(self, url: str):
        self.base_url = url
        if self.api_key:
            self._reinit_client()

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self._reinit_client()

    def _reinit_client(self):
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

    def fetch_nvidia_catalog_models(self) -> dict:
        """
        Fetch models directly from NVIDIA's API catalog.
        Returns dict with 'free' and 'paid' model lists.
        Filters out non-chat models (embeddings, rerankers, deprecated, etc.)
        """
        if not self.client:
            raise ValueError("API key not set. Call set_api_key() first.")  

        result = {
            "free": [],
            "paid": [],
            "all": []
        }   

        # Models/patterns that should be excluded (won't work for chat)
        EXCLUDED_PATTERNS = [
            "embed",           # Embedding models
            "rerank",          # Reranker models
            "bge-m3",          # BAAI embedding model
            "nv-embed",        # NVIDIA embedding
            "e5-",             # E5 embedding models
            "parakeet",        # Speech-to-text
            "fastpitch",       # Text-to-speech
            "nemo",            # Nemo models (often not chat)
            "deprecated",      # Deprecated models
            "baai/bge",        # BAAI embedding
            "snowflake/",      # Some Snowflake models
            "nvidia/nv-",      # NVIDIA non-chat models
            "yi-large",        # ADD THIS - deprecated model
            "01-ai",           # ADD THIS - provider with broken models
            "paligemma",       # ADD THIS - vision model, not chat
            "recurrentgemma",  # ADD THIS - not chat compatible
            "shieldgemma",     # ADD THIS - safety model, not chat
            "fuyu",            # ADD THIS - vision model
            "dracarys",        # ADD THIS - may be broken
        ]

        # Known good providers (always chat-compatible)
        GOOD_PROVIDERS = ["meta", "google", "mistralai", "deepseek-ai", "z-ai", "microsoft", "qwen"]

        try:
            # Get all models accessible with current API key
            response = self.client.models.list()
            filtered_count = 0  

            for model in response.data:
                model_id_lower = model.id.lower()

                # Skip excluded patterns
                should_exclude = any(pattern in model_id_lower for pattern in EXCLUDED_PATTERNS)

                if should_exclude:
                    filtered_count += 1
                    print(f"Filtered out (non-chat): {model.id}")
                    continue
                
                # For models without clear provider, we still include but mark appropriately
                model_info = {
                    "id": model.id,
                    "name": self._format_model_name(model.id),
                    "description": "",  # API doesn't provide this
                    "developer": model.id.split('/')[0] if '/' in model.id else "NVIDIA",
                    "free": True,  # All accessible models are on free tier
                    "context_length": getattr(model, 'max_model_len', None),
                    "is_chat_model": True  # Mark as chat-compatible
                }
                result["all"].append(model_info)
                result["free"].append(model_info)   

            print(f"Fetched {len(result['all'])} chat-compatible models (filtered out {filtered_count} non-chat models)")
            return result   

        except Exception as e:
            print(f"Error fetching models: {e}")
            return result
    
    def _format_model_name(self, model_id: str) -> str:
        """Convert model ID to readable name"""
        if '/' in model_id:
            name = model_id.split('/')[-1]
        else:
            name = model_id

        # Clean up the name
        name = name.replace('-', ' ').replace('_', ' ')
        # Capitalize properly
        words = name.split()
        formatted = ' '.join(word.capitalize() for word in words)
        return formatted

    def generate_model_description(self, model_id: str, model_name: str = None) -> str:
        """
        Use a free model to generate a description for another model.
        This runs in the background and doesn't block the UI.
        """
        if not self.client or not self.current_model:
            return ""

        if not model_name:
            model_name = model_id.split('/')[-1].replace('-', ' ').title()

        prompt = f"""Generate a concise, one-sentence description for the AI model called "{model_name}" (ID: {model_id}).

    The description should:
    - Be 15-30 words maximum
    - Mention what the model is good at (coding, reasoning, general chat, multilingual, etc.)
    - Be factual and professional
    - Not include marketing hype

    Example: "Llama 3.3 70B is a powerful instruction-tuned model excelling at reasoning, code generation, and complex multi-step tasks."

    Now generate a description for {model_name}:"""

        try:
            response = self.client.chat.completions.create(
                model=self.current_model,
                messages=[
                    {"role": "system", "content": "You are a technical writer who writes concise, accurate model descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )

            description = response.choices[0].message.content.strip()
            description = description.strip('"\'')
            return description

        except Exception as e:
            error_msg = str(e)
            print(f"Error generating description for {model_id}: {error_msg}")

            # ADD THIS ERROR HANDLING:
            if "404" in error_msg or "Not Found" in error_msg:
                print(f"   → The model '{self.current_model}' may not support chat completions.")
                print(f"   → Try selecting a different model for description generation.")

            return ""

    def enrich_models_with_descriptions(self, models: list, background_callback=None) -> list:
        """
        Enrich a list of models using optimized BATCH generation.
        Dramatically faster than sequential methods.
        """
        if not self.client or not self.current_model:
            return models

        # 1. Identify ONLY models that need descriptions to minimize API load
        candidates = []
        for model in models:
            existing = model.get('description', '')
            # Only update if it's empty, short, or filler text
            if not existing or len(existing) < 25 or "no description" in existing.lower():
                candidates.append(model)

        if not candidates:
            return models # Nothing to do!

        total_candidates = len(candidates)
        
        # 2. Process in BATCHES to maximize performance without overloading context
        BATCH_SIZE = 10
        processed_count = 0

        for i in range(0, total_candidates, BATCH_SIZE):
            batch = candidates[i : i + BATCH_SIZE]
            
            # Run high-speed batch API request
            batch_results = self.generate_descriptions_batch(batch)
            
            # 3. Apply results back to original models
            for model in batch:
                model_id = model['id']
                # Lookup by ID in results
                if model_id in batch_results:
                    model['description'] = batch_results[model_id].strip('"\' ')
                    model['description_generated'] = True
                else:
                    # Fallback slightly meaningful descriptor
                    if not model.get('description'):
                         model['description'] = "Advanced LLM specializing in text generation and comprehension."
                    model['description_generated'] = False

            processed_count += len(batch)
            if background_callback:
                # Signal visual updates proportional to candidates processed
                background_callback(processed_count, total_candidates)
            
            # Minor 0.5s rest between chunks just as extra stability safety
            if i + BATCH_SIZE < total_candidates:
                import time
                time.sleep(0.5)

        return models
    
    def generate_descriptions_batch(self, models: list) -> dict:
        """
        Generate descriptions for MULTIPLE models in ONE API call.
        This is FAR more efficient than one call per model.
        """
        if not self.client or not self.current_model:
            return {}

        # Build a prompt that asks for all descriptions at once
        model_list = []
        for model in models:
            model_id = model['id']
            model_name = model.get('name', model_id.split('/')[-1].replace('-', ' ').title())
            model_list.append(f"- ID: {model_id}, Name: {model_name}")

        models_text = "\n".join(model_list)

        prompt = f"""You are a technical writer. Generate a ONE-SENTENCE description (15-30 words) for EACH model below.

    Models:
    {models_text}

    Return ONLY valid JSON with this exact format:
    {{
        "model_id_1": "description for model 1",
        "model_id_2": "description for model 2",
        ...
    }}

    Descriptions should be factual, mention what the model excels at (coding, reasoning, multilingual, vision, etc.).

    Now generate descriptions:"""

        try:
            try:
                response = self.client.chat.completions.create(
                    model=self.current_model,
                    messages=[
                        {"role": "system", "content": "You are a technical writer. Output ONLY raw JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2500,
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
            except Exception as e_inner:
                if "response_format" in str(e_inner).lower() or "400" in str(e_inner):
                    response = self.client.chat.completions.create(
                        model=self.current_model,
                        messages=[
                            {"role": "system", "content": "You are a technical writer. Output only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=2500,
                        temperature=0.2
                    )
                else:
                    raise e_inner

            import json
            raw_txt = response.choices[0].message.content.strip()
            import re
            match = re.search(r'\{.*\}', raw_txt, re.DOTALL)
            if match:
                raw_txt = match.group(0)
            
            result = json.loads(raw_txt)
            return result
        except Exception as e:
            print(f"Batch generation fully failed: {e}")
            return {}