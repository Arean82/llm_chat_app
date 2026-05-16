# headless/auth.py
# Specialized CLI-based authentication handler for headless execution.
# Allows configuring API keys directly from the terminal without a GUI.

import keyring
from utils.path_utils import get_app_settings
from logic.llm_client import LLMClient

class HeadlessAuth:
    """
    Handles terminal-based credential entry and vault synchronization.
    """
    
    @staticmethod
    def run_login_flow(client: LLMClient):
        """
        Interactively prompts for credentials in the terminal.
        """
        print("\n" + "="*50)
        print(" LLM CHAT APP: CLI AUTHENTICATION GATE")
        print("="*50)
        print("No active session found. Please configure your provider.")
        
        # 1. Select Provider
        print("\nAvailable Providers:")
        print(" - nvidia  (NVIDIA NIM / Open-AI Compatible)")
        print(" - google  (Gemini API)")
        print(" - openai  (Official OpenAI API)")
        
        p_id = input("\nSelect Provider [nvidia]: ").strip().lower() or "nvidia"
        
        # 2. Capture Key
        api_key = input(f"Enter API Key for {p_id}: ").strip()
        if not api_key:
            print("[!] Error: API Key cannot be empty.")
            return False
            
        # 3. Capture Base URL (Optional)
        base_url = ""
        if p_id != "google":
            default_url = "https://integrate.api.nvidia.com/v1" if p_id == "nvidia" else "https://api.openai.com/v1"
            base_url = input(f"Enter Base URL [{default_url}]: ").strip() or default_url
            
        # 4. Persist to Vault and Settings
        try:
            settings = get_app_settings()
            
            # Save to Keyring
            keyring.set_password("LLMChatApp", f"api_key_{p_id}", api_key)
            if p_id == "nvidia":
                keyring.set_password("LLMChatApp", "api_key", api_key) # Legacy compatibility
            
            # Save to Settings
            settings.setValue("active_provider_id", p_id)
            if base_url:
                settings.setValue(f"url_{p_id}", base_url)
                settings.setValue("base_url", base_url)
            
            settings.sync()
            
            # Re-hydrate the client to reflect changes
            client.hydrate()
            
            print("\n" + "-"*50)
            print(f"[SUCCESS] Credentials for '{p_id}' saved to OS vault.")
            print("-"*50 + "\n")
            return True
            
        except Exception as e:
            print(f"[!] Critical Vault Error: {e}")
            return False
