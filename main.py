# main.py
# This is the main entry point for the LLM Chat App. It initializes the application and shows the main window.  

import sys
import os
from pathlib import Path

import shutil

from utils.path_utils import get_resource_path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice

# from ui.main_window import MainWindowClass (Moved to main() for headless safety)
# ChatWorker import removed (handled by HeadlessEngine)

def detect_environment():
    """
    Logic: Detect if a Graphical User Interface is available.
    - Windows: Always assumes GUI unless running as a service or with --headless.
    - Linux: Checks for the 'DISPLAY' environment variable.
    - CLI Flag: Overrides with --headless if provided.
    """
    if "--headless" in sys.argv:
        return "HEADLESS"
    if sys.platform == "linux" and not os.environ.get('DISPLAY'):
        return "HEADLESS"
    return "GUI"


def smart_sync(src: Path, dst: Path):
    """Only copies src to dst if dst is missing or src is newer/different."""
    if not src.exists():
        return False
    
    should_copy = False
    if not dst.exists():
        should_copy = True
    else:
        # Compare modification times and sizes
        src_stat = src.stat()
        dst_stat = dst.stat()
        if src_stat.st_mtime > dst_stat.st_mtime or src_stat.st_size != dst_stat.st_size:
            should_copy = True
            
    if should_copy:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    return False

def copy_bundled_resources():
    """
    Handles resource synchronization for the EXE environment.
    - System Files: Updated only if the version in the EXE is newer.
    - User Files: Created only if missing.
    """
    if not getattr(sys, 'frozen', False):
        return
    
    try:
        from utils.storage_config import StorageManager
        bundle_dir = Path(sys._MEIPASS)
        # Crucial Fix: Extract into the verified writable storage path, not the EXE folder
        target_root = StorageManager.get_instance().get_storage_root()
        
        # 1. SYSTEM FILES & UI DESIGNER: Smart Sync (ensures updates without full wipe)
        system_files = [
            'resources/styles.qss',
            'resources/app_icon.png',
            'resources/app_icon.ico',
            'resources/app_icon.icns',
            'resources/app_icon_linux.png',
        ]
        
        for rel_path in system_files:
            smart_sync(bundle_dir / rel_path, target_root / rel_path)

        # Sync the entire UI designer folder individually
        bundle_ui = bundle_dir / "ui_designer"
        target_ui = target_root / "ui_designer"
        if bundle_ui.exists():
            for src_file in bundle_ui.rglob("*"):
                if src_file.is_file():
                    rel_path = src_file.relative_to(bundle_ui)
                    smart_sync(src_file, target_ui / rel_path)

        # 2. USER FILES: Only copy if MISSING (protects user work)
        # Dynamically sync any models_*.json files present in bundle
        bundle_res = bundle_dir / "resources"
        target_res = target_root / "resources"
        
        if bundle_res.exists():
            # Find all model manifests
            for src_file in bundle_res.glob("models_*.json"):
                dst_file = target_res / src_file.name
                if not dst_file.exists():
                    target_res.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
            
            # Handle specific fallback files
            legacy_files = ['models.json', 'user_prompts.json']
            for fname in legacy_files:
                src = bundle_res / fname
                dst = target_res / fname
                if src.exists() and not dst.exists():
                    target_res.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                
    except Exception as e:
        print(f"Resource sync error: {e}")

def main():
    # Detect Mode (GUI or Headless)
    env_mode = detect_environment()
    
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings
    
    # Global System-Level Configuration
    from utils.storage_config import StorageManager
    manager = StorageManager.get_instance()
    
    # Create the App instance first so we can apply styles/icons to it
    app = QApplication(sys.argv)
    
    if env_mode == "GUI":
        # 1. SET APP IDENTITY (Windows Taskbar Grouping)
        import platform
        if platform.system() == "Windows":
            import ctypes
            myappid = u'arean82.llmchatapp.v6.5'
            try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except: pass
            
        # 2. APPLY GLOBAL ICON
        from ui.shared_widgets import set_app_icon
        set_app_icon(app)

        # 3. LOAD STYLES
        from utils.path_utils import get_resource_path
        app.setStyle("Fusion")
    
    # --- SINGLE INSTANCE LOCK (Restored from v6) ---
    from PySide6.QtCore import QLockFile, QDir
    lock_path = os.path.join(QDir.tempPath(), "llm_chat_app_v6.lock")
    lock_file = QLockFile(lock_path)
    if not lock_file.tryLock(500):
        if env_mode == "GUI":
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Already Running")
            msg.setText("Another instance of LLM Chat App is already running.")
            msg.setInformativeText("Please close the existing instance before launching a new one.")
            msg.exec()
        else:
            print("[!] Error: Another instance of LLM Chat App is already running.")
        return
    
    # --- STORAGE CONFIGURATION LAYER ---
    from utils.storage_config import StorageManager
    from ui.first_run_dialog import FirstRunDialog
    from PySide6.QtCore import QSettings
    
    manager = StorageManager.get_instance()
    
    # Perform permission-based mode detection
    if manager.detect_existing_mode() is None:
        if env_mode == "GUI":
            setup_dlg = FirstRunDialog()
            if setup_dlg.exec() != FirstRunDialog.Accepted:
                sys.exit(0)
        else:
            # Headless default to APPDATA if not configured
            manager.finalize_setup("APPDATA")
            
    # GLORIOUS GLOBAL SWITCHER:
    # If we are portable, we override default QSettings storage globally to prevent Registry writes.
    if manager.is_portable:
        QSettings.setDefaultFormat(QSettings.IniFormat)
        # Explicitly set the scope path to the verified writable target root.
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(manager.get_storage_root()))
    
    # Now copy files safely without permission crash
    copy_bundled_resources()
    
    if env_mode == "GUI":
        from ui.main_window import MainWindowClass
        # Load stylesheet - use get_resource_path
        stylesheet_path = get_resource_path("resources/styles.qss")
        if stylesheet_path.exists():
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
                
        # Apply Global Application Icon (ALREADY HANDLED AT TOP)
        # from ui.shared_widgets import set_app_icon
        # set_app_icon(app) 
        
    # CLI Command Router
    if "--help" in sys.argv or "-h" in sys.argv:
        print("\n" + "="*50)
        print(" LLM CHAT APP - Headless Engine v6.5")
        print("="*50)
        print("Usage: python main.py [options]")
        print("\nOptions:")
        print("  --headless        Launch the standalone API Server (Port 5000)")
        print("  --list-models     List all models currently in the local manifest")
        print("  --update-models   Fetch latest models from the active provider")
        print("  --help / -h       Show this detailed help message")
        
        print("\nExamples:")
        print("  1. Configure Auth:  python main.py --headless (triggers prompt)")
        print("  2. Sync Models:     python main.py --update-models")
        print("  3. View manifest:   python main.py --list-models")
        
        print("\nDocumentation: see HEADLESS_GUIDE.md")
        print("="*50 + "\n")
        return

    if "--list-models" in sys.argv:
        from headless.models import HeadlessModels
        HeadlessModels.list_models()
        return

    if "--update-models" in sys.argv:
        from logic.llm_client import LLMClient
        from headless.models import HeadlessModels
        client = LLMClient()
        client.hydrate()
        HeadlessModels.update_models(client)
        return

    if "--headless" in sys.argv or (sys.platform == "linux" and not os.environ.get('DISPLAY')):
        # --- HEADLESS EXECUTION PATH ---
        from logic.llm_client import LLMClient
        client = LLMClient()
        client.hydrate()
        
        # 1. Initialize Headless Environment (CLI Auth + Manifest Sync)
        from headless.engine import HeadlessEngine
        try:
            HeadlessEngine.ensure_initialized(client)
        except Exception as e:
            print(f"[!] Headless Setup Failed: {e}")
            return

        # 2. Start API Manager with Headless Handler
        from logic.api_manager import ApiManager
        api_manager = ApiManager(client, request_handler_callback=HeadlessEngine.request_handler)
        
        try:
            api_manager.start_api_server()
            print("[+] Headless Engine is live. Listening for IDE requests...")
            print("[+] Press Ctrl+C to terminate safely.")
            
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Termination signal received.")
        finally:
            print("[*] Cleaning up headless services...")
            api_manager.stop_api_server()
            print("[+] Shutdown complete.")
    else:
        # --- GUI EXECUTION PATH ---
        from logic.llm_client import LLMClient
        client = LLMClient()
        client.hydrate()
        
        # Session Check: Only show gate if NOT authenticated
        if not client.is_globally_authenticated():
            from ui.login_dialog import LoginDialogClass
            login_dlg = LoginDialogClass()
            from ui.shared_widgets import set_app_icon
            set_app_icon(login_dlg)
            
            if not login_dlg.exec():
                print("[*] Login cancelled. Exiting.")
                sys.exit(0)
            
        # INITIALIZE MAIN WINDOW
        from ui.main_window import MainWindowClass
        window = MainWindowClass()
        window.showMaximized()  
        window.start_services()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
