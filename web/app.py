import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# saas/app.py
"""
Unified SaaS Multi-Tenant Flask Application Engine (Phase 6)
Orchestrates JWT/Passport gateway auth, dynamic workspace routing, 
economic feature locks on Model Arena, and autonomous SMTP alerts.
"""

from server.logic.model_io import load_provider_metadata
from server.utils import get_resource_path
import os
import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, Response, stream_with_context, render_template, send_from_directory

from web.core.tenant_db import TenantDatabaseManager
from server.logic.llm_client import LLMClient
from server.utils.storage_config import StorageManager

def create_saas_app():
    """
    Core Factory initializing the unified, multi-tenant API routing ecosystem.
    """
    from server.utils.logger import AppLogger
    logger = AppLogger.get_instance("web")
    logger.info("Initializing SaaS Web Portal...")
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
            msg["From"] = f"Synora Studio Security <{smtp_user}>"
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
            from server.utils.path_utils import get_resource_path
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
    @app.route('/v1/validate_passport', methods=['POST'])
    @app.route('/v2/validate_passport', methods=['POST'])
    def validate_passport():
        """
        Pre-flight validation handshake performing real-time live check 
        against NVIDIA/OpenAI endpoints prior to allowing profile creation.
        """
        data = request.get_json(silent=True) or {}
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
    @app.route('/v1/health', methods=['GET'])
    @app.route('/v2/health', methods=['GET'])
    def srv_health():
        """Autonomous heartbeat monitoring node."""
        return jsonify({
            "status": "online", 
            "service": "Multi-Tenant Cloud Node", 
            "timestamp": int(time.time())
        })

    @app.route('/api/admin/system_prompts', methods=['GET', 'POST'])
    @app.route('/v1/admin/system_prompts', methods=['GET', 'POST'])
    @app.route('/v2/admin/system_prompts', methods=['GET', 'POST'])
    def sync_admin_prompts():
        """Real-time mirroring of System Prompts between Admin SaaS and Desktop Global Store."""
        from server.utils.path_utils import get_resource_path
        import json
        prompts_file = get_resource_path("resources/user_prompts.json")
        
        if request.method == 'GET':
            try:
                if os.path.exists(prompts_file):
                    with open(prompts_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return jsonify({"success": True, "data": data})
                else:
                    return jsonify({"success": True, "data": []})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
                
        if request.method == 'POST':
            try:
                payload = request.get_json(silent=True) or []
                with open(prompts_file, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=4)
                return jsonify({"success": True, "message": "Synced to Desktop Globally"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/user/settings', methods=['GET', 'POST'])
    @app.route('/v1/user/settings', methods=['GET', 'POST'])
    @app.route('/v2/user/settings', methods=['GET', 'POST'])
    def user_settings():
        """Secure endpoints for regular SaaS tenants to persist UI configuration blobs."""
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        if request.method == 'GET':
            settings = db.get_user_settings(user['id'])
            return jsonify({"success": True, "data": settings})
            
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            success = db.update_user_settings(user['id'], payload)
            if success:
                return jsonify({"success": True, "message": "Settings updated"})
            return jsonify({"success": False, "error": "Failed to update settings"}), 500

    # --- HERMES AGENT ROUTES ---
    @app.route('/api/agent/status', methods=['GET'])
    @app.route('/v1/agent/status', methods=['GET'])
    def agent_status():
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        from web.core.agent_manager import AgentManager
        mgr = AgentManager.get_instance()
        status = mgr.get_status(user['id'])
        return jsonify({"success": True, "status": status})

    @app.route('/api/agent/start', methods=['POST'])
    @app.route('/v1/agent/start', methods=['POST'])
    def agent_start():
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        from web.core.agent_manager import AgentManager
        mgr = AgentManager.get_instance()
        # Ensure agent requests route back through this SaaS Universal API via environment variable injection
        gateway_url = f"http://localhost:{os.getenv('PORT', 5000)}/v1"
        success = mgr.start_agent(user['id'], user['api_key'], gateway_url)
        if success:
            db.update_agent_instance(user['id'], "Hermes", "running")
            return jsonify({"success": True, "status": "RUNNING"})
        return jsonify({"success": False, "error": "Failed to start agent"}), 500

    @app.route('/api/agent/stop', methods=['POST'])
    @app.route('/v1/agent/stop', methods=['POST'])
    def agent_stop():
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        from web.core.agent_manager import AgentManager
        mgr = AgentManager.get_instance()
        success = mgr.stop_agent(user['id'])
        if success:
            db.update_agent_instance(user['id'], "Hermes", "stopped")
            return jsonify({"success": True, "status": "STOPPED"})
        return jsonify({"success": False, "error": "Failed to stop agent"}), 500
    @app.route('/api/agent/skills', methods=['GET'])
    @app.route('/v1/agent/skills', methods=['GET'])
    def agent_skills_list():
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        skills = db.get_agent_skills(user['id'])
        # Convert sqlite3.Row objects to dicts for JSON serialization
        skills_list = [dict(row) for row in skills]
        return jsonify({"success": True, "skills": skills_list})

    @app.route('/api/agent/skills/add', methods=['POST'])
    @app.route('/v1/agent/skills/add', methods=['POST'])
    def agent_skills_add():
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        data = request.get_json() or {}
        skill_name = data.get("skill_name", "").strip()
        skill_code = data.get("skill_code", "").strip()
        
        if not skill_name or not skill_code:
            return jsonify({"success": False, "error": "Missing skill name or code"}), 400
            
        try:
            db.add_agent_skill(user['id'], skill_name, skill_code)
            return jsonify({"success": True, "message": "Skill added successfully"})
        except Exception as e:
            logger.error(f"Failed to add skill: {e}")
            return jsonify({"success": False, "error": "Database error adding skill"}), 500

    @app.route('/api/admin/gen_params', methods=['GET', 'POST'])
    @app.route('/v1/admin/gen_params', methods=['GET', 'POST'])
    @app.route('/v2/admin/gen_params', methods=['GET', 'POST'])
    def admin_gen_params():
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin parameters access denied", "FAILED")
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin parameters access granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            
        config_file = get_resource_path("resources/config.json")

        if request.method == 'GET':
            try:
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return jsonify({"success": True, "data": data})
                return jsonify({"success": True, "data": {}})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
                
        if request.method == 'POST':
            try:
                payload = request.get_json(silent=True) or {}
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        current = json.load(f)
                else:
                    current = {}
                current.update(payload)
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(current, f, indent=4)
                return jsonify({"success": True, "message": "Synced to Desktop Globally"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/admin/local_api', methods=['GET', 'POST'])
    @app.route('/v1/admin/local_api', methods=['GET', 'POST'])
    @app.route('/v2/admin/local_api', methods=['GET', 'POST'])
    def admin_local_api():
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin local API access denied", "FAILED")
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin local API access granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            
        from server.utils.path_utils import get_app_settings
        settings = get_app_settings()
        
        if request.method == 'GET':
            enabled = str(settings.value("api_enabled", "true")).lower() == "true"
            key = settings.value("local_api_auth_key", "")
            return jsonify({"success": True, "enabled": enabled, "key": key})
            
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            action = payload.get("action")
            
            if action == "toggle":
                current_enabled = str(settings.value("api_enabled", "true")).lower() == "true"
                new_enabled = not current_enabled
                settings.setValue("api_enabled", "true" if new_enabled else "false")
                
                instance = getattr(app, "saas_server_instance", None)
                if instance:
                    instance.api_manager_action.emit("restart" if new_enabled else "stop")
                return jsonify({"success": True, "enabled": new_enabled})
                
            elif action == "regen":
                import uuid
                new_key = f"llm-local-auth-{uuid.uuid4().hex[:10]}"
                settings.setValue("local_api_auth_key", new_key)
                
                instance = getattr(app, "saas_server_instance", None)
                if instance:
                    instance.api_manager_action.emit("restart")
                return jsonify({"success": True, "key": new_key})
                
            return jsonify({"success": False, "error": "Unknown action"}), 400

    @app.route('/api/admin/saas_config', methods=['GET', 'POST'])
    @app.route('/v1/admin/saas_config', methods=['GET', 'POST'])
    @app.route('/v2/admin/saas_config', methods=['GET', 'POST'])
    def admin_saas_config():
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin SaaS config access denied", "FAILED")
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin SaaS config access granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            
        try:
            from web.core.config_manager import SaaSConfigManager
            saas_cfg = SaaSConfigManager()
            
            if request.method == 'GET':
                data = {
                    "smtp_enabled": saas_cfg.get_bool("SMTP_RELAY", "enabled", False),
                    "smtp_host": saas_cfg.get_str("SMTP_RELAY", "host", "smtp.gmail.com"),
                    "smtp_port": saas_cfg.get_int("SMTP_RELAY", "port", 587),
                    "smtp_user": saas_cfg.get_str("SMTP_RELAY", "user", ""),
                    "smtp_password": saas_cfg.get_str("SMTP_RELAY", "password", "")
                }
                return jsonify({"success": True, "data": data})
                
            if request.method == 'POST':
                payload = request.get_json(silent=True) or {}
                if "smtp_enabled" in payload: saas_cfg.set_val("SMTP_RELAY", "enabled", payload["smtp_enabled"])
                if "smtp_host" in payload: saas_cfg.set_val("SMTP_RELAY", "host", payload["smtp_host"])
                if "smtp_port" in payload: saas_cfg.set_val("SMTP_RELAY", "port", int(payload["smtp_port"]))
                if "smtp_user" in payload: saas_cfg.set_val("SMTP_RELAY", "user", payload["smtp_user"])
                if "smtp_password" in payload: saas_cfg.set_val("SMTP_RELAY", "password", payload["smtp_password"])
                saas_cfg.save()
                return jsonify({"success": True, "message": "SaaS Config Synced"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/admin/models', methods=['POST'])
    @app.route('/v1/admin/models', methods=['POST'])
    @app.route('/v2/admin/models', methods=['POST'])
    def admin_models():
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin models access denied", "FAILED")
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin models access granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"success": False, "error": "Unauthorized action scope."}), 403
            
        try:
            from server.logic.model_io import load_all_models, save_models
            data = request.get_json(silent=True) or {}
            if not data.get("id"):
                return jsonify({"success": False, "error": "Model ID is required."}), 400
                
            models = load_all_models()
            existing_idx = next((i for i, m in enumerate(models) if m.get("id") == data["id"]), None)
            
            if existing_idx is not None:
                models[existing_idx].update(data)
            else:
                models.append(data)
                
            save_models(models)
            return jsonify({"success": True, "message": "Model synced to Desktop."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500


    # --- USER ONBOARDING & PROFILE GATEWAY ---

    @app.route('/api/register', methods=['POST'])
    @app.route('/v1/register', methods=['POST'])
    @app.route('/v2/register', methods=['POST'])
    def register_user():
        """
        Registers validated passport user and provisions isolated filesystem workspace.
        Case 1 & Case 2 flows update profile details here.
        """
        data = request.get_json(silent=True) or {}
        api_key = data.get("api_key", "").strip()
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        # Hard-lock key_type to 'byok' for public registration (Fix Issue 72)
        key_type = "byok"
        
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
        send_alert_email(email, "Workspace Provisoned - Synora Studio", welcome_html)

        try:
            from server.logic.services import ServiceRegistry
            auth_service = ServiceRegistry.get("auth")
            user_data = {"id": user_id, "username": username, "email": email, "key_type": key_type}
            jwt_token = auth_service.generate_token(user_data)
        except Exception:
            jwt_token = api_key

        return jsonify({
            "success": True,
            "user_id": user_id,
            "key_type": key_type,
            "workspace_provisioned": True,
            "token": jwt_token,
            "passport_token": jwt_token,
            "message": "Multi-tenant account successfully provisioned. You may now log in."
        }), 201

    @app.route('/api/login', methods=['POST'])
    @app.route('/v1/login', methods=['POST'])
    @app.route('/v2/login', methods=['POST'])
    def login_user():
        """Validates standard login credentials for web workstation entry."""
        data = request.get_json(silent=True) or {}
        user_input = data.get("username_or_email", "").strip()
        password = data.get("password", "").strip()
        
        user = db.authenticate_by_login(user_input, password)
        if not user:
            return jsonify({"success": False, "error": "Invalid login credentials."}), 401
            
        try:
            from server.logic.services import ServiceRegistry
            auth_service = ServiceRegistry.get("auth")
            jwt_token = auth_service.generate_token(user)
            user['passport_token'] = jwt_token
            user['token'] = jwt_token
        except Exception as e:
            print(f"[JWT Error] Failed to generate token: {e}")
            
        return jsonify({
            "success": True,
            "user": user,
            "message": f"Authentication successful. Welcome back, {user['username']}."
        })

    @app.route('/api/update_profile', methods=['POST'])
    @app.route('/v1/update_profile', methods=['POST'])
    @app.route('/v2/update_profile', methods=['POST'])
    def update_profile():
        """Secure endpoint enabling authenticated tenants to rotate keys and profile metadata."""
        user = getattr(request, 'tenant', None)
        if not user:
            # Fallback manual check if routing intercepted prior to before_request resolution
            return jsonify({"success": False, "error": "Unauthorized action scope."}), 401
            
        data = request.get_json(silent=True) or {}
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
            
        try:
            from server.logic.services import ServiceRegistry
            auth_service = ServiceRegistry.get("auth")
            jwt_token = auth_service.generate_token(refreshed)
            refreshed['passport_token'] = jwt_token
            refreshed['token'] = jwt_token
        except Exception:
            refreshed['passport_token'] = refreshed.get('api_key', '')
        
        return jsonify({
            "success": True,
            "user": refreshed,
            "message": "Local sandbox security profile successfully updated!"
        })

    # --- SECURED MULTI-TENANT API RUNTIME GATEWAY ---

    @app.before_request
    def record_start_time():
        request.start_time = time.perf_counter()

    @app.after_request
    def log_telemetry_metrics(response):
        exempt_starts = ['/static', '/health', '/app_icon.ico']
        if any(request.path.startswith(prefix) for prefix in exempt_starts):
            return response
            
        start_time = getattr(request, 'start_time', None)
        if start_time:
            latency = time.perf_counter() - start_time
            user = getattr(request, 'tenant', None)
            tenant_id = user['id'] if user else "anonymous"
            
            tokens = 0
            if request.path == '/v1/chat/completions' and response.status_code == 200:
                try:
                    data = request.get_json(silent=True) or {}
                    messages = data.get("messages", [])
                    prompt_chars = sum(len(m.get("content", "")) for m in messages)
                    tokens = int(prompt_chars / 4)
                except:
                    pass
            
            error = (response.status_code >= 400)
            
            try:
                from server.logic.services import ServiceRegistry
                telemetry_service = ServiceRegistry.get("telemetry")
                telemetry_service.record_request(
                    tenant_id=str(tenant_id),
                    latency=latency,
                    tokens=tokens,
                    error=error
                )
            except:
                pass
                
        return response

    @app.before_request
    def enforce_tenant_authorization():
        """
        Global passport gate middleware verifying API tokens and injected routing context.
        """
        # Exempt UI landing, static folders, health nodes, and onboarding endpoints
        exempt_starts = ['/static', '/health', '/api/validate_passport', '/api/register', '/api/login', '/app_icon.ico']
        exempt_starts += ['/v1/health', '/v2/health', '/v1/validate_passport', '/v2/validate_passport', 
                         '/v1/register', '/v2/register', '/v1/login', '/v2/login']
                         
        if request.path == '/' or any(request.path.startswith(prefix) for prefix in exempt_starts):
            return None
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized. Missing API Passport token."}), 401
            
        passport_key = auth_header.replace("Bearer ", "").strip()
        
        # A. Try to verify JWT first
        user = None
        try:
            from server.logic.services import ServiceRegistry
            auth_service = ServiceRegistry.get("auth")
            payload = auth_service.verify_token(passport_key)
            if payload:
                user = {
                    "id": payload["id"],
                    "username": payload["username"],
                    "email": payload["email"],
                    "key_type": payload["key_type"],
                    "api_key": passport_key,
                    "status": "active"
                }
        except Exception:
            user = None

        # B. Fallback to passport API key lookup
        if not user:
            user = db.authenticate_by_passport(passport_key)
        
        if not user:
            return jsonify({"error": "Forbidden. Invalid or revoked API Passport."}), 403
            
        # Embed context securely onto the request context thread for routing resolution
        request.tenant = user

        # C. Enforce Redis-backed rate-limiting via Token Bucket
        try:
            from server.logic.services import ServiceRegistry
            rate_limiter = ServiceRegistry.get("rate_limiter")
            
            # Global IP-based rate limiting (120 requests per minute)
            ip = request.remote_addr or "unknown_ip"
            if not rate_limiter.is_allowed(f"ip:{ip}", limit=120):
                try:
                    telemetry_service = ServiceRegistry.get("telemetry")
                    if telemetry_service:
                        telemetry_service.record_rate_limit_block()
                except Exception:
                    pass
                return jsonify({"error": "Too Many Requests", "message": "Global IP rate limit exceeded."}), 429

            # Tenant-based rate limiting
            settings = db.get_user_settings(user['id'])
            rpm_limit = int(settings.get("requests_per_minute_limit", 60 if user['username'] != 'admin' else 0))
            if rpm_limit > 0:
                if not rate_limiter.is_allowed(f"tenant:{user['id']}", limit=rpm_limit):
                    try:
                        telemetry_service = ServiceRegistry.get("telemetry")
                        if telemetry_service:
                            telemetry_service.record_rate_limit_block()
                    except Exception:
                        pass
                    return jsonify({"error": "Too Many Requests", "message": f"Tenant rate limit of {rpm_limit} RPM exceeded."}), 429
        except Exception as e:
            print(f"[RateLimiter Warning] Throttling check failed: {e}")

        return None


    @app.route('/v1/tenant/credentials', methods=['GET', 'POST'])
    @app.route('/v2/tenant/credentials', methods=['GET', 'POST'])
    def manage_credentials():
        """Retrieve masked keys or save new API keys for the current tenant."""
        is_admin = request.tenant['username'] == 'admin'
        
        if request.method == 'GET':
            if is_admin:
                import keyring
                import json
                from server.utils.path_utils import get_app_settings
                from server.logic.model_io import load_provider_metadata
                
                creds = {}
                try:
                    metadata = load_provider_metadata()
                    for p in metadata.get("providers", []):
                        pid = p.get("id")
                        if not pid: continue
                        creds[pid] = keyring.get_password("LLMChatApp", f"api_key_{pid}") or ""
                        creds[f"{pid}_base_url"] = keyring.get_password("LLMChatApp", f"url_{pid}") or ""
                        
                    custom = json.loads(get_app_settings().value("custom_providers", "[]"))
                    for c in custom:
                        eco_key = c['ecosystem'].lower().replace(' ', '_')
                        cid = f"{c['sdk']}_{eco_key}"
                        creds[cid] = keyring.get_password("LLMChatApp", f"api_key_{cid}") or ""
                        creds[f"{cid}_base_url"] = keyring.get_password("LLMChatApp", f"url_{cid}") or ""
                except:
                    pass
                    
                if not creds.get('nvidia'):
                    creds['nvidia'] = keyring.get_password("LLMChatApp", "api_key") or ""
            else:
                creds = db.get_tenant_credentials(request.tenant['id'])
                
            masked = {}
            for prov, key in creds.items():
                if not key:
                    continue
                if prov.endswith('_base_url'):
                    masked[prov] = key # don't mask URLs
                elif len(key) > 8:
                    masked[prov] = key[:4] + "...." + key[-4:]
                else:
                    masked[prov] = "********"
            return jsonify(masked)
        
        elif request.method == 'POST':
            data = request.json
            if not isinstance(data, dict):
                return jsonify({"error": "Invalid format"}), 400
                
            if is_admin:
                import keyring
                for prov, key in data.items():
                    if prov.endswith('_base_url'):
                        k_name = f"url_{prov.replace('_base_url', '')}"
                    else:
                        k_name = f"api_key_{prov}"
                    
                    if key.strip():
                        keyring.set_password("LLMChatApp", k_name, key.strip())
                    else:
                        try: keyring.delete_password("LLMChatApp", k_name)
                        except: pass
            else:
                for prov, key in data.items():
                    db.set_tenant_credential(request.tenant['id'], prov.lower(), key.strip())
            return jsonify({"status": "success", "message": "Credentials synchronized."})

    @app.route('/v1/system/providers', methods=['GET', 'POST'])
    @app.route('/v2/system/providers', methods=['GET', 'POST'])
    def list_system_providers():
        """Returns the dynamic list of base providers + custom providers, and allows Admin to add new ones."""
        try:
            from server.logic.model_io import load_provider_metadata
            from server.utils.path_utils import get_app_settings
            import json
            
            if request.method == 'POST':
                user = getattr(request, 'tenant', None)
                try:
                    from server.logic.services import ServiceRegistry
                    security_svc = ServiceRegistry.get("security")
                    if not security_svc.check_permission(user, "admin"):
                        security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Add system provider access denied", "FAILED")
                        return jsonify({"error": "Forbidden. Operator access only."}), 403
                    security_svc.log_audit(user.get('id'), request.path, "Add system provider access granted", "SUCCESS")
                except Exception:
                    if not user or user.get('key_type') != 'admin_funded':
                        return jsonify({"error": "Forbidden. Operator access only."}), 403
                    
                data = request.get_json(silent=True)
                if not data or 'sdk' not in data or 'ecosystem' not in data or 'url' not in data:
                    return jsonify({"error": "Missing required fields."}), 400
                    
                settings = get_app_settings()
                custom_raw = settings.value("custom_providers", "[]")
                try:
                    custom_providers = json.loads(custom_raw)
                except:
                    custom_providers = []
                    
                custom_providers.append({
                    "sdk": data["sdk"],
                    "ecosystem": data["ecosystem"],
                    "url": data["url"]
                })
                settings.setValue("custom_providers", json.dumps(custom_providers))
                return jsonify({"success": True})
            
            metadata = load_provider_metadata()
            raw_providers = metadata.get("providers", [])
            
            base_providers = []
            for p in raw_providers:
                base_providers.append({
                    "id": p.get("id"),
                    "sdk": p.get("sdk", "openai"),
                    "ecosystem": p.get("display_name", p.get("id")),
                    "default_url": p.get("default_url", "")
                })
                
            settings = get_app_settings()
            custom_raw = settings.value("custom_providers", "[]")
            try:
                custom_providers = json.loads(custom_raw)
            except:
                custom_providers = []
                
            formatted_custom = []
            for c in custom_providers:
                eco_key = c['ecosystem'].lower().replace(' ', '_')
                formatted_custom.append({
                    "id": f"{c['sdk']}_{eco_key}", 
                    "sdk": c['sdk'],
                    "ecosystem": c['ecosystem'],
                    "default_url": c['url']
                })
                
            return jsonify({"base": base_providers, "custom": formatted_custom})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route('/v1/models', methods=['GET'])
    @app.route('/v2/models', methods=['GET'])
    def list_saas_models():
        """
        Exposes standard OpenAI compatibility model manifest to third-party SaaS clients.
        """
        try:
            from server.logic.model_io import load_all_models
            from server.utils.model_config import does_model_support_tools
            all_models = load_all_models()
            
            is_admin = request.tenant['username'] == 'admin' if hasattr(request, 'tenant') else False
            tenant_creds = db.get_tenant_credentials(request.tenant['id']) if hasattr(request, 'tenant') and not is_admin else {}
            
            import keyring
            model_data = []
            for m in all_models:
                prov = m.get('provider', 'nvidia').lower()
                
                has_key = False
                if is_admin:
                    metadata = load_provider_metadata()
                    base_providers = {p.get("id"): p for p in metadata.get("providers", [])}
                    
                    def normalize(p):
                        return str(p).lower().replace(" ", "").replace("_", "").replace("-", "")
 
                    p_id = normalize(prov)
                    mapped_id = p_id
                    for base_id, base_p in base_providers.items():
                        if normalize(base_p.get("display_name", "")) == p_id or normalize(base_id) == p_id:
                            mapped_id = base_id
                            break
                            
                    if mapped_id in base_providers:
                        if keyring.get_password("LLMChatApp", f"api_key_{mapped_id}"):
                            has_key = True
                        elif mapped_id == "nvidia" and keyring.get_password("LLMChatApp", "api_key"):
                            has_key = True
                    
                    if not has_key:
                        from server.utils.path_utils import get_app_settings
                        import json
                        custom = json.loads(get_app_settings().value("custom_providers", "[]"))
                        for cp in custom:
                            if normalize(cp['ecosystem']) == p_id:
                                eco_key = cp['ecosystem'].lower().replace(' ', '_')
                                if keyring.get_password("LLMChatApp", f"api_key_{cp['sdk']}_{eco_key}"):
                                    has_key = True
                                    break
                else:
                    has_key = prov in tenant_creds and bool(tenant_creds[prov])
                    
                if prov in ['local', 'ollama', 'lmstudio']:
                    has_key = True
                    
                if has_key:
                    m_id = m.get("id", "")
                    m_desc = m.get("description", "").lower()
                    is_vision = "vision" in m_id.lower() or "-vl" in m_id.lower() or "vision" in m_desc or "multimodal" in m_desc
                    
                    model_data.append({
                        "id": m_id,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": m.get("provider", "llm-chat-app"),
                        "name": m.get("name", m_id),
                        "description": m.get("description", ""),
                        "free": m.get("free", True),
                        "developer": m.get("developer", ""),
                        "capabilities": {
                            "chat": m.get('type', 'chat') == 'chat',
                            "tools": does_model_support_tools(m_id),
                            "vision": is_vision
                        }
                    })
                
            return jsonify({"data": model_data})
        except Exception as e:
            return jsonify({"data": []})

    # --- ADMIN / OPERATOR APIs ---
    
    @app.route('/api/admin/users', methods=['GET'])
    @app.route('/v1/admin/users', methods=['GET'])
    @app.route('/v2/admin/users', methods=['GET'])
    def admin_list_users():
        """Returns all tenants for the Operator Dashboard."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin list users denied", "FAILED")
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin list users granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        users = db.get_all_tenants()
        for u in users:
            settings = db.get_user_settings(u['id'])
            u['requests_per_minute_limit'] = settings.get('requests_per_minute_limit', 60 if u['username'] != 'admin' else 0)
        return jsonify({"success": True, "users": users})
        
    @app.route('/api/admin/stats', methods=['GET'])
    @app.route('/v1/admin/stats', methods=['GET'])
    @app.route('/v2/admin/stats', methods=['GET'])
    def admin_stats():
        """Returns aggregated telemetry for the Operator Dashboard."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin stats access denied", "FAILED")
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin stats access granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        stats = db.get_global_usage()
        return jsonify({"success": True, "stats": stats})

    @app.route('/api/admin/telemetry', methods=['GET'])
    @app.route('/v1/admin/telemetry', methods=['GET'])
    @app.route('/v2/admin/telemetry', methods=['GET'])
    def admin_telemetry():
        """Exposes dynamic central telemetry metrics to Screen D and System Health Dialog."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin telemetry access denied", "FAILED")
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin telemetry access granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        try:
            from server.logic.services import ServiceRegistry
            from server.logic.queue.job_queue import JobQueueEngine
            
            telemetry_service = ServiceRegistry.get("telemetry")
            metrics = telemetry_service.get_realtime_metrics()
            
            # 1. Inject LED health check statuses
            metrics["health"] = telemetry_service.run_health_checks()
            
            # 2. Inject circuit breaker state
            circuit_breaker = ServiceRegistry.get("circuit_breaker")
            metrics["circuit_breaker_state"] = circuit_breaker.state if circuit_breaker else "CLOSED"
            
            # 3. Inject active worker jobs
            try:
                queue_engine = JobQueueEngine()
                status = queue_engine.get_queue_status()
                active_list = status.get("processing_jobs", []) + status.get("queued_jobs", [])
                
                serialized_jobs = []
                for row, job in enumerate(active_list):
                    serialized_jobs.append({
                        "name": f"WorkerThread-{row+1}",
                        "job_id": str(job.get("job_id", "")),
                        "task_type": f"Ingest: {job.get('task_type', '')}",
                        "status": str(job.get("status", "")).upper()
                    })
                metrics["active_jobs"] = serialized_jobs
            except Exception as q_ex:
                metrics["active_jobs"] = []
                print(f"[Telemetry API] Error gathering queue status: {q_ex}")
                
            return jsonify({"success": True, "metrics": metrics})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/admin/tenants/<int:tenant_id>/rate-limit', methods=['POST'])
    @app.route('/v1/admin/tenants/<int:tenant_id>/rate-limit', methods=['POST'])
    @app.route('/v2/admin/tenants/<int:tenant_id>/rate-limit', methods=['POST'])
    def admin_set_tenant_rate_limit(tenant_id):
        """Updates specific tenant requests_per_minute_limit config bounds."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin set tenant rate limit denied", "FAILED")
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin set tenant rate limit granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        payload = request.get_json(silent=True) or {}
        rpm = payload.get("requests_per_minute_limit")
        if rpm is None:
            return jsonify({"error": "Missing requests_per_minute_limit"}), 400
            
        try:
            rpm = int(rpm)
            if rpm < 0:
                return jsonify({"error": "Rate limit must be non-negative"}), 400
        except ValueError:
            return jsonify({"error": "Invalid rate limit value"}), 400
            
        try:
            from server.logic.services import ServiceRegistry
            auth_service = ServiceRegistry.get("auth")
            current_settings = auth_service.get_user_settings(tenant_id)
            current_settings["requests_per_minute_limit"] = rpm
            auth_service.update_user_settings(tenant_id, current_settings)
            return jsonify({"success": True, "message": f"Tenant rate limit updated to {rpm} RPM"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/admin/dlq', methods=['GET'])
    @app.route('/v1/admin/dlq', methods=['GET'])
    @app.route('/v2/admin/dlq', methods=['GET'])
    def admin_get_dlq():
        """List failed background tasks for Operator DLQ review."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin get DLQ access denied", "FAILED")
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin get DLQ access granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        try:
            from server.logic.queue.job_queue import JobQueueEngine
            queue_engine = JobQueueEngine()
            entries = queue_engine.get_dlq_entries()
            return jsonify({"success": True, "dlq": entries})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/admin/dlq/retry', methods=['POST'])
    @app.route('/v1/admin/dlq/retry', methods=['POST'])
    @app.route('/v2/admin/dlq/retry', methods=['POST'])
    def admin_retry_dlq_job():
        """Retry a failed background task."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin retry DLQ job denied", "FAILED")
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin retry DLQ job granted", "SUCCESS")
        except Exception:
            if not user or user.get('key_type') != 'admin_funded':
                return jsonify({"error": "Forbidden. Operator access only."}), 403
            
        payload = request.get_json(silent=True) or {}
        job_id = payload.get("job_id")
        if not job_id:
            return jsonify({"error": "Missing job_id"}), 400
            
        try:
            from server.logic.queue.job_queue import JobQueueEngine
            queue_engine = JobQueueEngine()
            new_job_id = queue_engine.retry_dlq_job(job_id)
            return jsonify({"success": True, "new_job_id": new_job_id, "message": f"Job successfully enqueued as {new_job_id}."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500


    # --- USER SETTINGS APIs ---

    @app.route('/api/tenant/settings', methods=['GET', 'POST'])
    def manage_tenant_settings():
        """Retrieve or update tenant-specific configuration blobs."""
        user = getattr(request, 'tenant', None)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
            
        try:
            from server.logic.services import ServiceRegistry
            auth_service = ServiceRegistry.get("auth")
            
            if request.method == 'GET':
                settings = auth_service.get_user_settings(user['id'])
                return jsonify({"success": True, "settings": settings})
                
            if request.method == 'POST':
                new_settings = request.get_json(silent=True) or {}
                current_settings = auth_service.get_user_settings(user['id'])
                if "failover_provider_sequence" in new_settings:
                    current_settings["failover_provider_sequence"] = new_settings["failover_provider_sequence"]
                    
                auth_service.update_user_settings(user['id'], current_settings)
                return jsonify({"success": True, "settings": current_settings})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

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
            
        data = request.get_json(silent=True) or {}
        conversation_data = data.get("messages")
        
        if not conversation_data:
            return jsonify({"error": "No message data provided."}), 400
            
        share_hash = db.create_share_link(user['id'], json.dumps(conversation_data))
        return jsonify({
            "success": True, 
            "share_url": f"/share/{share_hash}"
        })
        
    @app.route('/app_icon.ico')
    def app_icon():
        from flask import send_file
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'app_icon.ico'))
        if os.path.exists(icon_path):
            return send_file(icon_path, mimetype='image/x-icon')
        return "", 404

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
    @app.route('/v2/chat/completions', methods=['POST'])
    def proxy_chat_completion():
        """
        Secure gateway processing completions requests. Enforces structural hard-locks
        on Model Arena Mode for cost controls on Admin-Funded tiers.
        """
        user = request.tenant
        data = request.get_json(silent=True) or {}
        
        # 🚀 SECURE FEATURE-GATE LOCK: (V7 economic quota controls)
        is_arena_request = data.get("arena_mode", False) or data.get("is_duel", False)
        
        if is_arena_request and user['key_type'] == 'admin_funded':
            # HARD-BLOCK to prevent admin balance over-consumption (50% savings)
            return jsonify({
                "error": "Forbidden. Parallel Model Arena is locked for Admin-Funded accounts.",
                "message": "Admin accounts are restricted to standard chat models to preserve compute balances."
            }), 403

        # Economic Billing Quota pre-flight check (3.2.3.b)
        try:
            from server.logic.services import ServiceRegistry
            cog_router = ServiceRegistry.get("cognitive_router")
            if not cog_router.check_billing_quota(user['id']):
                return jsonify({
                    "error": "Quota Exhausted",
                    "message": "Your allocated token quota has been exhausted. Please contact your system administrator."
                }), 402
        except Exception as quota_ex:
            print(f"[Quota Warning] Billing check failed: {quota_ex}")

        # Extract inference context
        user_msg = ""
        system_msg = ""
        messages = data.get("messages", [])
        for m in messages:
            if m.get("role") == "system": system_msg = m.get("content", "")
            elif m.get("role") == "user": user_msg = m.get("content", "")

        stream = data.get("stream", False)
        web_search_enabled = data.get("web_search", False)
        
        # Cognitive Router capability task-based model mapping (3.2.1.a)
        task = data.get("task", "chat")
        model_id = data.get("model", "meta/llama-3.1-8b-instruct")
        try:
            from server.logic.services import ServiceRegistry
            cog_router = ServiceRegistry.get("cognitive_router")
            model_id = cog_router.route_model(user['id'], task, model_id)
        except Exception as route_ex:
            print(f"[Cognitive Router Warning] Model routing failed: {route_ex}")

        # --- PHASE 9: L3 SEMANTIC QUERY CACHE GATE ---
        if user_msg and not web_search_enabled:
            try:
                from server.logic.services import ServiceRegistry
                cache_svc = ServiceRegistry.get("cache")
                
                cached_response = db.get_semantic_cache_hit(user_msg, user['id'])
                if cached_response:
                    if cache_svc:
                        cache_svc.hits += 1
                    print(f"[Semantic Cache] HIT for query by user {user['id']}")
                    if stream:
                        def generate_cache_stream():
                            yield f"data: {json.dumps({'choices': [{'delta': {'content': cached_response}}]})}\n\n"
                            yield "data: [DONE]\n\n"
                        return Response(stream_with_context(generate_cache_stream()), mimetype="text/event-stream")
                    else:
                        return jsonify({
                            "id": f"chatcmpl-cache-{int(time.time())}",
                            "object": "chat.completion",
                            "created": int(time.time()),
                            "model": model_id,
                            "choices": [{"message": {"role": "assistant", "content": cached_response}}],
                            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                        })
                else:
                    if cache_svc:
                        cache_svc.misses += 1
            except Exception as e:
                print(f"[Semantic Cache] Lookup error: {e}")
        
        if web_search_enabled and user_msg:
            try:
                from server.logic.tool_manager import ToolManager
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
                import keyring
                # Priority 1: Direct link to Desktop Master Console Keyring
                funded_key = keyring.get_password("LLMChatApp", f"api_key_{provider}")
                if not funded_key and provider == "nvidia":
                    funded_key = keyring.get_password("LLMChatApp", "api_key")
                
                # Priority 2: Fallback to old SaaSConfigManager flatfile
                if not funded_key:
                    from web.core.config_manager import SaaSConfigManager
                    cfg = SaaSConfigManager()
                    funded_key = cfg.get_str("GLOBAL_KEYS", f"{provider}_api_key", "").strip()
                    
                if funded_key:
                    api_execution_key = funded_key
                else:
                    api_execution_key = None

            except Exception as cred_ex:
                print(f"[Credentials Warning]: Failed to extract host-funded keys: {cred_ex}")
        
        if not api_execution_key:
            return jsonify({
                "error": "Missing Credentials", 
                "message": f"API key for '{provider}' is not configured in the Admin Desktop Console. Please add it via Settings -> Credential Manager."
            }), 400

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

        # --- SECURITY BLOCK (SSRF) ---
        final_url = getattr(llm_client, "base_url", "")
        if final_url and user.get('username') != 'admin':
            if any(host in final_url.lower() for host in ['localhost', '127.0.0.1', '0.0.0.0']):
                return jsonify({
                    "error": "Forbidden", 
                    "message": "Local infrastructure models (Ollama/LM Studio) are restricted to the Super Admin."
                }), 403
        # -----------------------------

        try:
            from server.logic.services import ServiceRegistry
            circuit_breaker = ServiceRegistry.get("circuit_breaker")
        except KeyError:
            circuit_breaker = None

        def run_completion(*args, **kwargs):
            if provider == "google":
                from google.genai import types
                gemini_method = getattr(llm_client.google_client.models, "generate_content")
                resp = gemini_method(
                    model=llm_client.current_model,
                    contents=[m.get("content") for m in messages if m.get("role") != "system"],
                    config=types.GenerateContentConfig(
                        system_instruction=system_msg or None,
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                            )
                        ]
                    )
                )
                return getattr(resp, "text")
            else:
                if user_msg:
                    try:
                        moderation_fn = getattr(llm_client.client, "moderations")
                        moderation_create = getattr(moderation_fn, "create")
                        moderation_create(input=user_msg)
                    except Exception:
                        pass

                from openai import RateLimitError, APIError
                try:
                    completions_fn = getattr(llm_client.client.chat, "completions")
                    create_fn = getattr(completions_fn, "create")
                    resp = create_fn(
                        model=llm_client.current_model,
                        messages=messages,
                        max_tokens=4096,
                        user=str(user.get('id', 'default_user'))
                    )
                except RateLimitError as e:
                    print(f"[OpenAI] Rate limit hit: {e}")
                    raise e
                except APIError as e:
                    print(f"[OpenAI] API error: {e}")
                    raise e
                except Exception as e:
                    raise e

                refusal = getattr(resp.choices[0].message, "refusal", None)
                if refusal:
                    raise ValueError(f"Request refused by model: {refusal}")
                return getattr(resp.choices[0].message, "content")

        try:
            if stream:
                # Check circuit breaker state first
                if circuit_breaker and circuit_breaker.is_enabled():
                    current_cb_state = circuit_breaker.check_state()
                    if current_cb_state == "OPEN":
                        # Tripped. Execute failover.
                        text = circuit_breaker._execute_failover(user['id'], llm_client, run_completion, system_msg, user_msg, 4096, 0.7)
                        def generate_failover_stream():
                            yield f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}\n\n"
                            yield "data: [DONE]\n\n"
                        return Response(stream_with_context(generate_failover_stream()), mimetype="text/event-stream")

                # Test stream initialization to catch 500/429 immediately!
                try:
                    if provider == "google":
                        from google.genai import types
                        gemini_stream_method = getattr(llm_client.google_client.models, "generate_content_stream")
                        stream_resp = gemini_stream_method(
                            model=llm_client.current_model,
                            contents=[m.get("content") for m in messages if m.get("role") != "system"],
                            config=types.GenerateContentConfig(
                                system_instruction=system_msg or None,
                                safety_settings=[
                                    types.SafetySetting(
                                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                                    ),
                                    types.SafetySetting(
                                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                                    ),
                                    types.SafetySetting(
                                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                                    ),
                                    types.SafetySetting(
                                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                                    )
                                ]
                            )
                        )
                    else:
                        if user_msg:
                            try:
                                moderation_fn = getattr(llm_client.client, "moderations")
                                moderation_create = getattr(moderation_fn, "create")
                                moderation_create(input=user_msg)
                            except Exception:
                                pass

                        completions_fn = getattr(llm_client.client.chat, "completions")
                        create_fn = getattr(completions_fn, "create")
                        stream_resp = create_fn(
                            model=llm_client.current_model,
                            messages=messages,
                            stream=True,
                            max_tokens=4096,
                            user=str(user.get('id', 'default_user'))
                        )
                except Exception as stream_init_error:
                    # Tripped/Failed! Seamlessly trigger the sandboxed failover routing topology
                    if circuit_breaker and circuit_breaker.is_enabled():
                        circuit_breaker.record_failure()
                        print(f"[Circuit Breaker] Primary stream init failed: {stream_init_error}. Routing to failover...")
                        text = circuit_breaker._execute_failover(user['id'], llm_client, run_completion, system_msg, user_msg, 4096, 0.7)
                        def generate_failover_stream():
                            yield f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}\n\n"
                            yield "data: [DONE]\n\n"
                        return Response(stream_with_context(generate_failover_stream()), mimetype="text/event-stream")
                    raise stream_init_error

                def generate_stream():
                    response_text = ""
                    try:
                        if provider == "google":
                            for chk in stream_resp:
                                if chk.text:
                                    response_text += chk.text
                                    yield f"data: {json.dumps({'choices': [{'delta': {'content': chk.text}}]})}\n\n"
                        else:
                            for chunk in stream_resp:
                                if chunk.choices and chunk.choices[0].delta.content:
                                    text = chunk.choices[0].delta.content
                                    response_text += text
                                    yield f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}\n\n"
                        
                        if circuit_breaker:
                            circuit_breaker.record_success()

                        # Post-stream tally execution
                        approx_comp_tokens = int(len(response_text) / 4)
                        db.record_usage(user['id'], approx_prompt_tokens, approx_comp_tokens)
                        
                        # --- PHASE 9: CACHE MISS WRITE ---
                        if user_msg and response_text and not web_search_enabled:
                            try:
                                db.set_semantic_cache_hit(user_msg, user['id'], response_text)
                            except Exception as e:
                                print(f"[Semantic Cache] Write error: {e}")
                                
                        yield "data: [DONE]\n\n"
                        
                    except Exception as e:
                        if circuit_breaker:
                            circuit_breaker.record_failure()
                        err_msg = str(e).replace('"', '\\"')
                        yield f"data: {json.dumps({'error': err_msg})}\n\n"
                        yield "data: [DONE]\n\n"

                return Response(stream_with_context(generate_stream()), mimetype="text/event-stream")
                
            else:
                # Standard blocking completions proxy
                if circuit_breaker and circuit_breaker.is_enabled():
                    text = circuit_breaker.execute(
                        user['id'],
                        llm_client,
                        run_completion,
                        system_msg,
                        user_msg,
                        4096,
                        0.7
                    )
                else:
                    text = run_completion()
                
                # Ledger commit
                approx_comp_tokens = int(len(text) / 4)
                db.record_usage(user['id'], approx_prompt_tokens, approx_comp_tokens)
                
                # --- PHASE 9: CACHE MISS WRITE ---
                if user_msg and text and not web_search_enabled:
                    try:
                        db.set_semantic_cache_hit(user_msg, user['id'], text)
                    except Exception as e:
                        print(f"[Semantic Cache] Write error: {e}")
                
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


    @app.route('/api/documents/list', methods=['GET'])
    @app.route('/v1/documents/list', methods=['GET'])
    @app.route('/v2/documents/list', methods=['GET'])
    def list_documents():
        user = getattr(request, 'tenant', None)
        is_admin = user and user.get('key_type') == 'admin_funded'
        docs = ["README_ADMIN.md", "README_USER.md", "API_SPEC.md", "IDE_INTEGRATION.md", "SECURITY.md"] if is_admin else ["README_USER.md", "API_SPEC.md"]
        return jsonify({"success": True, "documents": docs})

    @app.route('/api/documents/content/<doc_name>', methods=['GET'])
    @app.route('/v1/documents/content/<doc_name>', methods=['GET'])
    @app.route('/v2/documents/content/<doc_name>', methods=['GET'])
    def get_document_content(doc_name):
        user = getattr(request, 'tenant', None)
        is_admin = user and user.get('key_type') == 'admin_funded'
        admin_docs = ["README_ADMIN.md", "IDE_INTEGRATION.md", "SECURITY.md"]
        user_docs = ["README_USER.md", "API_SPEC.md"]
        if doc_name not in admin_docs and doc_name not in user_docs:
            return jsonify({"success": False, "error": "Not Found"}), 404
        if not is_admin and doc_name in admin_docs:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        try:
            from server.utils.path_utils import get_resource_path
            doc_path = get_resource_path(os.path.join("saas", "saas_docs", doc_name))
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({"success": True, "content": content})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # --- DYNAMIC IDE EXTENSIONS PORTAL ENDPOINTS ---

    @app.route('/api/extensions', methods=['GET'])
    @app.route('/v1/extensions', methods=['GET'])
    @app.route('/v2/extensions', methods=['GET'])
    def list_extensions():
        """
        Crawls the extension/ directory, merges with extension/extensions_config.json,
        and returns the available integrations.
        """
        user = getattr(request, 'tenant', None)
        is_admin = user and user.get('key_type') == 'admin_funded'

        ext_dir = get_resource_path("extension")
        config_path = get_resource_path(os.path.join("extension", "extensions_config.json"))

        # Load dynamic extensions configuration file safely
        config_data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except Exception as e:
                print(f"[Extensions Config] Error reading ledger: {e}")

        # Scan folder for .vsix and .zip files
        discovered = []
        if os.path.exists(ext_dir):
            for file in os.listdir(ext_dir):
                if file.endswith('.vsix') or file.endswith('.zip'):
                    file_path = os.path.join(ext_dir, file)
                    size_bytes = os.path.getsize(file_path)
                    
                    # Convert to friendly size
                    if size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                    platform = "vscode" if file.endswith('.vsix') else "jetbrains"
                    
                    # Auto-parse version from standard naming syntax: name-1.0.0.ext
                    import re
                    ver_match = re.search(r'-(\d+\.\d+\.\d+)\.', file)
                    version = ver_match.group(1) if ver_match else "1.0.0"

                    # Look up in config
                    config_item = config_data.get(file, {})
                    is_visible = config_item.get("is_visible", False)
                    description = config_item.get("description", "No description available.")
                    name = config_item.get("name", file.split('-')[0].replace('_', ' ').title())

                    item_meta = {
                        "filename": file,
                        "name": name,
                        "version": version,
                        "platform": platform,
                        "is_visible": is_visible,
                        "description": description,
                        "file_size": size_str,
                        "updated_at": time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(file_path)))
                    }

                    # Filter visible extensions for normal tenants
                    if is_admin or is_visible:
                        discovered.append(item_meta)

        return jsonify({"success": True, "extensions": discovered})

    @app.route('/api/admin/extensions/save', methods=['POST'])
    @app.route('/v1/admin/extensions/save', methods=['POST'])
    @app.route('/v2/admin/extensions/save', methods=['POST'])
    def save_extension_meta():
        """Saves custom name, visibility status, and description edits back to extensions_config.json."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin save extension meta denied", "FAILED")
                return jsonify({"success": False, "error": "Unauthorized"}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin save extension meta granted", "SUCCESS")
        except Exception:
            is_admin = user and user.get('key_type') == 'admin_funded'
            if not is_admin:
                return jsonify({"success": False, "error": "Unauthorized"}), 403

        data = request.get_json(silent=True) or {}
        filename = data.get("filename")
        if not filename:
            return jsonify({"success": False, "error": "Missing filename"}), 400

        config_path = get_resource_path(os.path.join("extension", "extensions_config.json"))
        config_data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except Exception:
                pass

        if filename not in config_data:
            config_data[filename] = {}

        config_data[filename]["is_visible"] = bool(data.get("is_visible", False))
        config_data[filename]["description"] = data.get("description", "")
        config_data[filename]["name"] = data.get("name", filename.split('-')[0].title())

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/admin/extensions/generate-desc', methods=['POST'])
    @app.route('/v1/admin/extensions/generate-desc', methods=['POST'])
    @app.route('/v2/admin/extensions/generate-desc', methods=['POST'])
    def generate_extension_desc():
        """Generates dynamic AI Markdown descriptions for extensions."""
        user = getattr(request, 'tenant', None)
        try:
            from server.logic.services import ServiceRegistry
            security_svc = ServiceRegistry.get("security")
            if not security_svc.check_permission(user, "admin"):
                security_svc.log_audit(user.get('id', 'anonymous'), request.path, "Admin generate extension desc denied", "FAILED")
                return jsonify({"success": False, "error": "Unauthorized"}), 403
            security_svc.log_audit(user.get('id'), request.path, "Admin generate extension desc granted", "SUCCESS")
        except Exception:
            is_admin = user and user.get('key_type') == 'admin_funded'
            if not is_admin:
                return jsonify({"success": False, "error": "Unauthorized"}), 403

        data = request.get_json(silent=True) or {}
        filename = data.get("filename")
        platform = data.get("platform", "vscode")
        if not filename:
            return jsonify({"success": False, "error": "Missing filename"}), 400

        prompt = (
            f"Write a highly professional, beautifully formatted, concise README-style Markdown description "
            f"for an IDE Extension plugin. The file name is '{filename}' and it is for the '{platform}' ecosystem.\n\n"
            f"Provide a brief overview of features (like inline autocomplete, model parameters editing, and workspace syncing), "
            f"step-by-step instructions on how to install it, and connection instructions "
            f"(explaining how it connects to the local Universal API server on Port 5000).\n\n"
            f"Keep it under 300 words. Do not use generic placeholders. Focus on premium glassmorphic UI synergy and security."
        )

        try:
            # Re-use our centralized LLM client to execute the prompt
            llm_client = LLMClient()
            # Feed prompt dynamically using the active configuration keys (NVIDIA / deepseek / OpenAI based on active slot)
            from server.utils.path_utils import get_app_settings
            active_p = get_app_settings().value("active_provider_id", "nvidia")
            import keyring
            api_key = keyring.get_password("LLMChatApp", f"api_key_{active_p}") or keyring.get_password("LLMChatApp", "api_key")
            base_url = get_app_settings().value(f"url_{active_p}") or get_app_settings().value("base_url", "https://integrate.api.nvidia.com/v1")
            
            if not api_key:
                return jsonify({"success": False, "error": "Active provider API key is not configured in desktop vault."}), 400

            llm_client.set_api_key(api_key)
            llm_client.set_base_url(base_url)
            
            # Fetch active model
            from server.logic.model_io import load_all_models
            model_id = get_app_settings().value("current_model_id")
            if not model_id:
                active_models = [m for m in load_all_models() if m.get('provider', 'nvidia') == active_p and m.get('free', True)]
                model_id = active_models[0]["id"] if active_models else "meta/llama-3.1-8b-instruct"
            llm_client.set_model(model_id)

            # Execute completion
            full_response = llm_client._run_completion_internal(
                "You are an expert technical writer.",
                prompt,
                1024,
                0.3
            )
                
            return jsonify({"success": True, "description": full_response.strip()})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/extensions/download/<filename>', methods=['GET'])
    @app.route('/v1/extensions/download/<filename>', methods=['GET'])
    @app.route('/v2/extensions/download/<filename>', methods=['GET'])
    def download_extension(filename):
        """Streams the requested extension package securely from the extension/ folder."""
        # Clean the filename to prevent directory traversal
        filename = os.path.basename(filename)
        ext_dir = get_resource_path("extension")
        file_path = os.path.join(ext_dir, filename)

        if not os.path.exists(file_path):
            return jsonify({"success": False, "error": "Extension file not found"}), 404

        # Read config to verify visibility if not an admin
        user = getattr(request, 'tenant', None)
        is_admin = user and user.get('key_type') == 'admin_funded'

        if not is_admin:
            config_path = get_resource_path(os.path.join("extension", "extensions_config.json"))
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        if not config_data.get(filename, {}).get("is_visible", False):
                            return jsonify({"success": False, "error": "Unauthorized Access"}), 403
                except Exception:
                    return jsonify({"success": False, "error": "Unauthorized Access"}), 403
            else:
                return jsonify({"success": False, "error": "Unauthorized Access"}), 403

        # Stream download
        return send_from_directory(ext_dir, filename, as_attachment=True)


    @app.route('/', methods=['GET'])
    def srv_index():
        """Main browser portal entry rendering the Single Page Workspace canvas."""
        return render_template('index.html')

    @app.route('/app_icon.ico', methods=['GET'])
    def srv_favicon():
        """Serve the application icon directly from the core resources folder."""
        from server.utils.path_utils import get_resource_path
        icon_dir = get_resource_path("resources")
        return send_from_directory(icon_dir, "app_icon.ico")

    return app

from PySide6.QtCore import QThread, Signal

class SaaSServer(QThread):
    """
    Autonomous multi-threaded executor hosting the SaaS Flask application context
    inside a PySide6 QThread for seamless desktop-shell execution (Task 7.1.1).
    """
    
    # Optional signals for GUI integration
    status_changed = Signal(bool, str)
    api_manager_action = Signal(str)

    def __init__(self, host: str = '127.0.0.1', port: int = 5000, parent=None):
        super().__init__(parent)
        self.flask_app = create_saas_app()
        self.flask_app.saas_server_instance = self
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self._startup_error = None

    def start_server(self):
        """Locks onto target socket and prepares the Werkzeug listener before starting the QThread."""
        if self.running:
            return True, "Already active"
            
        import socket
        
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
            self.server = make_server(bind_address, self.port, self.flask_app, threaded=True)
            self.running = True
            
            # Start the QThread event loop
            super().start()
            return True, "Success"
        except Exception as e:
            return False, f"Runtime Fault: {str(e)}"

    def run(self):
        """QThread execution block. Silently runs the Flask SaaS server internally."""
        print(f"[SaaS Daemon] Background server established at http://{self.host}:{self.port}")
        if self.server:
            self.server.serve_forever()

    def stop(self):
        """Triggers non-destructive shutdown loop and terminates the QThread."""
        if self.server:
            print("[SaaS Daemon] Commencing soft shutdown sequence...")
            self.server.shutdown()
            self.server = None
        self.running = False
        self.quit()
        self.wait()
        return True
