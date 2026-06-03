# server/build.py
"""
Synora Studio - Server Build Script
"""
import os
import subprocess
import sys

def main():
    print("Building Synora Studio API Server...")
    cwd = os.path.dirname(os.path.abspath(__file__))
    subprocess.check_call(["pyinstaller", "server.spec", "--noconfirm"], cwd=cwd)
    print("Server build completed successfully.")

if __name__ == "__main__":
    main()
