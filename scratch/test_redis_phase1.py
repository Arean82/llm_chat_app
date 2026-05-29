# scratch/test_redis_phase1.py

import sys
import os
import time
import threading
import logging

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s"
)
logger = logging.getLogger("QuantumRedisTest")

from server.logic.services.base_service import ServiceRegistry
from server.utils.path_utils import get_app_settings

def test_connection_pool_and_thread_safety():
    logger.info("=== TEST 1: Thread-Safe Redis Connection Pool ===")
    
    redis_svc = ServiceRegistry.get("redis")
    client = redis_svc.get_client()
    
    logger.info(f"Active Client Implementation: {'LIVE REDIS/MEMURAI' if redis_svc.is_live() else 'OFFLINE MOCK REDIS'}")
    
    # 1. Simple Set and Get
    client.set("test_phase1_key", "QuantumV9Rulez", ex=5)
    val = client.get("test_phase1_key")
    decoded_val = val.decode('utf-8') if isinstance(val, bytes) else str(val)
    logger.info(f"Simple write/read: Key 'test_phase1_key' -> '{decoded_val}'")
    assert decoded_val == "QuantumV9Rulez", f"Expected 'QuantumV9Rulez', got '{decoded_val}'"
    
    # 2. Multi-threaded Safety Test
    errors = []
    def worker(worker_id):
        try:
            worker_client = redis_svc.get_client()
            key = f"thread_key_{worker_id}"
            val_to_set = f"val_from_{worker_id}"
            
            # Write
            worker_client.set(key, val_to_set, ex=5)
            time.sleep(0.1) # Simulate dynamic load
            
            # Read
            read_val = worker_client.get(key)
            decoded = read_val.decode('utf-8') if isinstance(read_val, bytes) else str(read_val)
            
            if decoded != val_to_set:
                errors.append(f"Worker {worker_id} read wrong value. Expected '{val_to_set}', got '{decoded}'")
        except Exception as e:
            errors.append(f"Worker {worker_id} crashed: {str(e)}")

    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,), name=f"RedisWorker-{i}")
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if errors:
        for err in errors:
            logger.error(err)
        raise AssertionError("Multi-threaded safety checks failed!")
        
    logger.info("✅ Test 1: Thread-Safety and connection pool operations PASSED.")


def test_event_bus_pubsub():
    logger.info("=== TEST 2: Pub/Sub Event Bus Abstraction ===")
    
    event_bus = ServiceRegistry.get("event_bus")
    
    received_messages = []
    event_received = threading.Event()
    
    def on_model_changed_event(payload):
        logger.info(f"Subscriber received event on 'ModelChanged': {payload}")
        received_messages.append(payload)
        event_received.set()
        
    # Subscribe to channel
    event_bus.subscribe("ModelChanged", on_model_changed_event)
    
    # Wait for listener thread to establish
    time.sleep(0.5)
    
    # Publish event
    test_payload = {
        "event_type": "ModelChanged",
        "sender": "test_script",
        "model_id": "claude-3-5-sonnet",
        "timestamp": time.time()
    }
    
    event_bus.publish("ModelChanged", test_payload)
    
    # Wait for receipt
    if not event_received.wait(timeout=3.0):
        raise AssertionError("Timed out waiting for Pub/Sub event delivery!")
        
    # Assertions
    assert len(received_messages) == 1, "Expected 1 message payload"
    delivered = received_messages[0]
    assert delivered.get("model_id") == "claude-3-5-sonnet", "Payload data corrupted"
    
    # Clean up subscription
    event_bus.unsubscribe("ModelChanged", on_model_changed_event)
    logger.info("✅ Test 2: Event Bus Pub/Sub delivery PASSED.")


def main():
    logger.info("Starting Phase 1 Automated Verification...")
    
    # Setup App Settings to force enabled/disabled states for verification
    settings = get_app_settings()
    
    # Check if a live Redis is present by default
    logger.info("--- Initializing Services ---")
    ServiceRegistry.initialize_all()
    
    try:
        # Run test suites with whatever connection profile was hydrated
        test_connection_pool_and_thread_safety()
        test_event_bus_pubsub()
        
        # Shutdown
        ServiceRegistry.shutdown_all()
        
        logger.info("\n🏆 ALL PHASE 1 INTEGRATION TESTS PASSED SUCCESSFULLY!")
        
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
