import time
import logging
import hashlib
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumCacheService")

class CacheService(BaseService):
    """
    Central tenant-scoped semantic caching, ingestion bypassing,
    and SHA-256 payload registry service. Helps skip model executions for redundant queries.
    """
    def __init__(self):
        super().__init__()
        # In-memory stores structured per tenant_id
        # Structure: { tenant_id: { query_string: (response_string, timestamp) } }
        self._query_cache = {}
        
        # Cryptographic content registry: { tenant_id: { sha256_hash: (metadata, timestamp) } }
        self._content_registry = {}
        
        # Telemetry metrics
        self.hits = 0
        self.misses = 0

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Cache Service...")
        return True

    def on_shutdown(self) -> bool:
        logger.info("Clearing Quantum Cache Service in-memory tables...")
        self._query_cache.clear()
        self._content_registry.clear()
        return True

    def get_query_cache(self, tenant_id: str, query: str) -> str:
        """
        Retrieves cached response for an exact query match.
        Increment hit/miss telemetry.
        """
        tenant_store = self._query_cache.get(tenant_id)
        if not tenant_store:
            self.misses += 1
            return None
        
        entry = tenant_store.get(query.strip())
        if not entry:
            self.misses += 1
            return None
        
        response, timestamp = entry
        self.hits += 1
        logger.info(f"Cache HIT for query in tenant sandboxed cache: '{query[:30]}...'")
        return response

    def set_query_cache(self, tenant_id: str, query: str, response: str) -> None:
        """Saves a response to the tenant-isolated query cache."""
        if tenant_id not in self._query_cache:
            self._query_cache[tenant_id] = {}
        
        self._query_cache[tenant_id][query.strip()] = (response, time.time())
        logger.info(f"Cached response for query: '{query[:30]}...'")

    def invalidate_query_cache(self, tenant_id: str) -> None:
        """Invalidate the entire query cache for a specific tenant."""
        if tenant_id in self._query_cache:
            self._query_cache[tenant_id].clear()
            logger.info(f"Invalidated query cache for tenant: '{tenant_id}'")

    # --- CRYPTOGRAPHIC PAYLOAD HASHING REGISTRY (9.1.1) ---

    def calculate_payload_hash(self, tenant_id: str, text_payload: str) -> str:
        """Generate a SHA-256 hash for a normalized document payload scoped by tenant."""
        normalized = f"{tenant_id}:{text_payload.strip()}".encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    def register_content_hash(self, tenant_id: str, content_hash: str, metadata: dict) -> None:
        """Register a content hash to represent indexed document chunks."""
        if tenant_id not in self._content_registry:
            self._content_registry[tenant_id] = {}
        
        self._content_registry[tenant_id][content_hash] = (metadata, time.time())
        logger.info(f"Registered content hash: {content_hash} for tenant: {tenant_id}")

    def check_content_hash(self, tenant_id: str, content_hash: str) -> dict:
        """Check if a SHA-256 content hash exists inside a tenant's index."""
        tenant_store = self._content_registry.get(tenant_id)
        if not tenant_store:
            return None
        
        entry = tenant_store.get(content_hash)
        if not entry:
            return None
        
        metadata, timestamp = entry
        return metadata

    def get_hit_ratio(self) -> float:
        """Calculate the cache hit percentage ratio."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round((self.hits / total) * 100, 2)


# Register CacheService automatically
ServiceRegistry.register("cache", CacheService())
