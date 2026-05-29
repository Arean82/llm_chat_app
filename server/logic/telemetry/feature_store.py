# logic/telemetry/feature_store.py
import logging
import json
from typing import Any, Dict

from server.logic.services.base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumFeatureStore")

class FeatureStore(BaseService):
    """
    6.1.1 Feature Flags Database
    Manages dynamic feature flags (e.g. enable_agents, beta_features)
    backed by Redis for hot-swapping SaaS features globally without restarts.
    """
    def __init__(self):
        super().__init__()
        self.redis_svc = None
        self.client = None
        # Local fallback cache in case Redis is offline
        self._local_cache: Dict[str, Any] = {
            "enable_agents": False,
            "beta_features": False,
            "advanced_telemetry": True
        }
        self._prefix = "feature_flag:"

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Feature Store...")
        try:
            self.redis_svc = ServiceRegistry.get("redis")
            self.client = self.redis_svc.get_client()
        except Exception as e:
            logger.warning(f"FeatureStore could not bind to Redis ({e}). Running in isolated memory mode.")
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Feature Store...")
        return True

    def get_flag(self, flag_name: str, default: Any = False) -> Any:
        """Retrieves a feature flag. Falls back to local cache if Redis fails."""
        if not self.client:
            return self._local_cache.get(flag_name, default)

        try:
            raw = self.client.get(f"{self._prefix}{flag_name}")
            if raw is None:
                # Cache miss, fallback to local default
                return self._local_cache.get(flag_name, default)
                
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
                
            # Attempt to parse as JSON (for bools, dicts)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        except Exception as e:
            logger.error(f"Error fetching feature flag '{flag_name}': {e}")
            return self._local_cache.get(flag_name, default)

    def set_flag(self, flag_name: str, value: Any) -> bool:
        """Sets a feature flag globally in Redis and locally."""
        self._local_cache[flag_name] = value
        
        if not self.client:
            return True
            
        try:
            serialized = json.dumps(value)
            self.client.set(f"{self._prefix}{flag_name}", serialized)
            logger.info(f"Feature flag '{flag_name}' updated to: {value}")
            return True
        except Exception as e:
            logger.error(f"Error setting feature flag '{flag_name}': {e}")
            return False

# Register FeatureStore
ServiceRegistry.register("feature_store", FeatureStore())
