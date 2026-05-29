# logic/services/queue_broker.py

import json
import uuid
import logging
import threading
import time
from collections import deque
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumQueueBroker")

class RedisQueueBroker(BaseService):
    """
    Decoupled job queue broker mapping to Redis Lists (LPUSH/BRPOP),
    with automatic thread-safe collections.deque fallbacks for offline standalone modes.
    """
    def __init__(self):
        super().__init__()
        self.redis_svc = None
        self.client = None
        
        # Local mock stores for offline fallback
        self._mock_queues = {} # { queue_name: deque }
        self._mock_cvs = {}    # { queue_name: Condition }
        self._mock_lock = threading.Lock()

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Queue Broker Service...")
        try:
            self.redis_svc = ServiceRegistry.get("redis")
            self.client = self.redis_svc.get_client()
            logger.info("Queue Broker bound to central Redis Client manager.")
        except Exception as e:
            logger.error(f"Queue Broker service binding failed: {str(e)}")
            return False
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Queue Broker Service...")
        with self._mock_lock:
            self._mock_queues.clear()
            self._mock_cvs.clear()
        self.client = None
        self.redis_svc = None
        return True

    def _get_mock_queue_resources(self, queue_name: str):
        """Thread-safe acquisition of mock queue resources."""
        with self._mock_lock:
            if queue_name not in self._mock_queues:
                self._mock_queues[queue_name] = deque()
                self._mock_cvs[queue_name] = threading.Condition(self._mock_lock)
            return self._mock_queues[queue_name], self._mock_cvs[queue_name]

    def enqueue(self, queue_name: str, task_payload: dict) -> str:
        """
        Pushes a task payload to the tail of the target queue (LPUSH equivalent).
        Generates and injects a unique Job ID.
        """
        if not self.is_initialized or not self.client:
            logger.warning("Queue Broker not initialized. Suppressing enqueue call.")
            return None

        # Inject or reuse Job ID
        job_id = task_payload.get("job_id")
        if not job_id:
            job_id = f"job-{uuid.uuid4().hex}"
            task_payload["job_id"] = job_id
            
        if "created_at" not in task_payload:
            task_payload["created_at"] = time.time()
        
        # Fallback diagnostics check
        if self.redis_svc and not self.redis_svc.is_live():
            # Mock / Standalone mode
            q, cv = self._get_mock_queue_resources(queue_name)
            with self._mock_lock:
                q.append(task_payload)
                cv.notify_all()
            logger.debug(f"[Mock Queue] Enqueued job '{job_id}' on queue '{queue_name}'")
            return job_id

        try:
            payload_str = json.dumps(task_payload)
            # Standard Redis LPUSH (pushing left)
            self.client.lpush(queue_name, payload_str)
            logger.debug(f"[Redis Queue] Enqueued job '{job_id}' on queue '{queue_name}'")
            return job_id
        except Exception as e:
            logger.error(f"Failed to enqueue job on Redis list '{queue_name}': {str(e)}. Falling back to in-memory deque.")
            # Critical fallback on live connection drop
            q, cv = self._get_mock_queue_resources(queue_name)
            with self._mock_lock:
                q.append(task_payload)
                cv.notify_all()
            return job_id

    def dequeue(self, queue_name: str, timeout: int = 2) -> dict:
        """
        Blocks and retrieves a task from the head of the target queue (BRPOP equivalent).
        Returns None if timeout expires before a task is available.
        """
        if not self.is_initialized or not self.client:
            return None

        # Fallback diagnostics check
        if self.redis_svc and not self.redis_svc.is_live():
            # Mock / Standalone mode
            q, cv = self._get_mock_queue_resources(queue_name)
            with self._mock_lock:
                start_time = time.time()
                while not q:
                    elapsed = time.time() - start_time
                    remaining = float(timeout) - elapsed
                    if remaining <= 0:
                        return None
                    if not cv.wait(timeout=remaining):
                        return None
                return q.popleft() # Pop first in (FIFO)

        try:
            # Standard Redis BRPOP (blocks and pops right, representing left-to-right FIFO)
            # Returns tuple: (list_key, value)
            result = self.client.brpop(queue_name, timeout=timeout)
            if result:
                list_key, payload_str = result
                data_str = payload_str.decode('utf-8') if isinstance(payload_str, bytes) else str(payload_str)
                return json.loads(data_str)
            return None
        except Exception as e:
            logger.error(f"Redis BRPOP execution failed on '{queue_name}': {str(e)}. Swapping to in-memory lookup.")
            # Graceful fallback lookup on connection drops
            q, cv = self._get_mock_queue_resources(queue_name)
            with self._mock_lock:
                if q:
                    return q.popleft()
            return None

    def get_queue_length(self, queue_name: str) -> int:
        """Returns the current number of pending items in the target queue."""
        if not self.is_initialized or not self.client:
            return 0

        # Fallback diagnostics check
        if self.redis_svc and not self.redis_svc.is_live():
            q, cv = self._get_mock_queue_resources(queue_name)
            with self._mock_lock:
                return len(q)

        try:
            return int(self.client.llen(queue_name))
        except Exception as e:
            logger.error(f"Failed to query Redis llen for '{queue_name}': {str(e)}")
            q, cv = self._get_mock_queue_resources(queue_name)
            with self._mock_lock:
                return len(q)


# Auto-register RedisQueueBroker
ServiceRegistry.register("queue_broker", RedisQueueBroker())
