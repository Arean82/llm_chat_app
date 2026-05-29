# scratch/test_phases_1_to_4.py
"""
Comprehensive regression test covering Phases 1 through 4 of the V9 Enterprise architecture.

Phase 1: Redis Message Broker & Infrastructure Overlay
  - Redis client (mock fallback), Event Bus pub/sub, ServiceRegistry lifecycle

Phase 2: Distributed Job Queueing & Asynchronous Workers
  - RedisQueueBroker enqueue/dequeue, DLQ retry handling

Phase 3: Cognitive Routing & API Gateway Integration
  - Rate Limiter, Security Service, Cognitive Router availability

Phase 4: Distributed Memory Architecture
  - ShortTermMemory store/retrieve/append/clear, EmbeddingService init,
    Compression Engine (AsyncWorker compress_session)
"""

import unittest
import json
import threading
import time
import random
import string
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.services.base_service import ServiceRegistry


class TestPhase1_RedisAndEventBus(unittest.TestCase):
    """Phase 1: Redis Central Nervous System & Event Bus."""

    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_1_1_redis_manager_initializes(self):
        """1.1.1 – Redis client interfacing: service registers and initializes."""
        redis_svc = ServiceRegistry.get("redis")
        self.assertTrue(redis_svc.is_initialized, "Redis manager should be initialized")
        client = redis_svc.get_client()
        self.assertIsNotNone(client)
        self.assertTrue(client.ping(), "Redis client (or mock) should respond to ping")

    def test_1_2_redis_set_get_delete(self):
        """1.1.1 – Basic Redis operations work (set/get/delete)."""
        client = ServiceRegistry.get("redis").get_client()
        client.set("test_key_ph1", "hello_v9")
        val = client.get("test_key_ph1")
        if isinstance(val, bytes):
            val = val.decode("utf-8")
        self.assertEqual(val, "hello_v9")
        client.delete("test_key_ph1")
        self.assertIsNone(client.get("test_key_ph1"))

    def test_1_3_event_bus_initializes(self):
        """1.1.2 – Event Bus abstraction: service registers and initializes."""
        event_bus = ServiceRegistry.get("event_bus")
        self.assertTrue(event_bus.is_initialized, "Event Bus should be initialized")

    def test_1_4_event_bus_pub_sub(self):
        """1.1.3 – Pub/Sub: publish fires callback on subscriber."""
        event_bus = ServiceRegistry.get("event_bus")
        received = []

        def callback(payload):
            received.append(payload)

        event_bus.subscribe("test_channel", callback)
        event_bus.publish("test_channel", {"action": "test", "value": 42})

        # Allow event dispatch (mock is async via thread)
        time.sleep(0.5)
        event_bus.unsubscribe("test_channel", callback)

        self.assertTrue(len(received) >= 1, "Subscriber should receive at least one event")
        self.assertEqual(received[0].get("action"), "test")

    def test_1_5_redis_ttl_expiry(self):
        """1.1.4 – Redis TTL: keys expire after the set duration."""
        client = ServiceRegistry.get("redis").get_client()
        client.set("ttl_test_key", "expires_soon", ex=1)
        val = client.get("ttl_test_key")
        self.assertIsNotNone(val, "Key should exist immediately after set")
        time.sleep(1.5)
        val = client.get("ttl_test_key")
        self.assertIsNone(val, "Key should have expired after TTL")


class TestPhase2_JobQueueing(unittest.TestCase):
    """Phase 2: Distributed Job Queueing & Asynchronous Workers."""

    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_2_1_queue_broker_initializes(self):
        """2.1.1 – Queue Broker Engine: service registers and initializes."""
        broker = ServiceRegistry.get("queue_broker")
        self.assertTrue(broker.is_initialized, "Queue Broker should be initialized")

    def test_2_2_enqueue_dequeue(self):
        """2.1.2 – Enqueue and dequeue a task payload (FIFO order)."""
        broker = ServiceRegistry.get("queue_broker")
        task_a = {"task_type": "embed", "text": "hello world"}
        task_b = {"task_type": "index", "text": "second task"}
        broker.enqueue("test_queue_ph2", task_a)
        broker.enqueue("test_queue_ph2", task_b)

        result_a = broker.dequeue("test_queue_ph2", timeout=2)
        self.assertIsNotNone(result_a, "First dequeue should return a task")
        self.assertEqual(result_a.get("task_type"), "embed")

        result_b = broker.dequeue("test_queue_ph2", timeout=2)
        self.assertIsNotNone(result_b, "Second dequeue should return a task")
        self.assertEqual(result_b.get("task_type"), "index")

    def test_2_3_queue_length(self):
        """2.1.2 – Queue length reflects enqueued items."""
        broker = ServiceRegistry.get("queue_broker")
        q_name = "test_queue_len"
        broker.enqueue(q_name, {"task_type": "a"})
        broker.enqueue(q_name, {"task_type": "b"})
        length = broker.get_queue_length(q_name)
        self.assertEqual(length, 2)
        # Drain
        broker.dequeue(q_name, timeout=1)
        broker.dequeue(q_name, timeout=1)
        self.assertEqual(broker.get_queue_length(q_name), 0)

    def test_2_4_dequeue_timeout_returns_none(self):
        """2.1.3 – DLQ: dequeue on empty queue times out and returns None."""
        broker = ServiceRegistry.get("queue_broker")
        result = broker.dequeue("empty_queue_ph2", timeout=1)
        self.assertIsNone(result, "Dequeue on empty queue should return None after timeout")


class TestPhase3_CognitiveRouting(unittest.TestCase):
    """Phase 3: Cognitive Routing & API Gateway Integration."""

    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_3_1_rate_limiter_initializes(self):
        """3.1.1.b – Rate Limiter: service registers and initializes."""
        rate_limiter = ServiceRegistry.get("rate_limiter")
        self.assertTrue(rate_limiter.is_initialized, "Rate Limiter should be initialized")

    def test_3_2_security_service_initializes(self):
        """3.1.2.a – Security Service: service registers and initializes."""
        security = ServiceRegistry.get("security")
        self.assertTrue(security.is_initialized, "Security Service should be initialized")

    def test_3_3_cognitive_router_initializes(self):
        """3.2.1.a – Cognitive Router: service registers and initializes."""
        router = ServiceRegistry.get("cognitive_router")
        self.assertTrue(router.is_initialized, "Cognitive Router should be initialized")


class TestPhase4_DistributedMemory(unittest.TestCase):
    """Phase 4: Distributed Memory Architecture."""

    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()
        cls.memory_svc = ServiceRegistry.get("short_term_memory")

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_4_1_short_term_memory_initializes(self):
        """4.1.1 – ShortTermMemory service registers and initializes."""
        self.assertTrue(self.memory_svc.is_initialized, "Short-Term Memory should be initialized")

    def test_4_2_save_and_retrieve_session(self):
        """4.1.1 – Save and retrieve a session from Redis-backed store."""
        session_id = "ph4_test_session"
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        saved = self.memory_svc.save_session(session_id, messages, ttl=60)
        self.assertTrue(saved)

        retrieved = self.memory_svc.get_session(session_id)
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0]["content"], "Hello")
        self.memory_svc.clear_session(session_id)

    def test_4_3_append_to_session(self):
        """4.1.1 – Append a message to an existing session."""
        session_id = "ph4_append_test"
        self.memory_svc.save_session(session_id, [{"role": "user", "content": "First"}], ttl=60)
        self.memory_svc.append_to_session(session_id, {"role": "assistant", "content": "Second"}, ttl=60)
        retrieved = self.memory_svc.get_session(session_id)
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[1]["content"], "Second")
        self.memory_svc.clear_session(session_id)

    def test_4_4_clear_session(self):
        """4.1.1 – Clearing a session removes it from the store."""
        session_id = "ph4_clear_test"
        self.memory_svc.save_session(session_id, [{"role": "user", "content": "Temp"}], ttl=60)
        self.memory_svc.clear_session(session_id)
        retrieved = self.memory_svc.get_session(session_id)
        self.assertEqual(retrieved, [])

    def test_4_5_embedding_service_initializes(self):
        """4.1.2 – EmbeddingService registers and initializes (decoupled from UI)."""
        embedding_svc = ServiceRegistry.get("embedding")
        self.assertTrue(embedding_svc.is_initialized, "Embedding Service should be initialized")

    def test_4_6_compression_engine(self):
        """4.1.3 – Compression Engine: large session is compressed via AsyncWorker."""
        from workers.async_worker import AsyncWorker
        from logic.llm_client import get_mock_llm_client

        worker = AsyncWorker()
        worker.llm_client = get_mock_llm_client()

        session_id = "ph4_compress_test"
        # Build a session with ~18000 chars to exceed 80% of 4000 token ceiling
        random.seed(99)
        messages = []
        for i in range(30):
            content = "".join(random.choices(string.ascii_letters + string.digits + " ", k=600))
            role = "assistant" if i % 2 == 0 else "user"
            messages.append({"role": role, "content": content})

        self.memory_svc.save_session(session_id, messages, ttl=3600)
        original_len = len(messages)

        task = {
            "job_id": "test_compress_ph4",
            "task_type": "compress_session",
            "session_id": session_id,
            "context_limit": 4000,
            "user_id": 1,
        }
        result = worker._execute_compress_session(task)
        self.assertTrue(result, "Compression task should succeed")

        compressed = self.memory_svc.get_session(session_id)
        self.assertIsInstance(compressed, list)
        self.assertLess(len(compressed), original_len, "Compressed session should have fewer messages")
        self.assertEqual(compressed[0]["role"], "system")
        self.assertIn("Compressed memory", compressed[0]["content"])
        self.memory_svc.clear_session(session_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
