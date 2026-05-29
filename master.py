import subprocess
import sys
import os
import time

def start_process(name, script_path):
    print(f"[*] Starting {name} from {script_path}...")
    # Use python executable currently running this script
    python_exe = sys.executable
    return subprocess.Popen([python_exe, script_path])

def main():
    print("="*60)
    print(" 🚀 LLM CHAT APP - MASTER ORCHESTRATOR")
    print("="*60)
    
    root_dir = os.path.abspath(os.path.dirname(__file__))
    
    processes = []
    
    try:
        # 1. Start the core backend server
        server_p = start_process("Backend Server", os.path.join(root_dir, "server", "run_server.py"))
        processes.append(("Server", server_p))
        time.sleep(1) # Give server time to bind ports
        
        # 2. Start the web SaaS portal
        web_p = start_process("Web SaaS Portal", os.path.join(root_dir, "web", "run_web.py"))
        processes.append(("Web", web_p))
        time.sleep(1)
        
        # 3. Start the Desktop GUI
        desktop_p = start_process("Desktop GUI", os.path.join(root_dir, "desktop", "main.py"))
        processes.append(("Desktop", desktop_p))
        
        print("\n[+] All modules have been successfully launched!")
        print("[+] Logs are being written to logs/server/, logs/web/, and logs/desktop/.")
        print("[+] Press Ctrl+C at any time to terminate all modules safely.\n")
        
        # Wait for the desktop app to exit, then gracefully kill others
        desktop_p.wait()
        print("\n[*] Desktop GUI closed. Initiating shutdown of remaining modules...")
        
    except KeyboardInterrupt:
        print("\n[*] Orchestrator terminated by user. Shutting down modules...")
    finally:
        for name, p in processes:
            if p.poll() is None:
                print(f"[*] Terminating {name}...")
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        print("[+] Master Orchestrator shutdown complete.")

if __name__ == "__main__":
    main()
