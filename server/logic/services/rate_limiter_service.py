# logic/services/rate_limiter_service.py

import time
import logging
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumRateLimiterService")

class RateLimiterService(BaseService):
    """
    Unified Redis-backed Token-Bucket Rate Limiter.
    Throttles API queries per IP address or per Tenant ID.
    Compatible with both Live Redis/Memurai and the Mock fallback modes.
    """
    def __init__(self):
        super().__init__()
        self.redis_svc = None
        self.client = None

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Rate Limiter Service...")
        try:
            self.redis_svc = ServiceRegistry.get("redis")
            self.client = self.redis_svc.get_client()
            logger.info("Rate Limiter Service bound to central Redis Client manager.")
        except Exception as e:
            logger.error(f"Rate Limiter Service binding failed: {str(e)}")
            return False
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Rate Limiter Service...")
        self.client = None
        self.redis_svc = None
        return True

    def is_allowed(self, key: str, limit: int, period: int = 60) -> bool:
        """
        Token Bucket algorithm backed by Redis.
        - key: Unique identifier (e.g. "ip:127.0.0.1" or "tenant:5")
        - limit: Maximum requests allowed in the period (RPM limit)
        - period: The bucket window duration in seconds (defaults to 60)
        """
        if not self.is_initialized or not self.client:
            logger.warning("Rate Limiter Service not initialized. Allowing request by default.")
            return True

        if limit <= 0:
            return True  # Unlimited

        now = time.time()
        tokens_key = f"rate_limit:{key}:tokens"
        last_updated_key = f"rate_limit:{key}:last_updated"

        try:
            # 1. Fetch current state from Redis
            tokens_bytes = self.client.get(tokens_key)
            last_updated_bytes = self.client.get(last_updated_key)

            if tokens_bytes is None or last_updated_bytes is None:
                # First request or expired bucket
                tokens = float(limit)
                last_updated = now
            else:
                # Decode bytes to float
                if isinstance(tokens_bytes, bytes):
                    tokens = float(tokens_bytes.decode('utf-8'))
                else:
                    tokens = float(tokens_bytes)

                if isinstance(last_updated_bytes, bytes):
                    last_updated = float(last_updated_bytes.decode('utf-8'))
                else:
                    last_updated = float(last_updated_bytes)

            # 2. Replenish tokens based on elapsed time
            elapsed = max(0.0, now - last_updated)
            # Limit / Period represents rate per second
            replenish_rate = float(limit) / float(period)
            tokens = min(float(limit), tokens + elapsed * replenish_rate)
            last_updated = now

            # 3. Check and consume a token
            allowed = False
            if tokens >= 1.0:
                tokens -= 1.0
                allowed = True

            # 4. Save state back to Redis with a TTL of double the period to prevent memory leaks
            ttl = int(period * 2)
            self.client.set(tokens_key, str(tokens), ex=ttl)
            self.client.set(last_updated_key, str(last_updated), ex=ttl)

            if not allowed:
                logger.warning(f"Rate limit hit for key '{key}' (Limit: {limit} requests per {period}s)")
            return allowed

        except Exception as e:
            # Resilient fallback: allow request in case of Redis errors
            logger.error(f"Error checking rate limit in Redis for key '{key}': {str(e)}. Allowing by default.")
            return True

# Auto-register RateLimiterService
ServiceRegistry.register("rate_limiter", RateLimiterService())
