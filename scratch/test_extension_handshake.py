# scratch/test_extension_handshake.py
"""
Automated Integration Handshake Test for IDE Extensions.
Validates dynamic URL pinging, tenant registration, credentials authentication,
and bearer-authorized proxy routing completions.
"""

import sys
import json
import random
import urllib.request
import urllib.error

# Target Host URL (points to SaaS Multi-Tenant server port 8888 by default for register/login)
BASE_URL = "http://localhost:8888"

def make_request(url, method="GET", payload=None, headers=None):
    if headers is None:
        headers = {}
    
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            try:
                parsed_body = json.loads(body)
            except json.JSONDecodeError:
                parsed_body = body
            return status, parsed_body
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8")
        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError:
            parsed_body = body
        return status, parsed_body
    except urllib.error.URLError as e:
        print(f"❌ Network URLError contacting {url}: {e.reason}")
        return None, str(e.reason)
    except Exception as e:
        print(f"❌ Unexpected request failure: {e}")
        return None, str(e)

def run_handshake_test():
    print("=" * 60)
    print("🚀 STARTING EXTENSION HANDSHAKE INTEGRATION TEST")
    print(f"Target Server: {BASE_URL}")
    print("=" * 60)

    # ----------------------------------------------------
    # PHASE 1: Health Ping Check
    # ----------------------------------------------------
    health_url = f"{BASE_URL}/health"
    print(f"\n[Phase 1]: Pinging health endpoint: {health_url}...")
    status, res = make_request(health_url, "GET")
    
    if status != 200:
        print(f"❌ Health check failed with status {status}. Is the Flask server running on port 5000?")
        sys.exit(1)
    
    print(f"✅ Health check successful: {res}")

    # ----------------------------------------------------
    # PHASE 2: Dynamic User Registration
    # ----------------------------------------------------
    rand_id = random.randint(1000, 9999)
    username = f"ext_user_{rand_id}"
    email = f"ext_{rand_id}@quantum-ide.local"
    password = f"Pass_{rand_id}_Secure"
    api_key = f"sk-proj-ext-key-{rand_id}-secure-mock-auth"
    
    register_url = f"{BASE_URL}/api/register"
    payload = {
        "api_key": api_key,
        "username": username,
        "email": email,
        "password": password,
        "key_type": "byok"
    }
    
    print(f"\n[Phase 2]: Registering new user '{username}' via POST /api/register...")
    status, res = make_request(register_url, "POST", payload)
    
    if status not in (200, 201) or not res.get("success"):
        print(f"❌ User registration failed with status {status}: {res}")
        sys.exit(1)
        
    print(f"✅ User registered successfully. Workspace Provisioned: {res.get('workspace_provisioned')}")

    # ----------------------------------------------------
    # PHASE 3: Login Authentication
    # ----------------------------------------------------
    login_url = f"{BASE_URL}/api/login"
    login_payload = {
        "username_or_email": username,
        "password": password
    }
    
    print(f"\n[Phase 3]: Authenticating user credentials via POST /api/login...")
    status, res = make_request(login_url, "POST", login_payload)
    
    if status != 200 or not res.get("success"):
        print(f"❌ Login authentication failed with status {status}: {res}")
        sys.exit(1)
        
    user_data = res.get("user", {})
    passport_token = user_data.get("passport_token")
    if not passport_token:
        passport_token = user_data.get("api_key")
        
    if not passport_token:
        print("❌ Login response did not return a valid bearer passport_token or api_key.")
        sys.exit(1)
        
    print(f"✅ Login authentication successful.")
    print(f"   Provisioned Passport Token: {passport_token[:15]}...[SECURED]")

    # ----------------------------------------------------
    # PHASE 4: Bearer-Authorized Query Completion Routing
    # ----------------------------------------------------
    completions_url = f"{BASE_URL}/v1/chat/completions"
    completions_payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Confirm extension handshake connectivity."}
        ],
        "temperature": 0.5,
        "max_tokens": 100
    }
    headers = {
        "Authorization": f"Bearer {passport_token}"
    }
    
    print(f"\n[Phase 4]: Routing chat completion query via POST /v1/chat/completions...")
    status, res = make_request(completions_url, "POST", completions_payload, headers)
    
    if status != 200:
        print(f"❌ Chat completions routing failed with status {status}: {res}")
        sys.exit(1)
        
    try:
        choice = res["choices"][0]
        content = choice["message"]["content"]
        print(f"✅ Chat completions successful! Response:")
        print(f"   {content.strip()}")
    except (KeyError, IndexError) as e:
        print(f"❌ Failed to parse choices from completion response: {res}. Error: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 ALL DYNAMIC EXTENSION HANDSHAKE TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_handshake_test()
