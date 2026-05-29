# logic/agents/base_agent.py
import logging
import uuid
from typing import Optional

from server.logic.agents.agent_state_store import AgentStateStore
from server.logic.services.base_service import ServiceRegistry

logger = logging.getLogger("QuantumBaseAgent")

class BaseAgent:
    """
    Abstract Base Agent providing state persistence, lifecycle management,
    and a unified execution interface for autonomous agents.
    """
    def __init__(self, agent_id: Optional[str] = None, llm_client=None):
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.llm_client = llm_client
        self.state_store = None
        
        try:
            redis_svc = ServiceRegistry.get("redis")
            self.state_store = AgentStateStore(redis_svc)
        except Exception:
            logger.warning("Redis service not found. State persistence disabled.")

    def run(self, task_payload: dict) -> dict:
        """
        Main execution loop. Must be implemented by subclasses.
        Args:
            task_payload: Dict containing the task context and instructions.
        Returns:
            Dict containing the execution results and status.
        """
        raise NotImplementedError("Subclasses must implement run()")

    def save_checkpoint(self, checkpoint_data: dict):
        """Saves current state for pause/resume capabilities."""
        if self.state_store:
            self.state_store.save_state(self.agent_id, checkpoint_data)
            logger.debug(f"Agent {self.agent_id} saved checkpoint.")

    def load_checkpoint(self) -> Optional[dict]:
        """Loads previous state."""
        if self.state_store:
            return self.state_store.load_state(self.agent_id)
        return None
