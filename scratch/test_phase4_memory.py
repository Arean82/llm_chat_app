# scratch/test_phase4_memory.py
"""Test suite for Phase 4 memory compression and short-term memory service.

This test verifies:
1. ShortTermMemoryService can store and retrieve a session.
2. The AsyncWorker's compress_session task correctly compresses a large session
   by summarizing the oldest messages and replacing them with a single system
   message, while preserving the remaining recent messages.
"""

import unittest
import random
import string

# Ensure the workspace root is on the import path
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.services.short_term_memory import ShortTermMemoryService
from logic.services.base_service import ServiceRegistry
from workers.async_worker import AsyncWorker


class TestPhase4Memory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize all services (Redis, queue broker, etc.)
        ServiceRegistry.initialize_all()
        # Ensure short term memory service is initialized
        cls.memory_svc: ShortTermMemoryService = ServiceRegistry.get("short_term_memory")
        assert cls.memory_svc.is_initialized
        # Create an AsyncWorker instance (no need to start the daemon loop)
        cls.worker = AsyncWorker()
        # Hydrate LLM client inside worker (required for summary generation)
        from logic.llm_client import get_mock_llm_client
        cls.worker.llm_client = get_mock_llm_client()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def generate_dummy_message(self, idx: int) -> dict:
        # Generate a deterministic random string of ~600 characters
        random.seed(idx)
        content = "".join(random.choices(string.ascii_letters + string.digits + " ", k=600))
        role = "assistant" if idx % 2 == 0 else "user"
        return {"role": role, "content": content}

    def test_compress_session_task(self):
        session_id = "test_session_001"
        # Build a session with enough characters to exceed the 80% token ceiling (4000 tokens => ~16000 chars)
        messages = [self.generate_dummy_message(i) for i in range(30)]  # ~30 * 600 = 18000 chars
        # Save the session via the service
        saved = self.memory_svc.save_session(session_id, messages, ttl=3600)
        self.assertTrue(saved, "Failed to save initial session")

        # Verify the session size before compression
        original_len = len(messages)
        self.assertEqual(original_len, 30)

        # Prepare a compress_session task dict
        task = {
            "job_id": "test_compress_001",
            "task_type": "compress_session",
            "session_id": session_id,
            "context_limit": 4000,
            "user_id": 1
        }

        # Execute compression directly via the worker (bypassing the queue loop for deterministic testing)
        result = self.worker._execute_compress_session(task)
        self.assertTrue(result, "Compression task reported failure")

        # Retrieve the updated session
        compressed_messages = self.memory_svc.get_session(session_id)
        self.assertIsInstance(compressed_messages, list)
        # The new session should have fewer messages than the original because the oldest 60% are collapsed
        self.assertLess(len(compressed_messages), original_len)
        # The first message should be a system message containing the compression tag
        first_msg = compressed_messages[0]
        self.assertEqual(first_msg.get("role"), "system")
        self.assertIn("Compressed memory of previous dialogue", first_msg.get("content", ""))

        # Ensure that at least one of the original recent messages remain after compression
        # The last 40% of original messages should still appear in the tail of the list
        remaining_expected = messages[int(len(messages) * 0.6) :]
        self.assertEqual(compressed_messages[-len(remaining_expected) :], remaining_expected)


if __name__ == "__main__":
    unittest.main()
