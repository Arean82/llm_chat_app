# logic/llm_client.py
# Enhanced Multi-Provider LLM Client supporting NVIDIA (OpenAI) & Google Gemini.

import json
import re
import time
from pathlib import Path
from openai import OpenAI
from server.utils.constants import OPENAI_BASE_URL

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

    def hydrate(self):
        """Loads available credentials from OS Keyring to restore session state with deep search."""
        from server.utils.path_utils import get_app_settings
        from server.utils.security_utils import decrypt_data, SESSION_MASTER_PASSWORD
        settings = get_app_settings()
        
        # Security Gate: If no active provider session exists in settings (e.g. user logged out),
        # strictly refuse to silently retrieve keys from the keyring vault.
        active_p = settings.value("active_provider_id")
        if not active_p:
            return
            
        import keyring
        active_p = str(active_p).lower()
        
        # 1. Restore Google Key (Centralized)
        gk = keyring.get_password("LLMChatApp", "api_key_google")
        if gk:
            gk = decrypt_data(gk, SESSION_MASTER_PASSWORD)
            self.set_google_api_key(gk)
        
        # 2. Deep Search for OpenAI/Generic Key
        ak = None
        # Priority A: Unified ID slot (e.g., api_key_nvidia)
        ak = keyring.get_password("LLMChatApp", f"api_key_{active_p}")
        
        if not ak:
            # Priority B: Legacy Ecosystem slot (e.g., api_key_openai_nvidia_nim)
            eco_guess = active_p.replace("_", " ")
            ak = keyring.get_password("LLMChatApp", f"api_key_openai_{eco_guess}")
            
        if not ak:
            # Priority C: Global legacy slots
            ak = keyring.get_password("LLMChatApp", "api_key") or keyring.get_password("LLMChatApp", "api_key_nvidia")
            
        if ak:
            ak = decrypt_data(ak, SESSION_MASTER_PASSWORD)
            self.set_api_key(ak)
            # Restore URL for this provider
            b_url = settings.value(f"url_{active_p}") or settings.value("base_url")
            if b_url and active_p != "google" and "google" not in b_url:
                self.set_base_url(b_url)

    def set_base_url(self, url: str):
        print(f"[LLMClient] Base URL set to: {url}")
        self.base_url = url
        if self.api_key:
            self._reinit_openai_client()

    def set_api_key(self, api_key: str):
        """Sets the active Nvidia API key and triggers OpenAI init."""
        print(f"[LLMClient] API Key updated (length: {len(api_key) if api_key else 0})")
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
            timeout=120.0
        )
        
    def set_model(self, model_id: str):
        self.current_model = model_id
        
    def get_available_models(self):
        from server.logic.model_io import load_all_models
        return load_all_models()
    
    def get_current_provider(self) -> str:
        """
        Detects the active backend provider dynamically based on the selected model ID.
        Returns 'google', 'nvidia', or custom provider IDs.
        """
        if not self.current_model:
            return "nvidia" # Safe baseline
            
        # 1. Thorough mapping scan from local disk cache (Source of Truth)
        models_list = self.get_available_models()
        for m in models_list:
            if m.get("id") == self.current_model:
                return m.get("provider", "nvidia") # defaults to nvidia if unlabeled
        
        # 2. Heuristic fallback for unknown/dynamic models
        mid_lower = self.current_model.lower()
        if "gemini" in mid_lower or mid_lower.startswith("models/gemini"):
            # Only return google if it's NOT an NVIDIA-prefixed model ID
            if "google/" not in mid_lower:
                return "google"
                
        return "nvidia"

    def is_model_vision_capable(self) -> bool:
        """
        Smart Validation Guard: Evaluates if current model supports binary image payloads.
        Prioritizes JSON schema explicit metadata, falling back to algorithmic root matching.
        """
        if not self.current_model:
            return False
            
        # Level 1: Explicit Metadata Scan
        models_list = self.get_available_models()
        for m in models_list:
            if m.get("id") == self.current_model:
                # Check for true truthy matches in user or provider config
                if m.get("vision") is True or str(m.get("vision")).lower() == "true":
                     return True
                if m.get("multimodal") is True or str(m.get("multimodal")).lower() == "true":
                     return True
                      
        # Heuristic fallback for vision
        mid_lower = self.current_model.lower()
        if "vision" in mid_lower or "-vl" in mid_lower or "pixtral" in mid_lower or "gemini" in mid_lower:
            return True
        return False

    def is_model_audio_capable(self) -> bool:
        """
        Smart Validation Guard: Evaluates if current model supports binary audio payloads.
        Prioritizes JSON schema explicit metadata, falling back to algorithmic root matching.
        """
        if not self.current_model:
            return False
        
        models_list = self.get_available_models()
        for m in models_list:
            if m.get("id") == self.current_model:
                if m.get("audio") is True or str(m.get("audio")).lower() == "true":
                    return True
        
        # Fallback keywords if metadata is missing
        mid_lower = self.current_model.lower()
        if "audio" in mid_lower or "voice" in mid_lower or "canary" in mid_lower or "gemini" in mid_lower:
            return True
        return False

    def is_model_video_capable(self) -> bool:
        """
        Smart Validation Guard: Evaluates if current model supports binary video payloads.
        Prioritizes JSON schema explicit metadata, falling back to algorithmic root matching.
        """
        if not self.current_model:
            return False
        
        models_list = self.get_available_models()
        for m in models_list:
            if m.get("id") == self.current_model:
                if m.get("video") is True or str(m.get("video")).lower() == "true":
                    return True
        
        # Fallback keywords if metadata is missing (Gemini 1.5/2.0 natively support video)
        mid_lower = self.current_model.lower()
        if "video" in mid_lower or "gemini-1.5" in mid_lower or "gemini-2.0" in mid_lower or "gemini-exp" in mid_lower:
            return True
        return False

    def is_model_coding_capable(self) -> bool:
        """
        Smart Validation Guard: Evaluates if current model is specialized/capable of coding/XML tasks.
        Prioritizes JSON schema explicit metadata, falling back to algorithmic root matching.
        """
        if not self.current_model:
            return False
        
        models_list = self.get_available_models()
        for m in models_list:
            if m.get("id") == self.current_model:
                if m.get("coding") is True or str(m.get("coding")).lower() == "true":
                    return True
        
        # Fallback keywords if metadata is missing
        mid_lower = self.current_model.lower()
        if "code" in mid_lower or "coder" in mid_lower or "codellama" in mid_lower or "gemini" in mid_lower or "gpt-4" in mid_lower:
            return True
        return False

    def has_api_key(self) -> bool:
        """Verify if the client has ANY valid active api keys set currently."""
        if self.is_local_provider():
            return True  # Local providers (Ollama/LM Studio) don't require keys
        provider = self.get_current_provider()
        if provider == "google":
            return bool(self.google_api_key)
        return bool(self.api_key)

    def is_local_provider(self) -> bool:
        """Determines if the current provider is a local/offline service (No key required)."""
        p_id = self.get_current_provider()
        from server.logic.model_io import load_provider_metadata
        metadata = load_provider_metadata()
        for p in metadata.get("providers", []):
            if p.get("id") == p_id:
                return not p.get("requires_key", True)
        return False

    def is_globally_authenticated(self) -> bool:
        """Determines if the application is logically 'Logged In' regardless of active slot."""
        return bool(self.api_key) or bool(self.google_api_key)

    # --- MULTI-PROVIDER ROUTER: GENERATION HELPERS ---
    
    def _run_completion_internal(self, system_msg: str, user_msg: str, max_tokens: int, temperature: float, force_json: bool = False) -> str:
        """
        Run a completion using the appropriate backend client.
        The provider is resolved dynamically via `get_current_provider()` and the
        client is obtained via `_get_provider_client`.
        """
        provider = self.get_current_provider()
        client = self._get_provider_client(provider)
        if not client:
            raise ValueError(f"{provider} client not configured yet.")
        try:
            # 1️⃣ Generic generate method (if the client implements it directly)
            if hasattr(client, "generate"):
                return client.generate(
                    system_msg=system_msg,
                    user_msg=user_msg,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    force_json=force_json,
                )
            # 2️⃣ Gemini‑style client (models.generate_content)
            if hasattr(client, "models") and hasattr(client.models, "generate_content"):
                gemini_kwargs = {
                    "model": self.current_model,
                    "contents": user_msg,
                    "config": types.GenerateContentConfig(
                        system_instruction=system_msg,
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        response_mime_type="application/json" if force_json else "text/plain",
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                        ],
                    ),
                }
                gemini_method = getattr(client.models, "generate_content")
                response = gemini_method(**gemini_kwargs)
                return getattr(response, "text")
            # 3️⃣ OpenAI‑compatible client (chat.completions.create)
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                req_params = {
                    "model": self.current_model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "user": "admin",
                }
                if force_json:
                    req_params["response_format"] = {"type": "json_object"}
                # Invoke the completion method dynamically
                completion_creator = getattr(client.chat.completions, "create")
                response = completion_creator(**req_params)
                refusal = getattr(response.choices[0].message, "refusal", None)
                if refusal:
                    raise ValueError(f"Request refused by model: {refusal}")
                return getattr(response.choices[0].message, "content")
            # 4️⃣ Anthropic‑compatible client (messages.create)
            if hasattr(client, "messages") and hasattr(client.messages, "create"):
                # Define safe upper bound for token usage
                MAX_TOKENS = 1024
                # Build request parameters with a default max_tokens value
                req_params = {
                    "model": self.current_model,
                    "messages": [
                        {"role": "user", "content": system_msg},
                        {"role": "assistant", "content": user_msg},
                    ],
                    "max_tokens": MAX_TOKENS,
                    "temperature": temperature,
                    # Anthropic supports a dedicated system field; include system prompt explicitly
                    "system": system_msg,
                    # Include metadata for abuse tracking; replace placeholder with actual hashed user ID at runtime
                    "metadata": {"user_id": "<hashed_user_id_placeholder>"},
                }
                # Override max_tokens if a valid lower value is provided
                if isinstance(max_tokens, int) and max_tokens <= MAX_TOKENS:
                    req_params["max_tokens"] = max_tokens
                if force_json:
                    # Anthropic uses "json" in `extra` parameter; placeholder
                    req_params["extra"] = {"response_format": {"type": "json_object"}}
                # Call Anthropic client with explicit max_tokens to satisfy security checks
                response = client.messages.create(
                    model=self.current_model,
                    messages=[
                        {"role": "user", "content": system_msg},
                        {"role": "assistant", "content": user_msg},
                    ],
                    max_tokens=req_params["max_tokens"],
                    temperature=temperature,
                    system=system_msg,
                    metadata={"user_id": "<hashed_user_id_placeholder>"},
                    **({"extra": req_params["extra"]} if "extra" in req_params else {}),
                )
                # Anthropic response: validate stop_reason THEN extract content
                stop_reason = getattr(response, "stop_reason", None)
                if stop_reason and stop_reason != "end_turn":
                    raise RuntimeError(f"Anthropic request stopped early: {stop_reason}")
                # stop_reason is valid — safe to read content
                content = getattr(response, "content", None)
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            return block["text"]
                        if hasattr(block, "text"):
                            return block.text
                return getattr(response, "text", "")
            # End of client handling
            # If no known method matched, raise
            raise NotImplementedError(f"Provider {provider} does not expose a known generation method.")
        except Exception as e:
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
            from server.workers.update_logger import get_logger
            get_logger().add_log(f"NVIDIA Model Discovery Failed: {e}", "ERROR")
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
            from server.workers.update_logger import get_logger
            get_logger().add_log(f"Google Model Discovery Failed: {e}", "ERROR")
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

    def generate_embeddings(self, text: str, user_id: int = 1) -> list:
        """
        Computes semantic vector embeddings utilizing the active API client credentials.
        Delegates dynamically to the decoupled EmbeddingService to ensure L2 caching and UI isolation.
        """

        # Updated embedding generation without hard‑coded provider strings
        from server.logic.services import ServiceRegistry
        try:
            embedding_svc = ServiceRegistry.get("embedding")
            return embedding_svc.generate_embedding(text, user_id, client_instance=self)
        except KeyError:
            if not text or not text.strip():
                return []
            import hashlib
            chunk_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            provider = self.get_current_provider()
            payload_slice = text[:8000]
            vector = []
            client = self._get_provider_client(provider)
            if provider == "google" and client and GOOGLE_SDK_AVAILABLE:
                try:
                    result = client.models.embed_content(
                        model="text-embedding-004",
                        contents=payload_slice
                    )
                    if result and result.embeddings:
                        vector = result.embeddings[0].values
                except Exception:
                    pass
            else:
                if client:
                    try:
                        resp = client.embeddings.create(
                            model="text-embedding-3-small",
                            input=payload_slice,
                            timeout=15.0
                        )
                        vector = resp.data[0].embedding
                    except Exception:
                        pass
            return vector

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

# Mock client for testing Phase 4 compression
class MockLLMClient(LLMClient):
    def _run_completion_internal(self, system_msg: str, user_msg: str, max_tokens: int, temperature: float, force_json: bool = False) -> str:
        # Return a deterministic short summary for compression tests
        return "[Mock summary] Key points extracted."

def get_mock_llm_client() -> LLMClient:
    mock = MockLLMClient()
    mock.hydrate()
    # Set a default model so provider resolution works without external config
    mock.current_model = "gpt-3.5-turbo"
    return mock
