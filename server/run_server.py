import sys
import os
import time

# Add the root directory to sys.path so 'server' and 'desktop' modules resolve
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_headless_server():
    from server.utils.logger import AppLogger
    logger = AppLogger.get_instance("server")
    logger.info("Starting isolated backend server...")
    
    from server.logic.llm_client import LLMClient
    client = LLMClient()
    client.hydrate()
    
    # 1. Initialize Headless Environment
    from desktop.headless.engine import HeadlessEngine
    try:
        HeadlessEngine.ensure_initialized(client)
    except Exception as e:
        logger.error(f"Headless Setup Failed: {e}")
        print(f"[!] Headless Setup Failed: {e}")
        return

    # 2. Start API Manager with Headless Handler
    from server.logic.api_manager import ApiManager
    api_manager = ApiManager(client, request_handler_callback=HeadlessEngine.request_handler)
    
    try:
        api_manager.start_api_server()
        print("[+] Backend Engine is live. Listening for API requests on Port 5000...")
        print("[+] Press Ctrl+C to terminate safely.")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Termination signal received.")
    finally:
        print("[*] Cleaning up backend services...")
        api_manager.stop_api_server()
        print("[+] Shutdown complete.")

if __name__ == "__main__":
    run_headless_server()
