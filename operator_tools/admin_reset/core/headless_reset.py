# operator_tools/admin_reset/core/headless_reset.py

import sys
import os

if getattr(sys, 'frozen', False):
    root_dir = os.path.dirname(sys.executable)
else:
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.path.insert(0, root_dir)

from saas.tenant_db import TenantDatabaseManager

def run_headless_reset():
    print("======================================================================")
    print(" 🚀 UNIVERSAL MASTER PASSWORD RESET SEQUENCE (CLI MODE)")
    print("======================================================================")
    print(f"Resolving project root directory: {root_dir}")
    print("Detecting active database driver from 'saas/config.ini'...")
    
    try:
        db = TenantDatabaseManager()
        db.reset_admin_account()
        
        print("\n✅ Successfully synchronized default Master Credentials across ALL ecosystems!")
        print("This applies universally to:")
        print("  1. Native Desktop GUI Admin Gateway")
        print("  2. SaaS Web Dashboard Portal")
        print("  3. Headless/CLI Node Service API endpoints")
        print("----------------------------------------------------------------------")
        print("  Default Master Profile:")
        print("  Username: admin")
        print("  Email:    admin@quantum-saas.local")
        print("  Password: admin")
        print("  API Key:  admin_master_passport")
        print("----------------------------------------------------------------------")
        print("\nNote: Stored API keys in your local OS Keyring will be safely secured")
        print("with the master password ('admin') upon your next GUI desktop launch.")
        print("======================================================================\n")
        return 0
    except Exception as e:
        print(f"❌ Critical: Universal admin reset failed: {e}")
        return 1
