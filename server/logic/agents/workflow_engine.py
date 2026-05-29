# logic/agents/workflow_engine.py
import logging
from typing import Dict, Any, List

from server.logic.agents.planner import PlanStep

logger = logging.getLogger("QuantumWorkflowEngine")

class WorkflowEngine:
    """
    5.3.a — Deterministic Workflow Engine
    Executes predefined chains of agents using a shared context.
    """
    def __init__(self, agents: Dict[str, Any]):
        """
        Args:
            agents: Dictionary mapping agent types to agent instances.
                    e.g. {"research": ResearchAgent(...), "code": CodingAgent(...), ...}
        """
        self.agents = agents

    def execute_chain(self, steps: List[PlanStep], initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a sequence of steps passing context between them.
        Assumes steps are topologically sorted.
        """
        context = dict(initial_context)
        logger.info(f"Starting deterministic workflow chain with {len(steps)} steps.")

        for step in steps:
            logger.info(f"Executing step {step.step_id} ({step.task_type}) - {step.description}")
            agent = self.agents.get(step.task_type)
            
            if not agent:
                logger.error(f"No agent registered for task_type '{step.task_type}'. Failing step.")
                step.status = "failed"
                return {"success": False, "failed_step": step.step_id, "context": context}

            # Prepare payload for the agent, combining global context with step-specific inputs
            payload = dict(context)
            payload.update(step.input_payload)

            try:
                result = agent.run(payload)
                step.status = "completed" if result.get("success") else "failed"
                step.output = result
                
                # Merge the agent's output back into the global context for downstream agents
                context.update(result)
                
                if not result.get("success"):
                    logger.warning(f"Step {step.step_id} failed during execution.")
                    return {"success": False, "failed_step": step.step_id, "context": context}
                    
            except Exception as e:
                logger.error(f"Exception during step {step.step_id} execution: {e}")
                step.status = "failed"
                return {"success": False, "failed_step": step.step_id, "error": str(e), "context": context}

        logger.info("Workflow chain completed successfully.")
        return {"success": True, "context": context}
