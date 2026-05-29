# scratch/test_phase_5_2.py
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.services.base_service import ServiceRegistry
from logic.agents import ResearchAgent, CodingAgent, ReviewAgent, WorkflowEngine, PlanStep

class TestPhase5_2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_research_agent(self):
        agent = ResearchAgent(agent_id="test-research")
        result = agent.run({"topic": "python async loops"})
        self.assertTrue(result["success"])
        self.assertIn("report", result)
        self.assertIn("MOCK SEARCH RESULTS", result["report"])

    def test_coding_agent(self):
        # We don't have LLM hooked up in tests, it will fall back to dummy string.
        agent = CodingAgent(agent_id="test-coding")
        result = agent.run({"instruction": "print('Hello CodingAgent')"})
        self.assertTrue(result["success"])
        self.assertIn("code", result)
        self.assertIn("CodingAgent executed dummy script successfully.", result["stdout"])
        self.assertEqual(result["return_code"], 0)

    def test_review_agent(self):
        agent = ReviewAgent(agent_id="test-review")
        # Should pass
        result_pass = agent.run({"code": "print('ok')", "execution_output": "ok", "success_flag": True})
        self.assertTrue(result_pass["success"])
        self.assertTrue(result_pass["passed"])
        
        # Should fail due to BUG string in fallback logic
        result_fail = agent.run({"code": "print('bug')", "execution_output": "bug", "success_flag": True})
        self.assertTrue(result_fail["success"])
        self.assertFalse(result_fail["passed"])

    def test_workflow_engine(self):
        agents = {
            "research": ResearchAgent(agent_id="wf-res"),
            "code": CodingAgent(agent_id="wf-cod"),
            "review": ReviewAgent(agent_id="wf-rev")
        }
        engine = WorkflowEngine(agents)
        
        steps = [
            PlanStep(step_id="1", task_type="research", input_payload={"topic": "test topic"}),
            PlanStep(step_id="2", task_type="code", input_payload={"instruction": "write something"}),
            PlanStep(step_id="3", task_type="review", input_payload={})
        ]
        
        result = engine.execute_chain(steps, initial_context={})
        
        self.assertTrue(result["success"])
        context = result["context"]
        self.assertIn("report", context)
        self.assertIn("stdout", context)
        self.assertIn("passed", context)
        
if __name__ == "__main__":
    unittest.main(verbosity=2)
