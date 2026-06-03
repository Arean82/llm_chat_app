# scripts/build.py
"""
Synora Studio - Unified Build & Packaging Orchestrator (v9.0.0)
Auto-detects host environment and bundles public clients, admin panels, and extensions.
"""

import os
import sys
import platform
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, cwd=None):
    print(f"\n[*] Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        subprocess.check_call(cmd, shell=True, cwd=cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Command failed: {e}")
        return False

def build_pyinstaller_executables():
    print("\n=============================================================")
    # Check specs directory
    specs = [
        os.path.join(ROOT_DIR, "desktop", "desktop.spec"),
        os.path.join(ROOT_DIR, "server", "server.spec"),
        os.path.join(ROOT_DIR, "web", "web.spec"),
        os.path.join(ROOT_DIR, "operator_tools", "admin_reset", "reset_admin.spec"),
        os.path.join(ROOT_DIR, "operator_tools", "companion", "companion_operation.spec")
    ]
    
    print("[Step 1]: Compiling PyInstaller binaries...")
    for spec in specs:
        if os.path.exists(spec):
            run_command(["pyinstaller", f'"{spec}"', "--noconfirm"])
        else:
            print(f"[!] Warning: Spec file {spec} not found.")

def build_ide_plugins():
    print("\n=============================================================")
    print("[Step 2]: Packaging IDE Extensions...")
    
    # 1. VS Code Extension
    vscode_dir = os.path.join(ROOT_DIR, "extensions", "vscode-llm-chat")
    if os.path.exists(vscode_dir):
        print("\n[*] Bundling VS Code Extension...")
        if not os.path.exists(os.path.join(vscode_dir, "node_modules")):
            run_command("npm install", cwd=vscode_dir)
        run_command("npm run compile", cwd=vscode_dir)
        run_command("npx -y @vscode/vsce package", cwd=vscode_dir)
    
    # 2. JetBrains Extension
    jb_dir = os.path.join(ROOT_DIR, "extensions", "jetbrains-llm-chat")
    if os.path.exists(jb_dir):
        print("\n[*] Bundling JetBrains Extension...")
        gradlew = "gradlew.bat" if platform.system() == "Windows" else "./gradlew"
        run_command(f"{gradlew} buildPlugin", cwd=jb_dir)

def package_distributions():
    print("\n=============================================================")
    print("[Step 3]: Triggering Platform Installer Bundling...")
    
    system = platform.system()
    if system == "Windows":
        iscc = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if os.path.exists(iscc):
            run_command([f'"{iscc}"', "installer_script.iss"])
        else:
            print("[!] Inno Setup compiler (ISCC.exe) not found. Skip Windows Installer creation.")
            
    elif system == "Linux":
        if os.path.exists(os.path.join(ROOT_DIR, "build_deb.sh")):
            run_command("bash build_deb.sh")
        if os.path.exists(os.path.join(ROOT_DIR, "build_appimage.sh")):
            run_command("bash build_appimage.sh")
            
    elif system == "Darwin":
        if os.path.exists(os.path.join(ROOT_DIR, "build_mac.sh")):
            run_command("bash build_mac.sh")

def main():
    print("=============================================================")
    print("🚀 SYNORA STUDIO UNIFIED BUILD PIPELINE (v9.0.0)")
    print("=============================================================")
    
    # Run the sections
    build_pyinstaller_executables()
    build_ide_plugins()
    package_distributions()
    
    print("\n=============================================================")
    print("🎉 Unified Build Pipeline Execution Finished!")
    print("=============================================================")

if __name__ == "__main__":
    main()
