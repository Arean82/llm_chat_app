# scripts/reset_admin.py
# ╔══════════════════════════════════════════════════════════════════╗
# ║  ⚠️  DEPRECATED — This script has been relocated.               ║
# ║                                                                  ║
# ║  The canonical Master Password Reset utility is now located at:  ║
# ║    operator_tools/reset_admin.py                                 ║
# ║                                                                  ║
# ║  This file is retained only as a redirect stub.                  ║
# ║  In production builds, use: reset_admin.exe                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os

# Redirect to the canonical operator_tools version
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

print("⚠️  scripts/reset_admin.py is DEPRECATED.")
print("    Redirecting to operator_tools/reset_admin.py...\n")

from operator_tools.reset_admin import reset_admin
reset_admin()
