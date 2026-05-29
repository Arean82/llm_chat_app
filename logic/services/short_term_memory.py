# logic/services/short_term_memory.py

import json
import logging
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumShortTermMemoryService")

class ShortTermMemoryService(BaseService):
    """
    Short-Term Session Memory Service backed by central Redis client with TTL.
    Supports thread-safe mock fallback mode.
    """
    def __init__(self):
        super().__init__()
        self.redis_svc = None
        self.client = None

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Short-Term Memory Service...")
        try:
            self.redis_svc = ServiceRegistry.get("redis")
            self.client = self.redis_svc.get_client()
            logger.info("Short-Term Memory Service bound to central Redis Client manager.")
        except Exception as e:
            logger.error(f"Short-Term Memory Service binding failed: {str(e)}")
            return False
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Short-Term Memory Service...")
        self.client = None
        self.redis_svc = None
        return True

    def save_session(self, session_id: str, messages: list, ttl: int = 3600) -> bool:
        """Stores the list of messages in a JSON string under the key session:{session_id}."""
        if not self.is_initialized or not self.client:
            logger.warning("Short-Term Memory Service not initialized. Cannot save session.")
            return False
        try:
            key = f"session:{session_id}"
            serialized = json.dumps(messages)
            self.client.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {str(e)}")
            return False

    def get_session(self, session_id: str) -> list:
        """Retrieves the active session messages, returning an empty list if expired/absent."""
        if not self.is_initialized or not self.client:
            logger.warning("Short-Term Memory Service not initialized. Returning empty session.")
            return []
        try:
            key = f"session:{session_id}"
            data = self.client.get(key)
            if data is None:
                return []
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id}: {str(e)}")
            return []

    def append_to_session(self, session_id: str, message: dict, ttl: int = 3600) -> bool:
        """Appends a new message block thread-safely and refreshes the cache TTL."""
        if not self.is_initialized or not self.client:
            logger.warning("Short-Term Memory Service not initialized. Cannot append.")
            return False
        try:
            messages = self.get_session(session_id)
            messages.append(message)
            return self.save_session(session_id, messages, ttl)
        except Exception as e:
            logger.error(f"Failed to append to session {session_id}: {str(e)}")
            return False

    def clear_session(self, session_id: str) -> bool:
        """Purges session keys from the database."""
        if not self.is_initialized or not self.client:
            logger.warning("Short-Term Memory Service not initialized. Cannot clear session.")
            return False
        try:
            key = f"session:{session_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear session {session_id}: {str(e)}")
            return False

# Register ShortTermMemoryService
ServiceRegistry.register("short_term_memory", ShortTermMemoryService())
