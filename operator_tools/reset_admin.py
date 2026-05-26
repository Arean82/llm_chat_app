# operator_tools/reset_admin.py
# Universal Master Password Reset Sequence for SaaS, Desktop GUI, and CLI Headless Gates
# Designed to run securely as a standalone binary (reset_admin.exe) and compatible with system services.

import sys
import os

# Absolute service-friendly pathing resolution
if getattr(sys, 'frozen', False):
    root_dir = os.path.dirname(sys.executable)
else:
    # operator_tools/reset_admin.py is located under project_root/operator_tools/
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, root_dir)

from saas.tenant_db import TenantDatabaseManager

def reset_admin():
    print("======================================================================")
    print(" 🚀 UNIVERSAL MASTER PASSWORD RESET SEQUENCE")
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
        
    except Exception as e:
        print(f"❌ Critical: Universal admin reset failed: {e}")

if __name__ == "__main__":
    reset_admin()
