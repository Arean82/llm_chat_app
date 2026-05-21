# saas/launcher.py
"""
Headless SaaS Launcher (Phase 6)
Orchestrates pure non-Qt domain controllers, initializes credentials, 
and hosts the standalone Flask server with synchronous callback routing.
"""

import sys
import time
import keyring
from pathlib import Path

# Core Domain Engine Imports (Strictly Non-UI)
from logic.llm_client import LLMClient
from logic.api_server import APIServer
from utils.storage_config import StorageManager
from utils.constants import OPENAI_BASE_URL
from saas.config_manager import SaaSConfigManager

def run_headless_saas():
    """
    Entrypoint dispatched by main.py --headless.
    Locks the running thread into the standalone Flask server instance.
    """
    print("\n=== [Headless SaaS Engine Initializing] ===")
    print("==========================================")
    
    # 1. Resolve Active Storage Mode (Dev/Portable/AppData)
    manager = StorageManager.get_instance()
    root_path = manager.get_storage_root()
    print(f"[*] Core Storage Root: {root_path}")
    
    # 2. Hydrate Persistent Platform Configuration
    settings = manager.get_active_settings()
    
    active_p = str(settings.value("active_provider_id", "nvidia"))
    base_url = settings.value(f"url_{active_p}") or settings.value("base_url", OPENAI_BASE_URL)
    current_model = str(settings.value("current_model_id", "")).strip()
    
    print(f"[*] Loaded Active Provider: {active_p.upper()}")
    print(f"[*] Target URL Target: {base_url}")
    
    # 3. Recover OS Secure Keyring Credentials
    print("[*] Restoring credentials vault...")
    api_key = keyring.get_password("LLMChatApp", f"api_key_{active_p}")
    if not api_key and active_p == "nvidia":
        # Legacy fallback safety Check
        api_key = keyring.get_password("LLMChatApp", "api_key")
        
    # Also check Google AI credentials if configuring Gemini
    google_key = keyring.get_password("LLMChatApp", "api_key_google")
    
    if not api_key and not google_key:
        print("[!] WARNING: No API Keys detected in system keyring! Headless node running in unauthenticated state.")
    else:
        print("[OK] System Vault Credentials Loaded Successfully.")

    # 4. Initialize the Global Inference Client
    llm_client = LLMClient()
    llm_client.set_base_url(base_url)
    
    if api_key:
        llm_client.set_api_key(api_key)
    if google_key:
        llm_client.set_google_api_key(google_key)
        
    # Set Model fallback if no model saved
    if not current_model:
        # Default safe fallback
        current_model = "meta/llama-3.1-8b-instruct" if "nvidia" in base_url else "gpt-4o-mini"
    
    llm_client.set_model(current_model)
    print(f"[*] Deployment Inference Model: {current_model}")

    # 5. Define Lightweight, Synchronous Direct Inference Handlers
    
    def get_messages_payload(user_msg, messages_list, system_msg):
        """Prepares uniform prompt context."""
        payload = []
        if system_msg:
            payload.append({"role": "system", "content": system_msg})
        
        if messages_list:
            # Ensure messages list doesn't double system prompt
            payload.extend([m for m in messages_list if m.get('role') != 'system'])
        else:
            payload.append({"role": "user", "content": user_msg})
        return payload

    def sync_send_message(user_msg, messages_list=None, system_message="", temperature=0.7, max_tokens=4096):
        """Polymorphic callback for standard synchronous generation requests."""
        provider = llm_client.get_current_provider()
        
        try:
            if provider == "google":
                # Rely on LLMClient Google SDK instance
                if not llm_client.google_client:
                    return "[Error]: Google Client configuration missing."
                from google.genai import types
                
                # Map payloads
                contents = [m.get('content') for m in get_messages_payload(user_msg, messages_list, "")]
                
                resp = llm_client.google_client.models.generate_content(
                    model=llm_client.current_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_message or None,
                        max_output_tokens=max_tokens,
                        temperature=temperature
                    )
                )
                return resp.text
            else:
                # Standard OpenAI-Compatible Client flow
                if not llm_client.client:
                    return "[Error]: API Gateway client not configured."
                
                messages = get_messages_payload(user_msg, messages_list, system_message)
                resp = llm_client.client.chat.completions.create(
                    model=llm_client.current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return resp.choices[0].message.content
        except Exception as e:
            print(f"[Headless Engine Error]: {e}")
            return f"[API Node Error]: {str(e)}"

    def sync_stream_message(user_msg, system_message="", temperature=0.7, max_tokens=4096, messages_list=None):
        """Polymorphic callback for real-time server-sent event stream chunks."""
        provider = llm_client.get_current_provider()
        
        try:
            if provider == "google":
                if not llm_client.google_client:
                    yield "[Error: Google Client missing]"
                    return
                from google.genai import types
                contents = [m.get('content') for m in get_messages_payload(user_msg, messages_list, "")]
                
                chunks = llm_client.google_client.models.generate_content_stream(
                    model=llm_client.current_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_message or None,
                        max_output_tokens=max_tokens,
                        temperature=temperature
                    )
                )
                for chk in chunks:
                    if chk.text:
                        yield chk.text
            else:
                # Standard OpenAI stream loop
                if not llm_client.client:
                    yield "[Error: OpenAI Client missing]"
                    return
                
                messages = get_messages_payload(user_msg, messages_list, system_message)
                stream = llm_client.client.chat.completions.create(
                    model=llm_client.current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
        except Exception as e:
            print(f"[Headless Streaming Error]: {e}")
            yield f"\n[API Node Error]: {str(e)}"

    # 6. Initialize and Bind the Standalone Multi-Tenant SaaS Server
    print("[*] Reading physical server configuration...")
    cfg = SaaSConfigManager()
    
    # Enforce CLI override or soft-disable gate
    if not cfg.get_bool("NETWORK", "enabled", True):
        print("[!] WARNING: Network SaaS is disabled in saas/config.ini! Overriding for headless CLI session.")
        
    host = cfg.get_str("NETWORK", "host", "127.0.0.1")
    port = cfg.get_int("NETWORK", "port", 8888)
    
    print(f"[*] Mobilizing Cloud SaaS Platform Console ({host}:{port})...")
    from saas.app import SaaSServer
    
    # Initialize headless Qt Application context so QThread works
    from PySide6.QtCore import QCoreApplication
    import sys
    if not QCoreApplication.instance():
        app = QCoreApplication(sys.argv)
        
    server = SaaSServer(host=host, port=port)
    
    success, message = server.start_server()
    if not success:
        print(f"[!] CRITICAL FAILURE: Gateway failed to bind. Details: {message}")
        sys.exit(1)
        
    print("[SUCCESS] Multi-Tenant Cloud SaaS Engine is online and listening!")
    print("----------------------------------------------------------------")
    print(f"[Web Dashboard  ]: http://{host}:{port}/")
    print(f"[Health Endpoint]: http://{host}:{port}/health")
    print("----------------------------------------------------------------")
    print("[Status]: Running standalone cloud node (Press Ctrl+C to terminate).")
    
    # 7. Thread Lock: Lock execution loop to keep the daemon thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Gracefully terminating Headless SaaS server services...")
        server.stop()
        print("[OK] Server offline. Exiting node.")
        sys.exit(0)
