# logic/services/cognitive_router_service.py

import logging
import time
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumCognitiveRouterService")

class CognitiveRouterService(BaseService):
    """
    Cognitive Model Router & Cost Engine.
    Handles capability-based model routing, provider health aggregation,
    and pre-flight token quota/billing quota checks.
    """
    def __init__(self):
        super().__init__()
        self.provider_health = {
            "nvidia": True,
            "openai": True,
            "google": True,
            "groq": True,
            "ollama": True
        }

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Cognitive Router Service...")
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Cognitive Router Service...")
        return True

    def route_model(self, user_id: int, task: str, requested_model: str = None) -> str:
        """
        Capability Mapping Engine (3.2.1.a).
        Dynamically routes chat completion requests to the best capability-fit model based on task.
        - task: "code", "vision", "reasoning", or "chat"
        """
        # Centralized enterprise default routing matrix
        routing_matrix = {
            "code": "meta/llama-3.1-405b-instruct",
            "vision": "nvidia/llama-3.2-11b-vision-instruct",
            "reasoning": "deepseek-ai/deepseek-r1",
            "chat": "meta/llama-3.1-8b-instruct"
        }
        
        # Load user settings to see if the tenant has customized their cognitive routes
        try:
            auth_service = ServiceRegistry.get("auth")
            settings = auth_service.get_user_settings(user_id)
            custom_routing = settings.get("custom_cognitive_routing", {})
            if isinstance(custom_routing, dict) and task in custom_routing:
                routed = custom_routing[task]
                logger.info(f"Custom cognitive route resolved for user {user_id} task '{task}': {routed} (overriding default)")
                return routed
        except Exception as e:
            logger.error(f"Error loading custom cognitive routes: {str(e)}")
            
        routed = routing_matrix.get(task, requested_model or routing_matrix["chat"])
        logger.info(f"Cognitive route resolved for user {user_id} task '{task}': {routed}")
        return routed

    def ping_provider(self, provider: str, url: str) -> bool:
        """
        Health-Check Aggregator (3.2.2.a).
        Performs a lightweight ping check on provider endpoints to determine uptime states.
        """
        import requests
        try:
            # Enforce strict 2-second timeout to prevent locking up thread executors
            response = requests.get(url, timeout=2.0)
            is_healthy = response.status_code < 500
            self.provider_health[provider] = is_healthy
            return is_healthy
        except Exception:
            self.provider_health[provider] = False
            return False

    def check_billing_quota(self, user_id: int) -> bool:
        """
        Pre-flight check to verify if the tenant's admin-funded token quota is exceeded (3.2.3.b).
        Returns True if quota is healthy (or user is BYOK/unlimited), False if exhausted.
        """
        try:
            auth_service = ServiceRegistry.get("auth")
            
            # Fetch settings blob to get token_quota constraints
            settings = auth_service.get_user_settings(user_id)
            token_quota = settings.get("token_quota")
            
            if token_quota is None or int(token_quota) <= 0:
                # No quota limit configured (unlimited admin-funded)
                return True
                
            # Query db for total consumed across their historical daily logs
            tenants = auth_service.db.get_all_tenants()
            user_data = next((t for t in tenants if t["id"] == user_id), None)
            
            if user_data:
                consumed = int(user_data.get("total_tokens", 0))
                if consumed >= int(token_quota):
                    logger.warning(f"Pre-flight Billing Quota Rejected: Tenant {user_id} has exhausted their allocated quota ({consumed}/{token_quota} tokens).")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking billing quota for user {user_id}: {str(e)}")
            return True # Fail-safe: allow requests if database is temporarily locked

# Auto-register CognitiveRouterService
ServiceRegistry.register("cognitive_router", CognitiveRouterService())
