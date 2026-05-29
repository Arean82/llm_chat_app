# logic/agents/coding_agent.py
import logging
from server.logic.agents.base_agent import BaseAgent
from server.logic.agents.sandbox import ToolExecutionSandbox

logger = logging.getLogger("QuantumCodingAgent")

class CodingAgent(BaseAgent):
    """
    5.2.b — Coding Agent
    Specialized agent with read/write access to the local sandbox file system 
    and python subprocess execution tools.
    """
    def __init__(self, agent_id=None, llm_client=None, workspace_dir=None):
        super().__init__(agent_id, llm_client)
        self.sandbox = ToolExecutionSandbox(workspace_dir=workspace_dir)

    def run(self, task_payload: dict) -> dict:
        instruction = task_payload.get("instruction", "")
        logger.info(f"CodingAgent processing instruction: {instruction[:50]}...")
        
        self.save_checkpoint({"status": "generating_code", "instruction": instruction})
        
        # 1. Generate code using LLM
        if self.llm_client:
            sys_msg = (
                "You are an expert autonomous software engineer. "
                "Write a complete, runnable Python script to satisfy the instruction. "
                "Output ONLY the python code inside ```python blocks. Do not include markdown or explanations outside the block."
            )
            try:
                raw_code = self.llm_client._run_completion_internal(
                    system_msg=sys_msg,
                    user_msg=instruction,
                    max_tokens=2000,
                    temperature=0.1
                )
                code = self._extract_code(raw_code)
            except Exception as e:
                logger.error(f"CodingAgent LLM error: {e}")
                return {"success": False, "error": str(e)}
        else:
            # Fallback code for testing without LLM
            code = "print('CodingAgent executed dummy script successfully.')"
            
        logger.debug(f"CodingAgent generated code:\n{code}")
        
        # 2. Execute code in sandbox
        self.save_checkpoint({"status": "executing_code"})
        sandbox_result = self.sandbox.execute(code)
        
        self.save_checkpoint({"status": "completed"})
        
        return {
            "success": sandbox_result.success,
            "agent_id": self.agent_id,
            "code": code,
            "stdout": sandbox_result.stdout,
            "stderr": sandbox_result.stderr,
            "return_code": sandbox_result.return_code,
            "error": sandbox_result.error,
            "execution_time_ms": sandbox_result.execution_time_ms
        }

    def _extract_code(self, raw: str) -> str:
        """Extracts python code from markdown code blocks."""
        if "```python" in raw:
            parts = raw.split("```python")
            if len(parts) > 1:
                return parts[1].split("```")[0].strip()
        elif "```" in raw:
            parts = raw.split("```")
            if len(parts) > 1:
                return parts[1].strip()
        return raw.strip()
