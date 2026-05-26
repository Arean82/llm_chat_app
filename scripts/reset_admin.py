# scripts/reset_admin.py
# Universal Master Password Reset Sequence for SaaS, Desktop GUI, and CLI Headless Gates

import sys
import os

# Ensure the root directory is in the Python path to import modules properly
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from saas.tenant_db import TenantDatabaseManager

def reset_admin():
    print("======================================================================")
    print(" 🚀 UNIVERSAL MASTER PASSWORD RESET SEQUENCE")
    print("======================================================================")
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
        
    except Exception as e:
        print(f"❌ Critical: Universal admin reset failed: {e}")

if __name__ == "__main__":
    reset_admin()
