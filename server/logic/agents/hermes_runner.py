# server/logic/agents/hermes_runner.py
"""
Hermes Agent Runner (v9.0.0)
Decoupled background process executing autonomous reasoning loops for tenants.
Uses the tenant's BYOK credentials via the SaaS API Gateway.
"""

import os
import sys
import time
import logging

# Ensure root directory is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from server.logic.llm_client import LLMClient

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Hermes) %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HermesRunner")

def run_agent_loop():
    logger.info("Initializing Hermes Autonomous Agent Loop...")
    
    gateway_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    tenant_id = os.environ.get("TENANT_USER_ID")
    
    if not gateway_url or not api_key:
        logger.error("Configuration missing! Environment variables OPENAI_BASE_URL and OPENAI_API_KEY must be set.")
        sys.exit(1)
        
    logger.info(f"Target Gateway: {gateway_url}")
    logger.info(f"Active Tenant ID: {tenant_id}")
    
    # Initialize connection client
    client = LLMClient()
    client.set_base_url(gateway_url)
    client.set_api_key(api_key)
    
    # Pull standard catalog models from active gateway
    try:
        models = client.fetch_custom_openai_models(gateway_url, api_key)
        if models:
            client.set_model(models[0]["id"])
            logger.info(f"Using default model: {models[0]['id']}")
    except Exception as e:
        logger.warning(f"Failed to fetch model catalog: {e}. Falling back to default.")
    
    logger.info("Hermes Agent loop is now running. Press Ctrl+C to terminate.")
    
    try:
        while True:
            # Perform background tasks (simulated RAG processing or query check)
            logger.info("Polling for active agent workspace jobs...")
            time.sleep(15)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Terminating Hermes Agent...")
        sys.exit(0)

if __name__ == "__main__":
    run_agent_loop()
