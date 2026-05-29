import os
import json
import time
import logging
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from server.logic.services.base_service import ServiceRegistry

logger = logging.getLogger("QuantumJobQueue")

class JobQueueEngine:
    """
    In-memory background job queue engine with persistent thread worker pooling.
    Handles decoupled slow background tasks (e.g. document indexing, vector embeddings creation)
    and manages a localized Dead Letter Queue (DLQ) for failed operations.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(JobQueueEngine, cls).__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # In-memory queues & worker pool
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="QuantumWorker")
        self.active_jobs = {} # Job ID -> status dict
        self.completed_jobs = {}
        
        # Dead Letter Queue storage path
        from server.utils.storage_config import StorageManager
        self.dlq_path = StorageManager.get_instance().get_storage_root() / "data" / "dlq.json"
        self.dlq_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize DLQ file if not exists
        if not self.dlq_path.exists():
            self._write_dlq([])

    def _read_dlq(self) -> list:
        try:
            if self.dlq_path.exists():
                with open(self.dlq_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read DLQ from disk: {str(e)}")
        return []

    def _write_dlq(self, dlq_list: list) -> None:
        try:
            with open(self.dlq_path, "w", encoding="utf-8") as f:
                json.dump(dlq_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to write DLQ to disk: {str(e)}")

    def get_dlq_entries(self) -> list:
        """Expose list of all dead letter items."""
        return self._read_dlq()

    def add_to_dlq(self, tenant_id: str, task_type: str, payload: dict, error_msg: str, stack_trace: str) -> None:
        """Serializes failed background tasks to dlq.json."""
        with self._lock:
            dlq = self._read_dlq()
            dlq_entry = {
                "job_id": f"dlq_{int(time.time())}_{len(dlq)}",
                "tenant_id": tenant_id,
                "task_type": task_type,
                "payload": payload,
                "timestamp": datetime_str(),
                "error": error_msg,
                "stack_trace": stack_trace,
                "retry_count": payload.get("retry_count", 0)
            }
            dlq.append(dlq_entry)
            self._write_dlq(dlq)
            logger.info(f"Task serialized to Dead Letter Queue (DLQ): {dlq_entry['job_id']}")

    def remove_from_dlq(self, job_id: str) -> dict:
        """Removes a dead-letter item by job_id and returns it."""
        with self._lock:
            dlq = self._read_dlq()
            target_entry = None
            updated_dlq = []
            for entry in dlq:
                if entry.get("job_id") == job_id:
                    target_entry = entry
                else:
                    updated_dlq.append(entry)
            if target_entry:
                self._write_dlq(updated_dlq)
            return target_entry

    def submit_job(self, tenant_id: str, task_type: str, payload: dict) -> str:
        """Submits a task for background thread pool execution."""
        job_id = f"job_{int(time.time())}_{len(self.active_jobs) + 1}"
        
        self.active_jobs[job_id] = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "task_type": task_type,
            "status": "queued",
            "submitted_at": datetime_str()
        }

        # Submit task execution to executor pool
        self.executor.submit(self._execute_wrapper, job_id, tenant_id, task_type, payload)
        return job_id

    def _execute_wrapper(self, job_id: str, tenant_id: str, task_type: str, payload: dict) -> None:
        logger.info(f"Starting execution of {task_type} background task {job_id}")
        self.active_jobs[job_id]["status"] = "processing"
        self.active_jobs[job_id]["started_at"] = datetime_str()
        
        try:
            if task_type == "ingest_document":
                # Invoke RAGService ingestion dynamically
                rag_service = ServiceRegistry.get("rag")
                document_title = payload.get("title", "Unnamed Document")
                text_content = payload.get("text", "")
                
                # Run the expensive ingestion indexing pipeline
                result = rag_service.ingest_document(tenant_id, document_title, text_content)
                self._complete_job(job_id, "completed", result)
                
            else:
                raise NotImplementedError(f"Task type '{task_type}' is not supported.")
                
        except Exception as e:
            err_msg = str(e)
            stack = traceback.format_exc()
            logger.error(f"Background task {job_id} failed: {err_msg}\n{stack}")
            
            self._complete_job(job_id, "failed", {"error": err_msg})
            
            # Serialize failed background task to disk DLQ
            self.add_to_dlq(tenant_id, task_type, payload, err_msg, stack)

    def _complete_job(self, job_id: str, status: str, result: dict) -> None:
        if job_id in self.active_jobs:
            job_info = self.active_jobs.pop(job_id)
            job_info["status"] = status
            job_info["completed_at"] = datetime_str()
            job_info["result"] = result
            self.completed_jobs[job_id] = job_info

    def retry_dlq_job(self, job_id: str) -> str:
        """Pulls a failed job from DLQ and resubmits it to the background queue."""
        entry = self.remove_from_json(job_id)
        if not entry:
            raise KeyError(f"Dead letter item {job_id} not found.")

        tenant_id = entry["tenant_id"]
        task_type = entry["task_type"]
        payload = entry["payload"]
        
        # Increment retry attempt count
        payload["retry_count"] = entry.get("retry_count", 0) + 1
        
        logger.info(f"Retrying Dead Letter item {job_id} for tenant {tenant_id} (Attempt {payload['retry_count']})")
        return self.submit_job(tenant_id, task_type, payload)

    def remove_from_json(self, job_id: str) -> dict:
        """Pops element from json file. Shared utility."""
        return self.remove_from_dlq(job_id)

    def get_queue_status(self) -> dict:
        """Return real-time diagnostic counts of background execution queues."""
        return {
            "active_threads_count": len(self.active_jobs),
            "queued_jobs": [job for job in self.active_jobs.values() if job["status"] == "queued"],
            "processing_jobs": [job for job in self.active_jobs.values() if job["status"] == "processing"],
            "completed_count": len(self.completed_jobs),
            "dlq_count": len(self.get_dlq_entries())
        }

def datetime_str() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
