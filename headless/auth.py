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
        
        # Load providers dynamically from the unified registry
        from logic.model_io import load_provider_metadata
        metadata = load_provider_metadata()
        raw_providers = metadata.get("providers", [])
        
        providers = []
        for p in raw_providers:
            providers.append({
                "id": p.get("id"),
                "group": p.get("group", "openai"),
                "sdk": p.get("sdk", "openai"),
                "ecosystem": p.get("display_name", p.get("id")),
                "url": p.get("default_url", ""),
                "requires_key": p.get("requires_key", True)
            })
        
        # 1. Select Platform / SDK Group
        raw_groups = metadata.get("groups", [])
        groups = [g["id"] for g in raw_groups]
        group_display_names = {g["id"]: g["name"] for g in raw_groups}
        
        print("\nStep 1: Select Platform/SDK Group:")
        for idx, grp in enumerate(groups, 1):
            print(f"  [{idx}] {group_display_names[grp]}")
            
        selection_grp = input(f"\nSelect Platform (1-{len(groups)}) [1]: ").strip()
        try:
            sel_grp_idx = int(selection_grp) - 1 if selection_grp else 0
            if sel_grp_idx < 0 or sel_grp_idx >= len(groups):
                sel_grp_idx = 0
        except ValueError:
            sel_grp_idx = 0
            
        target_group = groups[sel_grp_idx]
        
        # 2. Select Ecosystem under target Platform Group
        ecosystems = [p for p in providers if p["group"] == target_group]
        
        print(f"\nStep 2: Select Ecosystem under {group_display_names[target_group]}:")
        for idx, eco in enumerate(ecosystems, 1):
            requires_key_label = " (offline/local)" if not eco["requires_key"] else ""
            print(f"  [{idx}] {eco['ecosystem']}{requires_key_label}")
            
        selection_eco = input(f"\nSelect Ecosystem (1-{len(ecosystems)}) [1]: ").strip()
        try:
            sel_eco_idx = int(selection_eco) - 1 if selection_eco else 0
            if sel_eco_idx < 0 or sel_eco_idx >= len(ecosystems):
                sel_eco_idx = 0
        except ValueError:
            sel_eco_idx = 0
            
        selected_p = ecosystems[sel_eco_idx]
        p_id = selected_p["id"]
        eco_name = selected_p["ecosystem"]
        base_url = selected_p["url"]
        requires_key = selected_p["requires_key"]
        target_sdk = selected_p["sdk"]
        
        # 3. Capture Key (Only if required!)
        api_key = ""
        if requires_key:
            api_key = input(f"\nEnter API Key for {eco_name}: ").strip()
            if not api_key:
                print("[!] Error: API Key cannot be empty.")
                return False
        
        # 4. Save to Vault and Settings
        try:
            settings = get_app_settings()
            
            if requires_key and api_key:
                # Save to Keyring (both legacy/primary and modern status slots)
                keyring.set_password("LLMChatApp", f"api_key_{p_id}", api_key)
                if p_id == "nvidia":
                    keyring.set_password("LLMChatApp", "api_key", api_key) # Legacy compatibility
                
                # Write to modern hierarchical status slot to synchronize GUI indicators
                eco_key = eco_name.lower().replace(' ', '_')
                modern_key_id = f"api_key_{target_sdk}_{eco_key}"
                keyring.set_password("LLMChatApp", modern_key_id, api_key)
            
            # Save to Settings
            settings.setValue("active_provider_id", p_id)
            if base_url:
                settings.setValue(f"url_{p_id}", base_url)
                settings.setValue("base_url", base_url)
            else:
                settings.remove(f"url_{p_id}")
                settings.remove("base_url")
            
            settings.sync()
            
            # Re-hydrate the client to reflect changes
            client.hydrate()
            
            print("\n" + "-"*50)
            print(f"[SUCCESS] Ecosystem set to '{eco_name}'.")
            if requires_key:
                print("Credentials successfully saved to OS vault.")
            print("-"*50 + "\n")
            return True
            
        except Exception as e:
            print(f"[!] Critical Vault Error: {e}")
            return False
