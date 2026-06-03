# logic/services/embedding_service.py

import hashlib
import logging
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumEmbeddingService")

class EmbeddingService(BaseService):
    """
    Decoupled Embedding Service strictly isolated from Qt/GUI bindings.
    Orchestrates semantic vector generation, L2 chunk caching, and direct Qdrant index updates.
    """
    def __init__(self):
        super().__init__()
        self.db_mgr = None

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Embedding Service...")
        from web.core.tenant_db import TenantDatabaseManager
        self.db_mgr = TenantDatabaseManager()
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Embedding Service...")
        self.db_mgr = None
        return True

    def generate_embedding(self, text: str, user_id: int = 1, client_instance=None) -> list:
        """
        Orchestrates semantic vector calculations.
        Checks L2 cache first, then falls back to live API calculations and caches on miss.
        """
        if not text or not text.strip():
            return []

        chunk_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

        # 1. Query L2 Cache
        if self.db_mgr:
            try:
                cached_vector = self.db_mgr.get_cached_embedding(chunk_hash)
                if cached_vector:
                    logger.info(f"[Embedding Cache] HIT for chunk {chunk_hash[:8]}... Bypassing API.")
                    return cached_vector
            except Exception as e:
                logger.error(f"[Embedding Cache] L2 Cache Lookup failed: {str(e)}")

        # 2. Live API Calculation
        vector = []
        if client_instance:
            provider = client_instance.get_current_provider()
            payload_slice = text[:8000] # Safe input bounds clip
            
            if provider == "google":
                if client_instance.google_client:
                    try:
                        result = client_instance.google_client.models.embed_content(
                            model="text-embedding-004",
                            contents=payload_slice
                        )
                        if result and result.embeddings:
                            vector = result.embeddings[0].values
                    except Exception as e:
                        logger.error(f"[Embedding] Google live calculation failed: {str(e)}")
            else:
                if client_instance.client:
                    try:
                        base_url_lower = client_instance.base_url.lower()
                        if "nvidia.com" in base_url_lower:
                            embed_model = "nvidia/nv-embed-v1"
                        elif "api.openai.com" in base_url_lower:
                            embed_model = "text-embedding-3-small"
                        else:
                            embed_model = "text-embedding-3-small"

                        kwargs = {
                            "model": embed_model,
                            "input": payload_slice,
                            "timeout": 15.0
                        }

                        if "nvidia.com" in base_url_lower:
                            kwargs["extra_body"] = {"input_type": "query"}

                        resp = client_instance.client.embeddings.create(**kwargs)
                        vector = resp.data[0].embedding
                    except Exception as e:
                        # Local model / Ollama fallback try
                        try:
                            resp = client_instance.client.embeddings.create(
                                model="nomic-embed-text",
                                input=payload_slice,
                                timeout=5.0
                            )
                            vector = resp.data[0].embedding
                        except Exception as local_err:
                            logger.error(f"[Embedding] Live calculations failed: {str(e)} (Local fallback: {str(local_err)})")

        # 3. Write L2 Cache Miss
        if vector and self.db_mgr:
            try:
                self.db_mgr.set_cached_embedding(chunk_hash, user_id, text, vector)
                logger.info(f"[Embedding Cache] MISS - Indexed chunk {chunk_hash[:8]} to L2.")
            except Exception as e:
                logger.error(f"[Embedding Cache] L2 Cache Write failed: {str(e)}")

        return vector

    def embed_and_index(self, tenant_id: str, collection_name: str, text: str, payload: dict, client_instance=None) -> bool:
        """Computes semantic embedding vector and upserts it directly to local Qdrant collection."""
        try:
            vector = self.generate_embedding(text, user_id=int(tenant_id), client_instance=client_instance)
            if not vector:
                logger.warning(f"Failed to generate embedding vector for tenant {tenant_id}.")
                return False

            from server.logic.vector_db import VectorDatabase
            vdb = VectorDatabase.get_instance()
            return vdb.upsert_segment(collection_name, vector, payload)
        except Exception as e:
            logger.error(f"Error during Qdrant indexing: {str(e)}")
            return False

# Auto-register EmbeddingService
ServiceRegistry.register("embedding", EmbeddingService())
