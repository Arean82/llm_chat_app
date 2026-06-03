# workers/async_worker.py

import os
import sys
import time
import json
import logging
import traceback
import hashlib
import threading
from datetime import datetime

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s"
)
logger = logging.getLogger("QuantumAsyncWorker")

# Bootstrap shared service registry
from server.logic.services.base_service import ServiceRegistry
import server.logic.services # Auto-registers all core services

class AsyncWorker:
    """
    Standalone, GUI-less Python daemon process.
    Handles heavy CPU and IO workloads asynchronously via the RedisQueueBroker.
    Includes comprehensive retry loops and Dead Letter Queue (DLQ) containment.
    """
    def __init__(self):
        self.queue_broker = None
        self.llm_client = None
        self.stop_event = threading.Event() if 'threading' in sys.modules else None
        
    def start(self):
        logger.info("Initializing Quantum Core Services in Standalone Daemon Mode...")
        # Initialize storage, RAG, cache, telemetry, and redis connections
        if not ServiceRegistry.initialize_all():
            logger.error("Failed to initialize all registered backend services. Exiting.")
            sys.exit(1)

        self.queue_broker = ServiceRegistry.get("queue_broker")
        
        # Instantiate and hydrate the LLM client for embedding generation
        from server.logic.llm_client import LLMClient
        self.llm_client = LLMClient()
        self.llm_client.hydrate()
        
        logger.info("====================================================")
        logger.info("🚀 QUANTUM ASYNCHRONOUS DAEMON WORKER IS ACTIVE")
        logger.info("Listening on queue: 'quantum_tasks'")
        logger.info("Dead Letter Queue (DLQ): 'quantum_dlq'")
        logger.info("GUI dependencies (PySide6/Qt): NONE (Fully Decoupled)")
        logger.info("====================================================")

        self._run_loop()

    def _run_loop(self):
        """Infinite blocking poll loop."""
        while True:
            try:
                # Dequeue FIFO task block (blocks up to 2 seconds if empty)
                task = self.queue_broker.dequeue("quantum_tasks", timeout=2)
                if not task:
                    continue
                
                job_id = task.get("job_id", "unknown")
                task_type = task.get("task_type", "unknown")
                logger.info(f"Picked up job '{job_id}' (Type: '{task_type}')")
                
                # Execute task
                success = self._execute_task(task)
                
                if success:
                    logger.info(f"✅ Job '{job_id}' successfully completed.")
                else:
                    self._handle_task_failure(task, "Task execution failed without unhandled exception")
                    
            except KeyboardInterrupt:
                logger.info("Termination signal received. Shutting down daemon gracefully...")
                break
            except Exception as e:
                logger.error(f"Error inside daemon run loop: {str(e)}")
                time.sleep(1.0)
                
        # Graceful cleanup
        ServiceRegistry.shutdown_all()
        logger.info("Daemon shutdown completed. Goodbye.")

    def _execute_task(self, task: dict) -> bool:
        """Task routing matrix."""
        task_type = task.get("task_type")
        
        if task_type == "vector_index":
            return self._execute_vector_index(task)
        elif task_type == "compress_session":
            return self._execute_compress_session(task)
        else:
            logger.warning(f"Unknown task type received: '{task_type}'")
            return False

    def _execute_vector_index(self, task: dict) -> bool:
        """Handles background vector embeddings calculation and Qdrant indexing."""
        user_text = task.get("user_text", "").strip()
        assistant_text = task.get("assistant_text", "").strip()
        conversation_id = task.get("conversation_id")
        model_id = task.get("model_id")
        user_id = task.get("user_id", 1)

        if not user_text or not assistant_text:
            logger.warning("Aborting indexing: user_text or assistant_text is empty.")
            return False

        exchange_payload = f"User: {user_text}\nAssistant: {assistant_text}"
        
        embedding_svc = ServiceRegistry.get("embedding")
        provider = self.llm_client.get_current_provider()
        collection_name = f"global_history_{provider}"

        payload = {
            "conversation_id": conversation_id,
            "model_id": model_id,
            "timestamp": datetime.now().isoformat(),
            "user_query": user_text,
            "assistant_reply": assistant_text,
            "full_text": exchange_payload
        }

        success = embedding_svc.embed_and_index(
            tenant_id=str(user_id),
            collection_name=collection_name,
            text=exchange_payload,
            payload=payload,
            client_instance=self.llm_client
        )
        return success

    def _execute_compress_session(self, task: dict) -> bool:
        """Runs the distributed memory session compression engine."""
        session_id = task.get("session_id")
        context_limit = task.get("context_limit", 4000)
        user_id = task.get("user_id", 1)

        if not session_id:
            logger.warning("Aborting session compression: session_id is missing.")
            return False

        try:
            memory_svc = ServiceRegistry.get("short_term_memory")
            messages = memory_svc.get_session(session_id)
            if not messages:
                logger.info(f"Session {session_id} is empty. Skipping compression.")
                return True

            total_chars = sum(len(m.get("content", "")) for m in messages)
            approx_tokens = int(total_chars / 4)

            trigger_limit = int(context_limit * 0.8)
            if approx_tokens < trigger_limit:
                logger.info(f"Session {session_id} usage ({approx_tokens} tokens) is below compression threshold ({trigger_limit} tokens). Skipping.")
                return True

            logger.info(f"⚡ Session {session_id} usage ({approx_tokens} tokens) crossed 80% ceiling ({trigger_limit} tokens). Running compression...")

            split_idx = int(len(messages) * 0.6)
            if split_idx == 0:
                split_idx = 1

            old_messages = messages[:split_idx]
            remaining_messages = messages[split_idx:]

            serialized_old = "\n".join(f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in old_messages)
            summary_prompt = f"Please provide a highly consolidated, extremely brief bulleted summary of this conversation segment, capturing only key facts and names for system memory retrieval:\n\n{serialized_old}"

            summary_text = self.llm_client._run_completion_internal(
                system_msg="You are an autonomous memory consolidation worker daemon. Summarize dialogue segments accurately and briefly.",
                user_msg=summary_prompt,
                max_tokens=500,
                temperature=0.3
            )

            if not summary_text or not summary_text.strip():
                raise RuntimeError("LLM returned empty session summary block")

            logger.info(f"Successfully generated memory summary segment ({len(summary_text)} chars).")

            from web.core.tenant_db import TenantDatabaseManager
            db_mgr = TenantDatabaseManager()
            summary_hash = hashlib.sha256(summary_text.encode('utf-8')).hexdigest()
            db_mgr.set_cached_embedding(summary_hash, user_id, f"Summary Segment of Session {session_id}", [0.0] * 384)

            compressed_context = f"Compressed memory of previous dialogue: {summary_text.strip()}"
            new_messages = [{"role": "system", "content": compressed_context}] + remaining_messages

            success = memory_svc.save_session(session_id, new_messages)
            if success:
                logger.info(f"Successfully compressed and consolidated Session {session_id}. New size: {len(new_messages)} messages.")
            return success

        except Exception as e:
            logger.error(f"Error executing session compression: {str(e)}")
            return False

    def _handle_task_failure(self, task: dict, error_msg: str):
        """Processes task failures with exponential backoffs and shifts to DLQ upon exhaust."""
        job_id = task.get("job_id", "unknown")
        retry_count = task.get("retry_count", 0) + 1
        task["retry_count"] = retry_count
        task["error_message"] = error_msg
        
        max_retries = 3
        if retry_count <= max_retries:
            backoff_delay = 2 ** retry_count
            logger.warning(f"⚠️ Job '{job_id}' failed: {error_msg}. Retrying {retry_count}/{max_retries} in {backoff_delay} seconds...")
            
            # Re-enqueue after sleeping (in a blocking manner for simplicity of single-worker model, 
            # or push back to queue immediately so delay happens on pickup)
            time.sleep(backoff_delay)
            self.queue_broker.enqueue("quantum_tasks", task)
        else:
            logger.error(f"❌ Job '{job_id}' completely failed after {max_retries} retries. Shifting to Dead Letter Queue (DLQ).")
            # Push payload to DLQ for admin inspection
            task["failed_at"] = time.time()
            self.queue_broker.enqueue("quantum_dlq", task)


if __name__ == "__main__":
    worker = AsyncWorker()
    worker.start()
