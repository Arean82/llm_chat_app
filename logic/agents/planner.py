# logic/agents/planner.py
"""
5.1.1.a — The Logic Planner Module

An abstract planner that decomposes a complex user prompt into a sequential
execution graph of discrete PlanSteps.  Each step carries a task type,
input payload, and dependency references so the Agent Runtime can execute
them in topological order.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional

logger = logging.getLogger("QuantumAgentPlanner")


@dataclass
class PlanStep:
    """A single atomic step in an execution plan."""
    step_id: str = field(default_factory=lambda: f"step-{uuid.uuid4().hex[:8]}")
    task_type: str = "generic"           # e.g. "research", "code", "review", "summarize"
    description: str = ""                # Human-readable description of the step
    input_payload: dict = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # step_ids this step waits for
    status: str = "pending"              # pending | running | completed | failed
    output: Optional[str] = None         # Result produced by this step

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AgentPlanner:
    """
    Abstract planner that breaks a complex prompt into a sequential execution graph.

    Usage:
        planner = AgentPlanner(llm_client)
        plan = planner.decompose("Build a REST API with auth and tests")
        for step in planner.get_execution_order(plan):
            ...execute step...
    """

    # Default decomposition system prompt
    DECOMPOSITION_SYSTEM_PROMPT = (
        "You are an autonomous task planner. Given a complex user request, "
        "decompose it into a strictly ordered list of discrete sub-tasks. "
        "Return ONLY a valid JSON array where each element has: "
        '"task_type" (one of: research, code, review, summarize, generic), '
        '"description" (brief description of the sub-task), '
        '"depends_on" (list of zero-indexed positions of tasks this depends on). '
        "Example: "
        '[{"task_type":"research","description":"Investigate auth patterns","depends_on":[]}, '
        '{"task_type":"code","description":"Implement JWT middleware","depends_on":[0]}]'
    )

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def decompose(self, prompt: str, max_steps: int = 10) -> List[PlanStep]:
        """
        Decomposes a complex user prompt into a list of PlanSteps by
        invoking the LLM to produce a structured execution graph.

        Falls back to a single generic step if the LLM is unavailable or
        returns unparseable output.
        """
        if not self.llm_client:
            logger.warning("No LLM client available. Returning single-step plan.")
            return [PlanStep(task_type="generic", description=prompt)]

        try:
            raw = self.llm_client._run_completion_internal(
                system_msg=self.DECOMPOSITION_SYSTEM_PROMPT,
                user_msg=prompt,
                max_tokens=800,
                temperature=0.2,
                force_json=True,
            )
            steps_data = json.loads(raw)
            if not isinstance(steps_data, list):
                raise ValueError("LLM did not return a JSON array")

            steps: List[PlanStep] = []
            for idx, item in enumerate(steps_data[:max_steps]):
                # Resolve positional depends_on to actual step_ids
                step = PlanStep(
                    task_type=item.get("task_type", "generic"),
                    description=item.get("description", ""),
                    input_payload=item.get("input_payload", {}),
                )
                steps.append(step)

            # Second pass: wire up depends_on by index → step_id
            for idx, item in enumerate(steps_data[:max_steps]):
                raw_deps = item.get("depends_on", [])
                for dep_idx in raw_deps:
                    if isinstance(dep_idx, int) and 0 <= dep_idx < len(steps):
                        steps[idx].depends_on.append(steps[dep_idx].step_id)

            logger.info(f"Decomposed prompt into {len(steps)} execution steps.")
            return steps

        except Exception as e:
            logger.error(f"Plan decomposition failed: {e}. Returning single-step fallback.")
            return [PlanStep(task_type="generic", description=prompt)]

    def get_execution_order(self, steps: List[PlanStep]) -> List[PlanStep]:
        """
        Returns the steps in topological execution order respecting depends_on.
        Steps with no dependencies come first.
        """
        id_map = {s.step_id: s for s in steps}
        visited = set()
        order = []

        def _visit(step: PlanStep):
            if step.step_id in visited:
                return
            visited.add(step.step_id)
            for dep_id in step.depends_on:
                dep = id_map.get(dep_id)
                if dep:
                    _visit(dep)
            order.append(step)

        for s in steps:
            _visit(s)

        return order

    def mark_step(self, step: PlanStep, status: str, output: Optional[str] = None):
        """Marks a step as completed/failed with optional output."""
        step.status = status
        if output is not None:
            step.output = output
        logger.info(f"Step {step.step_id} [{step.task_type}] → {status}")

    def serialize_plan(self, steps: List[PlanStep]) -> str:
        """Serializes the entire plan to a JSON string for persistence."""
        return json.dumps([s.to_dict() for s in steps])

    @staticmethod
    def deserialize_plan(data: str) -> List[PlanStep]:
        """Restores a plan from a JSON string."""
        items = json.loads(data)
        return [PlanStep.from_dict(item) for item in items]
