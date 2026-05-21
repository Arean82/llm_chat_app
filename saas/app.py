# saas/app.py
"""
Unified SaaS Multi-Tenant Flask Application Engine (Phase 6)
Orchestrates JWT/Passport gateway auth, dynamic workspace routing, 
economic feature locks on Model Arena, and autonomous SMTP alerts.
"""

import os
import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, Response, stream_with_context, render_template

from saas.tenant_db import TenantDatabaseManager
from logic.llm_client import LLMClient
from utils.storage_config import StorageManager

def create_saas_app():
    """
    Core Factory initializing the unified, multi-tenant API routing ecosystem.
    """
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
    
    # Explicitly force correct MIME mappings (combats severe Windows Registry corruptions preventing CSS/JS loading)
    import mimetypes
    mimetypes.add_type('text/css', '.css')
    mimetypes.add_type('application/javascript', '.js')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    db = TenantDatabaseManager()
    
    # Load Optional SMTP definitions
    def send_alert_email(to_email, subject, html_content):
        """Inbuilt autonomous SMTP Relay (enforcing zero external SaaS dependency)."""
        try:
            # In production, these load from OS EnvVars or resources/smtp_config.json
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_pass = os.getenv("SMTP_PASS", "")
            
            if not smtp_user or not smtp_pass:
                # Gracefully bypass if user hasn't configured relay variables
                return False
                
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"LLM Chat App Security <{smtp_user}>"
            msg["To"] = to_email
            
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, msg.as_string())
            return True
        except Exception as e:
            print(f"[SMTP Warning]: Autonomous alert failed: {e}")
            return False

    def get_provider_base_url(provider_id: str) -> str:
        """Resolves default API base URLs dynamically from centralized registry configuration."""
        default_urls = {
            "nvidia": "https://integrate.api.nvidia.com/v1",
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "lmstudio": "http://localhost:1234/v1",
            "ollama": "http://localhost:11434/v1"
        }
        try:
            from utils.path_utils import get_resource_path
            conf_path = get_resource_path("resources/api_providers.json")
            if os.path.exists(conf_path):
                with open(conf_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for p in data.get("providers", []):
                        if p.get("id") == provider_id:
                            return p.get("default_url", default_urls.get(provider_id, "https://integrate.api.nvidia.com/v1"))
        except Exception as e:
            print(f"[API Warning]: URL provider lookup failed: {e}")
        return default_urls.get(provider_id, "https://integrate.api.nvidia.com/v1")

    # --- CORE PRE-FLIGHT PASS-KEY PASSPORT HANDSHAKES ---

    @app.route('/api/validate_passport', methods=['POST'])
    def validate_passport():
        """
        Pre-flight validation handshake performing real-time live check 
        against NVIDIA/OpenAI endpoints prior to allowing profile creation.
        """
        data = request.get_json() or {}
        api_key = data.get("api_key", "").strip()
        provider = data.get("provider", "nvidia").lower()
        
        if not api_key:
            return jsonify({"success": False, "error": "API Key passport required."}), 400
            
        # Temporary sandbox client to perform pre-flight token confirmation
        try:
            from openai import OpenAI
            base_url = "https://integrate.api.nvidia.com/v1" if provider == "nvidia" else "https://api.openai.com/v1"
            
            temp_client = OpenAI(base_url=base_url, api_key=api_key, timeout=8.0)
            # Trigger standard non-billing API list operation to verify credential state
            temp_client.models.list()
            
            return jsonify({
                "success": True, 
                "status": "validated", 
                "message": "Passport verified active. Form unlocked for profile registration."
            })
        except Exception as e:
            return jsonify({
                "success": False, 
                "error": f"Passport Validation Failed: {str(e)}"
            }), 401

    @app.route('/health', methods=['GET'])
    def srv_health():
        """Autonomous heartbeat monitoring node."""
        return jsonify({
            "status": "online", 
            "service": "Multi-Tenant Cloud Node", 
            "timestamp": int(time.time())
        })

    # --- USER ONBOARDING & PROFILE GATEWAY ---

    @app.route('/api/register', methods=['POST'])
    def register_user():
        """
        Registers validated passport user and provisions isolated filesystem workspace.
        Case 1 & Case 2 flows update profile details here.
        """
        data = request.get_json() or {}
        api_key = data.get("api_key", "").strip()
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        key_type = data.get("key_type", "byok").lower() # "byok" or "admin_funded"
        
        if not all([api_key, username, email, password]):
            return jsonify({"success": False, "error": "All fields are mandatory."}), 400
            
        if key_type not in ['byok', 'admin_funded']:
            return jsonify({"success": False, "error": "Invalid user key tier classification."}), 400

        # Attempt SQL persistence
        user_id, db_err = db.register_user(api_key, username, email, password, key_type)
        if db_err:
            return jsonify({"success": False, "error": db_err}), 400
            
        # Generate dynamic physical sandboxes isolating cross-contamination
        workspace = db.get_user_workspace(user_id)
        
        # Dispatch welcome security notification if active
        welcome_html = f"""
        <h2>Welcome to the Multi-Tenant Grid, {username}!</h2>
        <p>Your secured SaaS sandbox has been successfully provisioned.</p>
        <p><b>Key Type Tier:</b> {key_type.upper()}</p>
        """
        send_alert_email(email, "Workspace Provisoned - LLM Chat App", welcome_html)

        return jsonify({
            "success": True,
            "user_id": user_id,
            "key_type": key_type,
            "workspace_provisioned": True,
            "message": "Multi-tenant account successfully provisioned. You may now log in."
        }), 201

    @app.route('/api/login', methods=['POST'])
    def login_user():
        """Validates standard login credentials for web workstation entry."""
        data = request.get_json() or {}
        user_input = data.get("username_or_email", "").strip()
        password = data.get("password", "").strip()
        
        user = db.authenticate_by_login(user_input, password)
        if not user:
            return jsonify({"success": False, "error": "Invalid login credentials."}), 401
            
        return jsonify({
            "success": True,
            "user": user,
            "message": f"Authentication successful. Welcome back, {user['username']}."
        })

    @app.route('/api/update_profile', methods=['POST'])
    def update_profile():
        """Secure endpoint enabling authenticated tenants to rotate keys and profile metadata."""
        user = getattr(request, 'tenant', None)
        if not user:
            # Fallback manual check if routing intercepted prior to before_request resolution
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        data = request.get_json() or {}
        new_username = data.get("username", "").strip()
        new_password = data.get("password", "").strip()
        new_api_key = data.get("api_key", "").strip()
        
        if not any([new_username, new_password, new_api_key]):
            return jsonify({"success": False, "error": "No profile update parameters provided."}), 400
            
        success, message = db.update_user_profile(
            user_id=user['id'],
            username=new_username or None,
            password_raw=new_password or None,
            api_key=new_api_key or None
        )
        
        if not success:
            return jsonify({"success": False, "error": message}), 400
            
        # Retrieve the completely refreshed user record for downstream client caching
        target_key = new_api_key if new_api_key else user.get('api_key')
        refreshed = db.authenticate_by_passport(target_key)
        
        if not refreshed:
            return jsonify({"success": False, "error": "Synchronized validation handshake failed."}), 500
            
        refreshed['passport_token'] = refreshed.get('api_key', '')
        
        return jsonify({
            "success": True,
            "user": refreshed,
            "message": "Local sandbox security profile successfully updated!"
        })

    # --- SECURED MULTI-TENANT API RUNTIME GATEWAY ---

    @app.before_request
    def enforce_tenant_authorization():
        """
        Global passport gate middleware verifying API tokens and injected routing context.
        """
        # Exempt UI landing, static folders, health nodes, and onboarding endpoints
        exempt_starts = ['/static', '/health', '/api/validate_passport', '/api/register', '/api/login']
        if request.path == '/' or any(request.path.startswith(prefix) for prefix in exempt_starts):
            return None
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized. Missing API Passport token."}), 401
            
        passport_key = auth_header.replace("Bearer ", "").strip()
        user = db.authenticate_by_passport(passport_key)
        
        if not user:
            return jsonify({"error": "Forbidden. Invalid or revoked API Passport."}), 403
            
        # Embed context securely onto the request context thread for routing resolution
        request.tenant = user
        return None

    @app.route('/v1/models', methods=['GET'])
    def list_saas_models():
        """
        Exposes standard OpenAI compatibility model manifest to third-party SaaS clients.
        """
        try:
            from logic.model_io import load_all_models
            all_models = load_all_models()
            
            model_data = []
            for m in all_models:
                model_data.append({
                    "id": m.get("id"),
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": m.get("provider", "llm-chat-app")
                })
                
            # Global system safety fallback
            if not model_data:
                model_data.append({
                    "id": "meta/llama-3.1-8b-instruct",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "nvidia"
                })
                
            return jsonify({"data": model_data})
        except Exception as e:
            return jsonify({
                "data": [{
                    "id": "meta/llama-3.1-8b-instruct",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "nvidia"
                }]
            })

    # --- ADMIN / OPERATOR APIs ---
    
    @app.route('/api/admin/users', methods=['GET'])
    def admin_list_users():
        """Returns all tenants for the Operator Dashboard."""
        user = getattr(request, 'tenant', None)
        if not user or user.get('key_type') != 'admin_funded':
            return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        users = db.get_all_tenants()
        return jsonify({"success": True, "users": users})
        
    @app.route('/api/admin/stats', methods=['GET'])
    def admin_stats():
        """Returns aggregated telemetry for the Operator Dashboard."""
        user = getattr(request, 'tenant', None)
        if not user or user.get('key_type') != 'admin_funded':
            return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        stats = db.get_global_usage()
        return jsonify({"success": True, "stats": stats})

    # --- MEMORY EXPLORER APIs ---

    @app.route('/api/memory/list', methods=['GET'])
    def memory_list():
        """Scans the physical tenant sandbox for active RAG vector collections."""
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
            
        workspace = db.get_user_workspace(user['id'])
        v_path = workspace.get('vector_path')
        
        collections = []
        if v_path and v_path.exists():
            for item in v_path.iterdir():
                if item.is_dir():
                    collections.append({
                        "name": item.name,
                        "created": os.path.getctime(str(item))
                    })
                    
        return jsonify({"success": True, "collections": collections})

    # --- PUBLIC SHARING APIs ---

    @app.route('/api/share', methods=['POST'])
    def create_share():
        """Generates a secure hash for a conversation stream."""
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
            
        data = request.get_json() or {}
        conversation_data = data.get("messages")
        
        if not conversation_data:
            return jsonify({"error": "No message data provided."}), 400
            
        share_hash = db.create_share_link(user['id'], json.dumps(conversation_data))
        return jsonify({
            "success": True, 
            "share_url": f"/share/{share_hash}"
        })
        
    @app.route('/share/<share_hash>', methods=['GET'])
    def view_shared_orbit(share_hash):
        """Renders the static, read-only conversational log."""
        orbit = db.get_shared_orbit(share_hash)
        if not orbit:
            return "Shared Orbit not found or has been deleted.", 404
            
        # Parse the JSON string back to an object for the Jinja template
        try:
            orbit['messages'] = json.loads(orbit['conversation_data'])
        except Exception:
            orbit['messages'] = []
            
        return render_template('share.html', orbit=orbit)

    # --- MULTI-PROVIDER PROXY INTEGRATION WIRED TO ECONOMIC FEATURES ---

    @app.route('/v1/chat/completions', methods=['POST'])
    def proxy_chat_completion():
        """
        Secure gateway processing completions requests. Enforces structural hard-locks
        on Model Arena Mode for cost controls on Admin-Funded tiers.
        """
        user = request.tenant
        data = request.get_json() or {}
        
        # 🚀 SECURE FEATURE-GATE LOCK: (V7 economic quota controls)
        is_arena_request = data.get("arena_mode", False) or data.get("is_duel", False)
        
        if is_arena_request and user['key_type'] == 'admin_funded':
            # HARD-BLOCK to prevent admin balance over-consumption (50% savings)
            return jsonify({
                "error": "Forbidden. Parallel Model Arena is locked for Admin-Funded accounts.",
                "message": "Admin accounts are restricted to standard chat models to preserve compute balances."
            }), 403

        # Extract inference context
        user_msg = ""
        system_msg = ""
        messages = data.get("messages", [])
        for m in messages:
            if m.get("role") == "system": system_msg = m.get("content", "")
            elif m.get("role") == "user": user_msg = m.get("content", "")

        stream = data.get("stream", False)
        web_search_enabled = data.get("web_search", False)
        model_id = data.get("model", "meta/llama-3.1-8b-instruct")
        
        if web_search_enabled and user_msg:
            try:
                from logic.tool_manager import ToolManager
                search_res = ToolManager.execute_web_search(user_msg, limit=3)
                if search_res and "⚠️" not in search_res:
                    injection = f"\n\n[SYSTEM TOOL CONTEXT: The user requested a real-time web search. Results:\n{search_res}\nUse these results to formulate your answer.]"
                    system_msg += injection
                    
                    has_sys = False
                    for m in messages:
                        if m.get("role") == "system":
                            m["content"] = system_msg
                            has_sys = True
                    if not has_sys:
                        messages.insert(0, {"role": "system", "content": system_msg})
            except Exception as e:
                print(f"[Gateway] Web Search pre-processing failed: {e}")
        
        # Bind to User's Private Isolated Key stored securely in DB context
        api_passport = user['api_key']
        
        # Provision temporary isolated execution Client with dynamic provider detection
        llm_client = LLMClient()
        llm_client.set_model(model_id)
        provider = llm_client.get_current_provider()
        
        # Resolve the physical execution API Key with Host-Funded Overrides
        api_execution_key = api_passport
        if user.get('key_type') == 'admin_funded':
            try:
                from saas.config_manager import SaaSConfigManager
                cfg = SaaSConfigManager()
                # Attempt to extract dedicated operator-funded key from configuration
                funded_key = cfg.get_str("GLOBAL_KEYS", f"{provider}_api_key", "").strip()
                if funded_key:
                    api_execution_key = funded_key
            except Exception as cred_ex:
                print(f"[Credentials Warning]: Failed to extract host-funded keys: {cred_ex}")
        
        if provider == "google":
            llm_client.set_google_api_key(api_execution_key)
        else:
            # Resolve the correct base URL dynamically based on detected provider slug
            base_url = get_provider_base_url(provider)
            llm_client.set_base_url(base_url)
            llm_client.set_api_key(api_execution_key)

        # Record telemetry counters (simulated for now, fully aggregated in production)
        prompt_chars = sum(len(m.get("content", "")) for m in messages)
        approx_prompt_tokens = int(prompt_chars / 4)

        try:
            if stream:
                def generate_stream():
                    response_text = ""
                    # Standard completions pipeline proxy
                    if provider == "google":
                        from google.genai import types
                        chunks = llm_client.google_client.models.generate_content_stream(
                            model=llm_client.current_model,
                            contents=[m.get("content") for m in messages if m.get("role") != "system"],
                            config=types.GenerateContentConfig(system_instruction=system_msg or None)
                        )
                        for chk in chunks:
                            if chk.text:
                                response_text += chk.text
                                yield f"data: {json.dumps({'choices': [{'delta': {'content': chk.text}}]})}\n\n"
                    else:
                        stream_resp = llm_client.client.chat.completions.create(
                            model=llm_client.current_model,
                            messages=messages,
                            stream=True
                        )
                        for chunk in stream_resp:
                            if chunk.choices and chunk.choices[0].delta.content:
                                text = chunk.choices[0].delta.content
                                response_text += text
                                yield f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}\n\n"
                                
                    # Post-stream tally execution
                    approx_comp_tokens = int(len(response_text) / 4)
                    db.record_usage(user['id'], approx_prompt_tokens, approx_comp_tokens)
                    yield "data: [DONE]\n\n"

                return Response(stream_with_context(generate_stream()), mimetype="text/event-stream")
                
            else:
                # Standard blocking completions proxy
                if provider == "google":
                    from google.genai import types
                    resp = llm_client.google_client.models.generate_content(
                        model=llm_client.current_model,
                        contents=[m.get("content") for m in messages if m.get("role") != "system"],
                        config=types.GenerateContentConfig(system_instruction=system_msg or None)
                    )
                    text = resp.text
                else:
                    resp = llm_client.client.chat.completions.create(
                        model=llm_client.current_model,
                        messages=messages
                    )
                    text = resp.choices[0].message.content
                
                # Ledger commit
                approx_comp_tokens = int(len(text) / 4)
                db.record_usage(user['id'], approx_prompt_tokens, approx_comp_tokens)
                
                return jsonify({
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model_id,
                    "choices": [{"message": {"role": "assistant", "content": text}}],
                    "usage": {
                        "prompt_tokens": approx_prompt_tokens,
                        "completion_tokens": approx_comp_tokens,
                        "total_tokens": approx_prompt_tokens + approx_comp_tokens
                    }
                })

        except Exception as e:
            return jsonify({"error": "Generation Engine Exception", "message": str(e)}), 500

    @app.route('/', methods=['GET'])
    def srv_index():
        """Main browser portal entry rendering the Single Page Workspace canvas."""
        return render_template('index.html')

    return app

class SaaSServer:
    """
    Autonomous multi-threaded executor hosting the SaaS Flask application context
    inside background system threads for seamless desktop-shell execution.
    """
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        self.app = create_saas_app()
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False

    def start(self):
        """Locks onto target socket and launches Werkzeug listener thread."""
        if self.running:
            return True, "Already active"
            
        import socket
        import sys
        from threading import Thread
        
        # Standardize address interface mapping
        bind_address = '127.0.0.1' if self.host == 'localhost' else self.host
        
        # Pre-flight port binding reservation test
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((bind_address, self.port))
            except OSError:
                msg = f"Port {self.port} is currently tied by another service."
                return False, msg
                
        try:
            from werkzeug.serving import make_server
            self.server = make_server(bind_address, self.port, self.app, threaded=True)
            
            def run():
                print(f"[SaaS Daemon] Background server established at http://{self.host}:{self.port}")
                self.server.serve_forever()
                
            self.server_thread = Thread(target=run, daemon=True)
            self.server_thread.start()
            self.running = True
            return True, "Success"
        except Exception as e:
            return False, f"Runtime Fault: {str(e)}"

    def stop(self):
        """Triggers non-destructive shutdown loop."""
        if self.server:
            print("[SaaS Daemon] Commencing soft shutdown sequence...")
            self.server.shutdown()
            self.server = None
        self.running = False
        return True
