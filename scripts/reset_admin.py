import sys
import os

# Ensure the root directory is in the Python path to import modules properly
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from saas.tenant_db import TenantDatabaseManager

def reset_admin():
    print("Initiating Super Admin Reset Sequence...")
    try:
        db = TenantDatabaseManager()
        db.reset_admin_account()
        print("✅ Successfully reset the 'admin' account to default credentials.")
                
            print("\nDefault Master Credentials:")
            print("-------------------------")
            print("Username: admin")
            print("Email:    admin@quantum-saas.local")
            print("Password: admin")
            print("API Key (Passport): admin_master_passport")
            print("-------------------------")
            print("\nYou can use these credentials to log in to the SaaS Web Portal.")
            
        except Exception as e:
            print(f"❌ Failed to reset admin account: {e}")

if __name__ == "__main__":
    reset_admin()
