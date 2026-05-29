# logic/agents/review_agent.py
import logging
from server.logic.agents.base_agent import BaseAgent

logger = logging.getLogger("QuantumReviewAgent")

class ReviewAgent(BaseAgent):
    """
    5.2.c — Review Agent
    Critiques code and outputs (from CodingAgent) for correctness and security,
    returning pass/fail metrics and detailed critique.
    """
    def __init__(self, agent_id=None, llm_client=None):
        super().__init__(agent_id, llm_client)

    def run(self, task_payload: dict) -> dict:
        code = task_payload.get("code", "")
        execution_output = task_payload.get("execution_output", "")
        success_flag = task_payload.get("success_flag", True)
        
        logger.info("ReviewAgent analyzing code and execution results...")
        
        self.save_checkpoint({"status": "reviewing"})
        
        if self.llm_client:
            sys_msg = (
                "You are an expert Security and Code Reviewer. "
                "Analyze the provided code and its execution output. "
                "Output ONLY a JSON object with two keys: "
                "'passed' (boolean indicating if the code is correct, secure, and bug-free), and "
                "'critique' (a detailed markdown string explaining the reasoning)."
            )
            prompt = f"Code:\n```python\n{code}\n```\n\nExecution Success: {success_flag}\nOutput:\n{execution_output}"
            
            try:
                raw_response = self.llm_client._run_completion_internal(
                    system_msg=sys_msg,
                    user_msg=prompt,
                    max_tokens=800,
                    temperature=0.1,
                    force_json=True
                )
                import json
                result = json.loads(raw_response)
                passed = result.get("passed", False)
                critique = result.get("critique", "No critique provided.")
            except Exception as e:
                logger.error(f"ReviewAgent LLM error: {e}")
                passed = False
                critique = f"Error during review: {e}"
        else:
            # Fallback logic for testing without LLM
            passed = success_flag
            critique = "Passed review." if success_flag else "Failed review due to execution error."
            if "BUG" in code.upper():
                passed = False
                critique = "Found bug in code."

        self.save_checkpoint({"status": "completed", "passed": passed})
        
        return {
            "success": True, # Agent ran successfully
            "agent_id": self.agent_id,
            "passed": passed,
            "critique": critique
        }
