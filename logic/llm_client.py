# logic/llm_client.py
# Enhanced Multi-Provider LLM Client supporting NVIDIA (OpenAI) & Google Gemini.

import json
import re
import time
from pathlib import Path
from openai import OpenAI
from utils.constants import OPENAI_BASE_URL

try:
    from google import genai
    from google.genai import types
    GOOGLE_SDK_AVAILABLE = True
except ImportError:
    GOOGLE_SDK_AVAILABLE = False


class LLMClient:
    def __init__(self):
        self.api_key = None # OpenAI/Universal API Key
        self.google_api_key = None # Google API Key
        self.current_model = None
        self.base_url = OPENAI_BASE_URL
        
        # Clients
        self.client = None  # OpenAI/Nvidia Client instance
        self.google_client = None # Modern Google GenAI Client
        self.genai_configured = False

    def set_base_url(self, url: str):
        self.base_url = url
        if self.api_key:
            self._reinit_openai_client()

    def set_api_key(self, api_key: str):
        """Sets the active Nvidia API key and triggers OpenAI init."""
        self.api_key = api_key
        self._reinit_openai_client()

    def set_google_api_key(self, api_key: str):
        """Configures global Google GenerativeAI SDK credentials."""
        self.google_api_key = api_key
        if GOOGLE_SDK_AVAILABLE and api_key:
            try:
                self.google_client = genai.Client(api_key=api_key)
                self.genai_configured = True
            except Exception as e:
                print(f"CRITICAL: Failed to configure Google GenAI SDK: {e}")

    def clear_keys(self):
        self.api_key = None
        self.google_api_key = None
        self.client = None
        self.google_client = None
        self.genai_configured = False
        self.current_model = None

    def _reinit_openai_client(self):
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=60.0
        )
        
    def set_model(self, model_id: str):
        self.current_model = model_id
        
    def get_available_models(self):
        from logic.model_io import load_all_models
        return load_all_models()
    
    def get_current_provider(self) -> str:
        """
        Detects the active backend provider dynamically based on the selected model ID.
        Returns 'google' or 'nvidia'.
        """
        if not self.current_model:
            return "nvidia" # Safe baseline
            
        mid_lower = self.current_model.lower()
        # Instant shortcut heuristic check
        if "gemini" in mid_lower or mid_lower.startswith("models/gemini"):
            return "google"

        # Thorough mapping scan from local disk cache
        models_list = self.get_available_models()
        for m in models_list:
            if m.get("id") == self.current_model:
                return m.get("provider", "nvidia") # defaults to nvidia if unlabeled
                
        return "nvidia"

    def has_api_key(self) -> bool:
        """Verify if the client has ANY valid active api keys set currently."""
        provider = self.get_current_provider()
        if provider == "google":
            return bool(self.google_api_key)
        return bool(self.api_key)

    # --- MULTI-PROVIDER ROUTER: GENERATION HELPERS ---
    
    def _run_completion_internal(self, system_msg: str, user_msg: str, max_tokens: int, temperature: float, force_json: bool = False) -> str:
        """
        Polymorphic, single-call routine utilized by internal tooling (like Description Generators).
        Routes traffic natively to whichever client holds our active model.
        """
        provider = self.get_current_provider()
        
        # 🟢 Case A: Google Gemini Generation
        if provider == "google":
            if not self.google_client or not GOOGLE_SDK_AVAILABLE:
                raise ValueError("Google GenAI is not configured yet. Configure API Key.")
            
            try:
                response = self.google_client.models.generate_content(
                    model=self.current_model,
                    contents=user_msg,
                    config=types.GenerateContentConfig(
                        system_instruction=system_msg,
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        response_mime_type="application/json" if force_json else "text/plain"
                    )
                )
                return response.text
            except Exception as e:
                # Graceful degrade if response block issues happen
                raise e

        # 🔵 Case B: General OpenAI Ecosystem Generation
        else:
            if not self.client:
                raise ValueError("OpenAI-compatible client not configured yet. Set Active Provider in Settings.")
                
            req_params = {
                "model": self.current_model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            if force_json:
                req_params["response_format"] = {"type": "json_object"}

            try:
                response = self.client.chat.completions.create(**req_params)
                return response.choices[0].message.content
            except Exception as e:
                # Fallback if model rejected response_format trigger
                if force_json and ("response_format" in str(e).lower() or "400" in str(e)):
                    del req_params["response_format"]
                    req_params["messages"][0]["content"] += " IMPORTANT: Output only valid JSON."
                    response = self.client.chat.completions.create(**req_params)
                    return response.choices[0].message.content
                raise e


    # --- CORE FUNCTIONALITY SUITE (Descriptions, Enrichment) ---

    def fetch_nvidia_catalog_models(self) -> dict:
        """NVIDIA specific discovery. Will stay rigid to avoid regression."""
        if not self.client:
            raise ValueError("API key not set. Call set_api_key() first.")  
        result = {"free": [], "paid": [], "all": []}   
        EXCLUDED_PATTERNS = [
            "embed", "rerank", "bge-m3", "nv-embed", "e5-", "parakeet", 
            "fastpitch", "nemo", "deprecated", "baai/bge", "snowflake/", 
            "nvidia/nv-", "yi-large", "01-ai", "paligemma", "recurrentgemma", 
            "shieldgemma", "fuyu", "dracarys"
        ]
        try:
            response = self.client.models.list()
            for model in response.data:
                model_id_lower = model.id.lower()
                if any(pattern in model_id_lower for pattern in EXCLUDED_PATTERNS):
                    continue
                model_info = {
                    "id": model.id,
                    "name": self._format_model_name(model.id),
                    "description": "",
                    "developer": model.id.split('/')[0] if '/' in model.id else "NVIDIA",
                    "free": True,
                    "context_length": getattr(model, 'max_model_len', None),
                    "is_chat_model": True,
                    "provider": "nvidia"
                }
                result["all"].append(model_info)
                result["free"].append(model_info)   
            return result   
        except Exception as e:
            print(f"Error fetching models: {e}")
            return result

    def fetch_google_catalog_models(self) -> dict:
        """Discovers dynamic live models on user's Google AI project profile."""
        result = {"free": [], "paid": [], "all": []}
        if not GOOGLE_SDK_AVAILABLE or not self.google_client:
            return result
        try:
            # Modern SDK uses models.list()
            for model in self.google_client.models.list():
                mid = model.name
                if mid.startswith("models/"):
                     mid = mid.replace("models/", "")
                     
                # Verify it is a standard generation model
                actions = model.supported_actions or []
                if "generateContent" in actions or "generate_content" in str(actions).lower() or "gemini" in mid:
                    if "-00" in mid: continue  # Skip hyper-subvariants
                    
                    info = {
                        "id": mid,
                        "name": self._format_model_name(mid),
                        "description": model.description or "Google Generative Language Model.",
                        "developer": "Google",
                        "free": True,
                        "context_length": model.input_token_limit,
                        "is_chat_model": True,
                        "provider": "google"
                    }
                    result["all"].append(info)
                    result["free"].append(info)
            return result
        except Exception as e:
            print(f"Google dynamic discovery failed: {e}")
            return result

    def _format_model_name(self, model_id: str) -> str:
        name = model_id.split('/')[-1] if '/' in model_id else model_id
        name = name.replace('-', ' ').replace('_', ' ')
        words = name.split()
        return ' '.join(word.capitalize() for word in words)

    def generate_model_description(self, model_id: str, model_name: str = None) -> str:
        if not self.has_api_key() or not self.current_model:
            return ""
        if not model_name:
            model_name = model_id.split('/')[-1].replace('-', ' ').title()

        prompt = f"""Generate a concise, one-sentence description for the AI model called "{model_name}" (ID: {model_id}).
        Requirements: 15-30 words, mention strengths (coding, reasoning), factual."""
        sys_msg = "You are an expert technical writer providing concise, accurate descriptions."

        try:
            raw = self._run_completion_internal(sys_msg, prompt, 100, 0.3)
            return raw.strip('"\' ')
        except Exception as e:
            print(f"Failed generic description step: {e}")
            return ""

    def enrich_models_with_descriptions(self, models: list, background_callback=None) -> list:
        """Identical pipeline utilizing the newly abstractionized batch handler."""
        if not self.has_api_key() or not self.current_model:
            return models
        candidates = []
        for model in models:
            existing = model.get('description', '')
            if not existing or len(existing) < 25 or "no description" in existing.lower():
                candidates.append(model)
        if not candidates: return models
        
        total = len(candidates)
        BATCH_SIZE = 10
        processed = 0

        for i in range(0, total, BATCH_SIZE):
            batch = candidates[i : i + BATCH_SIZE]
            batch_results = self.generate_descriptions_batch(batch)
            
            for model in batch:
                m_id = model['id']
                if m_id in batch_results:
                    model['description'] = batch_results[m_id].strip('"\' ')
                    model['description_generated'] = True
                else:
                    if not model.get('description'):
                         model['description'] = "High-performance LLM specializing in knowledge parsing."
                    model['description_generated'] = False
            
            processed += len(batch)
            if background_callback:
                background_callback(processed, total)
            if i + BATCH_SIZE < total:
                time.sleep(0.5)
        return models
    
    def generate_descriptions_batch(self, models: list) -> dict:
        """Generates batch utilizing the cross-client wrapper supporting native JSON enforcement."""
        if not self.has_api_key() or not self.current_model:
            return {}

        model_list = []
        for m in models:
            mid = m['id']
            name = m.get('name', mid.split('/')[-1].replace('-', ' ').title())
            model_list.append(f"- ID: {mid}, Name: {name}")
        
        formatted_list = "\n".join(model_list)
        sys_msg = "You are a technical dictionary writer. Return raw parsable JSON ONLY."
        user_msg = f"""Generate ONE-SENTENCE factual descriptions for these models:
        {formatted_list}
        Format as rigid JSON dictionary: {{"id": "description"}}"""

        try:
            raw_content = self._run_completion_internal(sys_msg, user_msg, 2500, 0.2, force_json=True)
            match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if match:
                raw_content = match.group(0)
            return json.loads(raw_content)
        except Exception as e:
            print(f"Abstract Batch Generation Exception: {e}")
            return {}
    def fetch_custom_openai_models(self, base_url: str, api_key: str, provider_id: str = "openai") -> list:
        """
        UNIVERSAL OPENAI DISCOVERY (Audit ID 024)
        Dynamic scraper targeting third-party endpoints like LM Studio, Ollama, vLLM.
        """
        from openai import OpenAI
        effective_key = api_key if api_key and api_key.strip() else "no-key-required"
        tmp_client = OpenAI(base_url=base_url, api_key=effective_key, timeout=15.0)
        
        models_found = []
        try:
            response = tmp_client.models.list()
            EXCLUDED = ["embed", "rerank", "bge", "encoder", "bert", "fastpitch"]
            
            for model in response.data:
                mid = model.id
                if any(term in mid.lower() for term in EXCLUDED):
                    continue
                    
                c_len = 131072 # reasonable modern fallback
                if hasattr(model, 'max_model_len'): c_len = model.max_model_len
                
                model_info = {
                    "id": mid,
                    "name": self._format_model_name(mid),
                    "description": f"Dynamically acquired from custom host {base_url}",
                    "developer": provider_id.capitalize().replace("_", " "),
                    "free": True,
                    "context_length": c_len,
                    "is_chat_model": True,
                    "provider": provider_id
                }
                models_found.append(model_info)
                
            return models_found
        except Exception as e:
            print(f"Dynamic OpenAI endpoint scan failed for {base_url}: {e}")
            raise e
