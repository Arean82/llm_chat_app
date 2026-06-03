import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web.app import create_saas_app
from server.utils.logger import AppLogger
from web.core.config_manager import SaaSConfigManager

def main():
    logger = AppLogger.get_instance("web")
    logger.info("Booting SaaS Web Portal in standalone mode...")
    
    config = SaaSConfigManager()
    host = config.get_str("NETWORK", "host", "127.0.0.1")
    port = config.get_int("NETWORK", "port", 8080)
    
    app = create_saas_app()
    print(f"[+] SaaS Web Portal is live. Listening on http://{host}:{port}...")
    
    try:
        from werkzeug.serving import make_server
        server = make_server(host, port, app, threaded=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down Web Portal...")
    except Exception as e:
        logger.error(f"Web Portal Crash: {e}")
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
