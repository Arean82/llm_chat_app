# logic/vector_db.py
# Local Qdrant Vector Engine providing Persistent Dense Retrieval storage capabilities.

import os
import uuid
from pathlib import Path
from utils.storage_config import StorageManager

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

class VectorDatabase:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.client = None
        if not QDRANT_AVAILABLE:
            print("[VectorDB] Qdrant client not found. Vector storage will be inactive.")
            return

        try:
            # Resolve absolute storage paths via system manager
            base_dir = StorageManager.get_instance().get_storage_root()
            self.db_dir = base_dir / "vector_db"
            self.db_dir.mkdir(parents=True, exist_ok=True)
            
            # Instantiate purely localized File-based mode
            self.client = QdrantClient(path=str(self.db_dir))
            print(f"[VectorDB] Initialized successfully at {self.db_dir}")
        except Exception as e:
            print(f"[VectorDB] Initialization Error: {e}")
            self.client = None

    def ensure_collection(self, collection_name: str, vector_size: int):
        """Creates the named collection if absent, specifying the expected dimension."""
        if not self.client:
            return False
        
        # VERSIONED COLLECTION NAME: Ensure we don't mix dimensions
        versioned_name = f"{collection_name}_{vector_size}"
        
        try:
            if not self.client.collection_exists(versioned_name):
                self._create_collection_internal(versioned_name, vector_size)
            return True, versioned_name
        except Exception as e:
            print(f"[VectorDB] Error establishing collection {versioned_name}: {e}")
            return False, versioned_name

    def _create_collection_internal(self, collection_name, vector_size):
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        print(f"[VectorDB] Created Collection: '{collection_name}'")

    def upsert_segment(self, collection_name: str, vector: list, payload: dict):
        """Saves a text chunk and its embedding vector into persistent storage."""
        if not self.client or not vector:
            return False
        try:
            vector_size = len(vector)
            success, target_name = self.ensure_collection(collection_name, vector_size)
            if not success:
                return False

            # Generate deterministic or random point ID
            point_id = str(uuid.uuid4())
            
            self.client.upsert(
                collection_name=target_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            print(f"[VectorDB] Upsert failed in {collection_name}: {e}")
            return False

    def search_similar(self, collection_name: str, query_vector: list, limit: int = 5, score_threshold: float = 0.3) -> list:
        """Locates top-K semantically closest snippets from vector database."""
        if not self.client or not query_vector:
            return []
        
        vector_size = len(query_vector)
        versioned_name = f"{collection_name}_{vector_size}"
        
        try:
            # Standard sanity safeguard: skip search if collection not instantiated yet
            if not self.client.collection_exists(versioned_name):
                return []

            # Using the modern high-level Unified Query Points Interface 
            response = self.client.query_points(
                collection_name=versioned_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True
            )
            
            # Format structured matches (from response.points array)
            hits = []
            if response and hasattr(response, 'points'):
                for r in response.points:
                    hits.append({
                        "id": r.id,
                        "score": r.score,
                        "payload": r.payload
                    })
            return hits
        except Exception as e:
            print(f"[VectorDB] Search operation failed on {collection_name}: {e}")
            return []

    def wipe_db(self):
        """Deletes all collections for clean factory reset."""
        if not self.client:
            return
        try:
            collections = self.client.get_collections().collections
            for c in collections:
                self.client.delete_collection(collection_name=c.name)
            print("[VectorDB] Fully purged all internal data collections.")
        except Exception as e:
             print(f"[VectorDB] Database purge failure: {e}")

    def close(self):
        """Explicitly teardown the Qdrant connection to release SQLite locks and prevent shutdown warnings."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[VectorDB] Error closing client: {e}")
            finally:
                self.client = None
