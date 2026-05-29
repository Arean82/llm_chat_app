import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web.app import create_saas_app
from server.utils.logger import AppLogger

def main():
    logger = AppLogger.get_instance("web")
    logger.info("Booting SaaS Web Portal in standalone mode...")
    
    app = create_saas_app()
    print("[+] SaaS Web Portal is live. Listening on http://127.0.0.1:8080...")
    
    try:
        from werkzeug.serving import make_server
        server = make_server('127.0.0.1', 8080, app, threaded=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down Web Portal...")
    except Exception as e:
        logger.error(f"Web Portal Crash: {e}")
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
