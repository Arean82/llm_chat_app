import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from web.tenant_db import TenantDatabaseManager
db = TenantDatabaseManager()
db.reset_admin_account()
print("Success! Admin password has been reset to 'admin'. You can now login.")
