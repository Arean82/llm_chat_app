# scratch/test_async_worker.py

import sys
import os
import time
import logging
import threading

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s"
)
logger = logging.getLogger("QuantumQueueTest")

from logic.services.base_service import ServiceRegistry

def test_enqueue_dequeue():
    logger.info("=== TEST 1: Enqueue and Dequeue (FIFO) ===")
    
    broker = ServiceRegistry.get("queue_broker")
    redis_svc = ServiceRegistry.get("redis")
    logger.info(f"Active Queue Implementation: {'LIVE REDIS/MEMURAI' if redis_svc.is_live() else 'OFFLINE MOCK QUEUE'}")
    
    # Clean previous records
    while broker.dequeue("test_queue", timeout=1):
        pass
        
    # Enqueue 3 tasks
    job_ids = []
    for i in range(1, 4):
        payload = {"task_type": "dummy", "index": i}
        job_id = broker.enqueue("test_queue", payload)
        job_ids.append(job_id)
        logger.info(f"Enqueued job {i}: {job_id}")
        
    assert broker.get_queue_length("test_queue") == 3, f"Expected length 3, got {broker.get_queue_length('test_queue')}"
    
    # Dequeue and verify FIFO order
    for i in range(1, 4):
        task = broker.dequeue("test_queue", timeout=2)
        assert task is not None, f"Expected task {i} to be dequeued, got None"
        assert task["index"] == i, f"Expected index {i}, got {task['index']}"
        assert task["job_id"] == job_ids[i-1], f"Expected job_id {job_ids[i-1]}, got {task['job_id']}"
        logger.info(f"Successfully dequeued job: {task['job_id']} (Index: {task['index']})")
        
    assert broker.get_queue_length("test_queue") == 0, f"Expected empty queue, got {broker.get_queue_length('test_queue')}"
    logger.info("✅ Test 1: Queue FIFO ordering and lengths PASSED.")


def test_worker_and_dlq_redirection():
    logger.info("=== TEST 2: Worker Failures & DLQ Redirection ===")
    
    broker = ServiceRegistry.get("queue_broker")
    
    # Clean DLQ
    while broker.dequeue("quantum_dlq", timeout=1):
        pass
        
    # Enqueue a bad task designed to crash
    bad_payload = {
        "task_type": "vector_index",
        "user_text": "", # Empty text will trigger a failure
        "assistant_text": "Hello assistant",
        "conversation_id": 999,
        "model_id": "test-model"
    }
    
    job_id = broker.enqueue("quantum_tasks", bad_payload)
    logger.info(f"Enqueued bad task: {job_id}")
    
    # Instantiate the worker in a separate thread so we can push tasks and watch it process
    from workers.async_worker import AsyncWorker
    worker = AsyncWorker()
    
    # Dynamically monkeypatch the worker's _run_loop to stop after processing/failing the task
    original_execute = worker._execute_task
    executed_events = []
    
    def mock_execute(task):
        executed_events.append(task)
        # Call original (which should fail because of empty user_text)
        return original_execute(task)
        
    worker._execute_task = mock_execute
    
    # Start the worker thread
    logger.info("Starting background worker thread...")
    worker_thread = threading.Thread(
        target=worker.start,
        name="MockDaemonWorker",
        daemon=True
    )
    worker_thread.start()
    
    # Wait for the worker to pick up, retry 3 times, and dump to DLQ
    # Backoff sequence: 2s -> 4s -> 8s (Total ~14s sleep inside worker)
    logger.info("Waiting for worker to process retries and push to DLQ (~10 seconds)...")
    time.sleep(12)
    
    # Stop the worker thread by checking the queue length of DLQ
    dlq_task = broker.dequeue("quantum_dlq", timeout=3)
    
    assert dlq_task is not None, "Expected task to be redirected to Dead Letter Queue (DLQ), got None"
    assert dlq_task["job_id"] == job_id, f"Expected DLQ job_id '{job_id}', got '{dlq_task['job_id']}'"
    assert dlq_task.get("retry_count") is not None and dlq_task["retry_count"] > 3, f"Expected >3 retries, got {dlq_task.get('retry_count')}"
    logger.info(f"Successfully recovered failed task from DLQ: {dlq_task['job_id']}")
    logger.info(f"Diagnostics error logged in DLQ: '{dlq_task.get('error_message')}'")
    
    logger.info("✅ Test 2: Asynchronous Worker and DLQ routing PASSED.")


def main():
    logger.info("Starting Phase 2 Asynchronous Workers Integration Tests...")
    
    # Initialize all services
    ServiceRegistry.initialize_all()
    
    try:
        test_enqueue_dequeue()
        test_worker_and_dlq_redirection()
        
        # Shutdown
        ServiceRegistry.shutdown_all()
        logger.info("\n🏆 ALL PHASE 2 INTEGRATION TESTS PASSED SUCCESSFULLY!")
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        # Attempt cleanup
        try:
            ServiceRegistry.shutdown_all()
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
