# operator_tools/companion/build.py
"""
Synora Studio - Companion Operation Build Script
"""
import os
import subprocess
import sys

def main():
    print("Building Synora Companion Operation Tool...")
    cwd = os.path.dirname(os.path.abspath(__file__))
    subprocess.check_call(["pyinstaller", "companion_operation.spec", "--noconfirm"], cwd=cwd)
    print("Companion Operation build completed successfully.")

if __name__ == "__main__":
    main()
