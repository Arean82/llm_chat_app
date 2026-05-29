# scratch/test_phases_1_to_5.py
"""
Comprehensive regression test: Phases 1 through 5.1 of V9 Enterprise.

Phase 1: Redis & Event Bus
Phase 2: Job Queueing
Phase 3: Cognitive Routing
Phase 4: Distributed Memory
Phase 5.1: Agent Runtime Environments
  - 5.1.a Logic Planner (decompose, topological order, serialize/deserialize)
  - 5.1.b Tool Execution Sandbox (safe execution, forbidden pattern rejection, timeout)
  - 5.1.c Redis Agent State Store (save/load/delete, pause/resume, field ops)
"""

import unittest
import json
import time
import random
import string
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.logic.services.base_service import ServiceRegistry


# ==================================================================== #
# Phase 1: Redis & Event Bus
# ==================================================================== #

class TestPhase1_RedisAndEventBus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_1_1_redis_manager_initializes(self):
        svc = ServiceRegistry.get("redis")
        self.assertTrue(svc.is_initialized)
        self.assertTrue(svc.get_client().ping())

    def test_1_2_redis_set_get_delete(self):
        c = ServiceRegistry.get("redis").get_client()
        c.set("k1", "v1")
        val = c.get("k1")
        if isinstance(val, bytes):
            val = val.decode()
        self.assertEqual(val, "v1")
        c.delete("k1")
        self.assertIsNone(c.get("k1"))

    def test_1_3_event_bus_pub_sub(self):
        bus = ServiceRegistry.get("event_bus")
        self.assertTrue(bus.is_initialized)
        received = []
        bus.subscribe("t_ch", lambda p: received.append(p))
        bus.publish("t_ch", {"x": 1})
        time.sleep(0.5)
        self.assertTrue(len(received) >= 1)

    def test_1_4_redis_ttl_expiry(self):
        c = ServiceRegistry.get("redis").get_client()
        c.set("ttl_k", "temp", ex=1)
        self.assertIsNotNone(c.get("ttl_k"))
        time.sleep(1.5)
        self.assertIsNone(c.get("ttl_k"))


# ==================================================================== #
# Phase 2: Job Queueing
# ==================================================================== #

class TestPhase2_JobQueueing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_2_1_broker_enqueue_dequeue(self):
        broker = ServiceRegistry.get("queue_broker")
        self.assertTrue(broker.is_initialized)
        broker.enqueue("q_ph2", {"task_type": "a"})
        broker.enqueue("q_ph2", {"task_type": "b"})
        r = broker.dequeue("q_ph2", timeout=2)
        self.assertEqual(r["task_type"], "a")
        r = broker.dequeue("q_ph2", timeout=2)
        self.assertEqual(r["task_type"], "b")

    def test_2_2_queue_length(self):
        broker = ServiceRegistry.get("queue_broker")
        broker.enqueue("q_len", {"t": 1})
        broker.enqueue("q_len", {"t": 2})
        self.assertEqual(broker.get_queue_length("q_len"), 2)
        broker.dequeue("q_len", timeout=1)
        broker.dequeue("q_len", timeout=1)

    def test_2_3_empty_dequeue_returns_none(self):
        broker = ServiceRegistry.get("queue_broker")
        self.assertIsNone(broker.dequeue("q_empty", timeout=1))


# ==================================================================== #
# Phase 3: Cognitive Routing
# ==================================================================== #

class TestPhase3_CognitiveRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_3_1_services_initialized(self):
        for name in ("rate_limiter", "security", "cognitive_router"):
            svc = ServiceRegistry.get(name)
            self.assertTrue(svc.is_initialized, f"{name} should be initialized")


# ==================================================================== #
# Phase 4: Distributed Memory
# ==================================================================== #

class TestPhase4_DistributedMemory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()
        cls.mem = ServiceRegistry.get("short_term_memory")

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_4_1_session_crud(self):
        sid = "ph4_crud"
        self.mem.save_session(sid, [{"role": "user", "content": "Hi"}], ttl=60)
        r = self.mem.get_session(sid)
        self.assertEqual(len(r), 1)
        self.mem.append_to_session(sid, {"role": "assistant", "content": "Hey"}, ttl=60)
        self.assertEqual(len(self.mem.get_session(sid)), 2)
        self.mem.clear_session(sid)
        self.assertEqual(self.mem.get_session(sid), [])

    def test_4_2_embedding_service(self):
        self.assertTrue(ServiceRegistry.get("embedding").is_initialized)

    def test_4_3_compression_engine(self):
        from server.workers.async_worker import AsyncWorker
        from server.logic.llm_client import get_mock_llm_client
        worker = AsyncWorker()
        worker.llm_client = get_mock_llm_client()
        sid = "ph4_comp"
        random.seed(42)
        msgs = [{"role": "user" if i % 2 else "assistant",
                 "content": "".join(random.choices(string.ascii_letters, k=600))} for i in range(30)]
        self.mem.save_session(sid, msgs, ttl=3600)
        result = worker._execute_compress_session({
            "job_id": "c1", "task_type": "compress_session",
            "session_id": sid, "context_limit": 4000, "user_id": 1,
        })
        self.assertTrue(result)
        compressed = self.mem.get_session(sid)
        self.assertLess(len(compressed), 30)
        self.assertIn("Compressed memory", compressed[0]["content"])
        self.mem.clear_session(sid)


# ==================================================================== #
# Phase 5.1: Agent Runtime Environments
# ==================================================================== #

class TestPhase5_1a_LogicPlanner(unittest.TestCase):
    """5.1.a — Logic Planner Module."""

    def test_planner_no_llm_fallback(self):
        """Without an LLM client the planner returns a single generic step."""
        from server.logic.agents.planner import AgentPlanner
        planner = AgentPlanner(llm_client=None)
        plan = planner.decompose("Build a REST API")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].task_type, "generic")
        self.assertIn("REST API", plan[0].description)

    def test_planner_with_mock_llm(self):
        """With a mock LLM the planner parses the decomposed JSON into steps."""
        from server.logic.agents.planner import AgentPlanner, PlanStep

        class MockLLMForPlanner:
            def _run_completion_internal(self, system_msg, user_msg, max_tokens, temperature, force_json=False):
                return json.dumps([
                    {"task_type": "research", "description": "Investigate auth patterns", "depends_on": []},
                    {"task_type": "code", "description": "Implement JWT middleware", "depends_on": [0]},
                    {"task_type": "review", "description": "Review code", "depends_on": [1]},
                ])

        planner = AgentPlanner(llm_client=MockLLMForPlanner())
        plan = planner.decompose("Build authenticated REST API")
        self.assertEqual(len(plan), 3)
        self.assertEqual(plan[0].task_type, "research")
        self.assertEqual(plan[1].task_type, "code")
        # Step 1 should depend on step 0
        self.assertIn(plan[0].step_id, plan[1].depends_on)

    def test_topological_order(self):
        """Execution order respects dependency graph."""
        from server.logic.agents.planner import AgentPlanner, PlanStep
        s0 = PlanStep(step_id="s0", task_type="research")
        s1 = PlanStep(step_id="s1", task_type="code", depends_on=["s0"])
        s2 = PlanStep(step_id="s2", task_type="review", depends_on=["s1"])

        planner = AgentPlanner()
        order = planner.get_execution_order([s2, s0, s1])  # scrambled input
        ids = [s.step_id for s in order]
        self.assertEqual(ids, ["s0", "s1", "s2"])

    def test_serialize_deserialize(self):
        """Plan round-trips through JSON serialization."""
        from server.logic.agents.planner import AgentPlanner, PlanStep
        steps = [
            PlanStep(step_id="a", task_type="code", description="write code"),
            PlanStep(step_id="b", task_type="review", depends_on=["a"]),
        ]
        planner = AgentPlanner()
        blob = planner.serialize_plan(steps)
        restored = AgentPlanner.deserialize_plan(blob)
        self.assertEqual(len(restored), 2)
        self.assertEqual(restored[0].step_id, "a")
        self.assertEqual(restored[1].depends_on, ["a"])

    def test_mark_step(self):
        from server.logic.agents.planner import AgentPlanner, PlanStep
        step = PlanStep(task_type="code")
        planner = AgentPlanner()
        planner.mark_step(step, "completed", output="done")
        self.assertEqual(step.status, "completed")
        self.assertEqual(step.output, "done")


class TestPhase5_1b_ToolSandbox(unittest.TestCase):
    """5.1.b — Tool Execution Sandbox."""

    def setUp(self):
        from server.logic.agents.sandbox import ToolExecutionSandbox
        self.sandbox = ToolExecutionSandbox()

    def test_safe_code_execution(self):
        result = self.sandbox.execute("print('hello from sandbox')")
        self.assertTrue(result.success)
        self.assertIn("hello from sandbox", result.stdout)
        self.assertEqual(result.return_code, 0)

    def test_forbidden_os_system(self):
        result = self.sandbox.execute("import os\nos.system('echo pwned')")
        self.assertFalse(result.success)
        self.assertIn("policy violation", result.error)

    def test_forbidden_subprocess(self):
        result = self.sandbox.execute("import subprocess\nsubprocess.run(['ls'])")
        self.assertFalse(result.success)
        self.assertIn("policy violation", result.error)

    def test_forbidden_eval(self):
        result = self.sandbox.execute("eval('1+1')")
        self.assertFalse(result.success)
        self.assertIn("policy violation", result.error)

    def test_syntax_error_returns_failure(self):
        result = self.sandbox.execute("def foo(:\n  pass")
        self.assertFalse(result.success)
        self.assertNotEqual(result.return_code, 0)

    def test_execution_captures_stderr(self):
        result = self.sandbox.execute("import sys\nsys.stderr.write('err msg')")
        self.assertIn("err msg", result.stderr)

    def test_execution_time_tracked(self):
        result = self.sandbox.execute("x = sum(range(1000))\nprint(x)")
        self.assertTrue(result.success)
        self.assertGreater(result.execution_time_ms, 0)


class TestPhase5_1c_AgentStateStore(unittest.TestCase):
    """5.1.c — Redis Agent State Store."""

    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()
        cls.redis_svc = ServiceRegistry.get("redis")

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def setUp(self):
        from server.logic.agents.agent_state_store import AgentStateStore
        self.store = AgentStateStore(self.redis_svc)

    def test_save_load_state(self):
        state = {"plan": [{"step": 1}], "current_step": 0}
        self.assertTrue(self.store.save_state("agent-001", state))
        loaded = self.store.load_state("agent-001")
        self.assertEqual(loaded["current_step"], 0)
        self.store.delete_state("agent-001")

    def test_delete_state(self):
        self.store.save_state("agent-del", {"x": 1})
        self.store.delete_state("agent-del")
        self.assertIsNone(self.store.load_state("agent-del"))

    def test_field_operations(self):
        self.store.set_field("agent-f", "status", "running")
        self.assertEqual(self.store.get_field("agent-f", "status"), "running")
        self.store.set_field("agent-f", "counter", 42)
        self.assertEqual(self.store.get_field("agent-f", "counter"), 42)
        # cleanup
        self.store.delete_state("agent-f")

    def test_pause_and_resume(self):
        plan_json = json.dumps([{"step_id": "s1", "task_type": "code"}])
        self.assertTrue(self.store.pause_agent("agent-pr", plan_json, current_step_idx=2))
        self.assertEqual(self.store.get_field("agent-pr", "status"), "paused")

        resumed = self.store.resume_agent("agent-pr")
        self.assertIsNotNone(resumed)
        self.assertIn("plan", resumed)
        self.assertIn("checkpoint", resumed)
        checkpoint = resumed["checkpoint"]
        self.assertEqual(checkpoint["step_index"], 2)
        self.assertEqual(self.store.get_field("agent-pr", "status"), "running")
        self.store.delete_state("agent-pr")

    def test_resume_non_paused_returns_none(self):
        self.store.set_field("agent-np", "status", "running")
        self.assertIsNone(self.store.resume_agent("agent-np"))
        self.store.delete_state("agent-np")

    def test_missing_state_returns_none(self):
        self.assertIsNone(self.store.load_state("agent-nonexistent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
