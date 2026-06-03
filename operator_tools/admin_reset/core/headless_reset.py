# operator_tools/admin_reset/core/headless_reset.py

import sys
import os

if getattr(sys, 'frozen', False):
    root_dir = os.path.dirname(sys.executable)
else:
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.insert(0, root_dir)

from web.core.tenant_db import TenantDatabaseManager

def run_headless_reset(random_pass=False, custom_pass=None):
    print("======================================================================")
    print(" 🚀 UNIVERSAL MASTER PASSWORD RESET SEQUENCE (CLI MODE)")
    print("======================================================================")
    print(f"Resolving project root directory: {root_dir}")
    print("Detecting active database driver from 'saas/config.ini'...")
    
    try:
        import string, random
        db = TenantDatabaseManager()
        
        if random_pass:
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        elif custom_pass:
            new_password = custom_pass
        else:
            new_password = "admin"
            
        db.reset_admin_account(new_password)
        
        print("\n✅ Successfully synchronized Master Credentials across ALL ecosystems!")
        print("This applies universally to:")
        print("  1. Native Desktop GUI Admin Gateway")
        print("  2. SaaS Web Dashboard Portal")
        print("  3. Headless/CLI Node Service API endpoints")
        print("----------------------------------------------------------------------")
        print("  Master Profile:")
        print("  Username: admin")
        print("  Email:    admin@synora-studio.local")
        print(f"  Password: {new_password}")
        print("  API Key:  admin_master_passport")
        print("----------------------------------------------------------------------")
        print("\nNote: Stored API keys in your local OS Keyring will be safely secured")
        print(f"with the master password ('{new_password}') upon your next GUI desktop launch.")
        print("======================================================================\n")
        return 0
    except Exception as e:
        print(f"❌ Critical: Universal admin reset failed: {e}")
        return 1
