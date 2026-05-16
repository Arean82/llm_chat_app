# workers/vector_indexer_worker.py
# Background worker designed to async compute embeddings and upsert conversational pairs to Qdrant.

from PySide6.QtCore import QThread, Signal
from datetime import datetime
from logic.vector_db import VectorDatabase

class VectorIndexerWorker(QThread):
    """
    Background daemon performing API requests to generate vectors and 
    writes text/embedding nodes into the persistent Qdrant cluster.
    """
    completed = Signal(bool)

    def __init__(self, llm_client, user_text: str, assistant_text: str, conversation_id: int, model_id: str, parent=None):
        super().__init__(parent)
        self.llm_client = llm_client
        self.user_text = user_text
        self.assistant_text = assistant_text
        self.conversation_id = conversation_id
        self.model_id = model_id

    def run(self):
        if not self.user_text or not self.assistant_text:
            self.completed.emit(False)
            return

        try:
            # Construct the combined context frame
            exchange_payload = f"User: {self.user_text.strip()}\nAssistant: {self.assistant_text.strip()}"
            
            # Compute semantic vector payload (blocks inside this thread, safe from main loop)
            vector = self.llm_client.generate_embeddings(exchange_payload)
            
            if not vector:
                print("[VectorIndexer] Failed to generate embeddings (empty list returned).")
                self.completed.emit(False)
                return

            # Identify provider target
            provider = self.llm_client.get_current_provider()
            collection_name = f"global_history_{provider}"

            # Compile metadata payload structure
            payload = {
                "conversation_id": self.conversation_id,
                "model_id": self.model_id,
                "timestamp": datetime.now().isoformat(),
                "user_query": self.user_text.strip(),
                "assistant_reply": self.assistant_text.strip(),
                "full_text": exchange_payload
            }

            # Push to Local SQLite/Qdrant Engine
            db = VectorDatabase.get_instance()
            success = db.upsert_segment(collection_name, vector, payload)
            
            if success:
                print(f"[VectorIndexer] Successfully indexed conversation ID {self.conversation_id} to '{collection_name}'")
            
            self.completed.emit(success)

        except Exception as e:
            print(f"[VectorIndexer] CRITICAL fault: {e}")
            self.completed.emit(False)
