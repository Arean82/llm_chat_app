# operator_tools/admin_reset/build.py
"""
Synora Studio - Admin Reset Tool Build Script
"""
import os
import subprocess
import sys

def main():
    print("Building Synora Admin Reset Tool...")
    cwd = os.path.dirname(os.path.abspath(__file__))
    subprocess.check_call(["pyinstaller", "reset_admin.spec", "--noconfirm"], cwd=cwd)
    print("Admin Reset Tool build completed successfully.")

if __name__ == "__main__":
    main()
