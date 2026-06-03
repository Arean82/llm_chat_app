# desktop/build.py
"""
Synora Studio - Desktop Build Script
"""
import os
import subprocess
import sys

def main():
    print("Building Synora Studio Desktop Client...")
    cwd = os.path.dirname(os.path.abspath(__file__))
    subprocess.check_call(["pyinstaller", "desktop.spec", "--noconfirm"], cwd=cwd)
    print("Desktop Client build completed successfully.")

if __name__ == "__main__":
    main()
