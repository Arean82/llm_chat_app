# saas/config_manager.py
"""
SaaS Configuration Manager
Governs standard-compliant INI file reading/writing for server operators.
Enables headless server admins to directly edit saas/config.ini with ease.
"""

import os
import configparser
from pathlib import Path
from utils.storage_config import StorageManager

class SaaSConfigManager:
    """
    Orchestrates isolated configuration persistence for the SaaS engine.
    Ensures programmatic GUI settings match manual headless INI edits.
    """
    
    def __init__(self):
        # Determine physical path of the configuration target
        # For portability & headless ease, we store it directly inside /saas/ if writable, 
        # otherwise fallback gracefully to Storage Root.
        proj_root = StorageManager.get_instance().get_exe_dir()
        self.config_path = proj_root / "saas" / "config.ini"
        
        # Fallback check if /saas/ is read-only (e.g. frozen in Program Files)
        if getattr(os, 'access', None) and os.path.exists(self.config_path.parent):
            if not os.access(str(self.config_path.parent), os.W_OK):
                self.config_path = StorageManager.get_instance().get_storage_root() / "saas_config.ini"
        else:
            # Ensure saas directory exists physically
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
        self.parser = configparser.ConfigParser(allow_no_value=True)
        self.load_or_create_default()

    def load_or_create_default(self):
        """Loads the INI document or bootstraps it with fully commented documentation."""
        if not self.config_path.exists():
            self._generate_documented_defaults()
        else:
            try:
                self.parser.read(str(self.config_path))
                # Self-Healing Block: Guarantee core keys exist even if user deleted lines
                changed = False
                if "NETWORK" not in self.parser:
                    self.parser.add_section("NETWORK")
                    changed = True
                
                defaults = {
                    ("NETWORK", "enabled"): "true",
                    ("NETWORK", "host"): "127.0.0.1",
                    ("NETWORK", "port"): "8888",
                    ("SECURITY", "public_signup"): "true",
                    ("SMTP_RELAY", "enabled"): "false",
                    ("SMTP_RELAY", "host"): "smtp.gmail.com",
                    ("SMTP_RELAY", "port"): "587",
                    ("SMTP_RELAY", "user"): "",
                    ("SMTP_RELAY", "password"): "",
                    ("GLOBAL_KEYS", "nvidia_api_key"): "",
                    ("GLOBAL_KEYS", "google_api_key"): "",
                    ("GLOBAL_KEYS", "openai_api_key"): ""
                }
                
                for (sec, key), val in defaults.items():
                    if sec not in self.parser:
                        self.parser.add_section(sec)
                        changed = True
                    if key not in self.parser[sec]:
                        self.parser[sec][key] = val
                        changed = True
                        
                if changed:
                    self.save()
            except Exception as e:
                print(f"[Config Exception]: Parse failure, regenerating defaults. Error: {e}")
                self._generate_documented_defaults()

    def _generate_documented_defaults(self):
        """Writes pristine default config template fitted with explanatory instructions."""
        template = """# ==============================================================
# SaaS Gateway Configuration Profile
# Manual edits are perfectly safe. Restart server to apply.
# ==============================================================

[NETWORK]
# Toggle the entire SaaS background network engine (true/false)
enabled = true

# Host binding:
#   - 127.0.0.1: Local computer security only.
#   - 0.0.0.0: Expose server to Wi-Fi/Local LAN network.
host = 127.0.0.1

# The network listener port (Default 8888)
port = 8888

[SECURITY]
# Allows remote guests to access validation/registration portals (true/false)
public_signup = true

[SMTP_RELAY]
# Toggle autonomous email alert notifications (true/false)
enabled = false

# Target SMTP server configurations
host = smtp.gmail.com
port = 587
user = 
password = 

[GLOBAL_KEYS]
# Master host-funded API keys for Admin-Funded user profiles
nvidia_api_key = 
google_api_key = 
openai_api_key = 
"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(template)
            # Immediately parse the newly generated template
            self.parser.read(str(self.config_path))
        except Exception as e:
            print(f"[CRITICAL]: Failed to generate config.ini: {e}")

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        try: return self.parser.getboolean(section, key, fallback=fallback)
        except: return fallback

    def get_str(self, section: str, key: str, fallback: str = "") -> str:
        try: return self.parser.get(section, key, fallback=fallback)
        except: return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        try: return self.parser.getint(section, key, fallback=fallback)
        except: return fallback

    def set_val(self, section: str, key: str, value: str):
        """Updates runtime cache memory."""
        if section not in self.parser:
            self.parser.add_section(section)
        self.parser.set(section, key, str(value).lower() if isinstance(value, bool) else str(value))

    def set_local_url(self, host: str, port: int) -> None:
        """Persist the computed local URL for the UI.
        The URL is stored under the NETWORK section as `local_access_url`.
        """
        url = f"http://{host}:{port}"
        self.set_val("NETWORK", "local_access_url", url)
        self.save()

    def save(self):
        """Hardware-flushes active memory back to the INI text document."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.parser.write(f)
        except Exception as e:
            print(f"[Config Exception]: Write to config.ini failed: {e}")
