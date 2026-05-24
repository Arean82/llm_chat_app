import time
import requests
import json
import hashlib
import sys
import os

# Add project root to path for local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from saas.tenant_db import TenantDatabaseManager
from logic.llm_client import LLMClient

# Ensure default admin is provisioned
db = TenantDatabaseManager()
admin = db.authenticate_by_login('admin', 'admin')
if not admin:
    print("Admin not found. Cannot proceed with API tests.")
    sys.exit(1)

TOKEN = admin['api_key']
USER_ID = admin['id']
BASE_URL = "http://127.0.0.1:8888"

print("--- Test 4: Clear Cache ---")
db.clear_tenant_cache(USER_ID)
print("Cache cleared.\n")

print("--- Test 1 & 2: /v1/chat/completions cache ---")
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
payload = {
    "model": "meta/llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "stream": False
}

start = time.perf_counter()
res1 = requests.post(f"{BASE_URL}/v1/chat/completions", headers=headers, json=payload)
end = time.perf_counter()
print(f"Request 1 (Miss) Time: {end - start:.4f}s")
if res1.status_code == 200:
    print(f"Response: {res1.json()['choices'][0]['message']['content'][:50]}...")
else:
    print(f"Error: {res1.text}")

start = time.perf_counter()
res2 = requests.post(f"{BASE_URL}/v1/chat/completions", headers=headers, json=payload)
end = time.perf_counter()
print(f"Request 2 (Hit) Time: {end - start:.4f}s")
if res2.status_code == 200:
    print(f"Response: {res2.json()['choices'][0]['message']['content'][:50]}...")
else:
    print(f"Error: {res2.text}")

print("\n--- Test 3: Embedding Cache (Local LLMClient bypass) ---")
llm = LLMClient()
text = "This is a test document for embedding caching."
chunk_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

print(f"Pre-check DB for hash {chunk_hash[:8]}: {db.get_cached_embedding(chunk_hash) is not None}")

# Simulate caching by inserting directly
db.set_cached_embedding(chunk_hash, USER_ID, text, [0.1, 0.2, 0.3])

print(f"Post-insert DB for hash {chunk_hash[:8]}: {db.get_cached_embedding(chunk_hash) is not None}")

# Now try fetching via LLMClient
vector = llm.generate_embeddings(text, user_id=USER_ID)
print(f"LLMClient generate_embeddings returned vector length: {len(vector)}")

print("\nAll Tests Complete.")
