# logic/agents/agent_state_store.py
"""
5.1.1.c — Redis Agent State Store

Caches agent memory, variables, execution plan state, and workflow context
in Redis so that agents can pause and resume mid-workflow.  Uses the
central RedisManager service for thread-safe access.
"""

import json
import logging
import time
from typing import Optional

logger = logging.getLogger("QuantumAgentStateStore")


class AgentStateStore:
    """
    Persistent key-value state store for autonomous agents.
    Backed by the central Redis service (or its mock fallback).

    Keys are namespaced as `agent:{agent_id}:{field}` to prevent collisions.

    Usage:
        store = AgentStateStore(redis_service)
        store.save_state("agent-001", {"plan": [...], "current_step": 2})
        state = store.load_state("agent-001")
        store.set_field("agent-001", "status", "paused")
    """

    DEFAULT_TTL = 86400  # 24 hours

    def __init__(self, redis_service=None):
        self.redis_svc = redis_service
        self.client = None
        if redis_service:
            self.client = redis_service.get_client()

    def _key(self, agent_id: str, field: str = "state") -> str:
        """Builds a namespaced Redis key."""
        return f"agent:{agent_id}:{field}"

    # ------------------------------------------------------------------ #
    # Full state blob operations
    # ------------------------------------------------------------------ #

    def save_state(self, agent_id: str, state: dict, ttl: int = None) -> bool:
        """Persists the entire agent state blob as a JSON string."""
        if not self.client:
            logger.warning("AgentStateStore: no Redis client. Cannot save state.")
            return False
        try:
            key = self._key(agent_id, "state")
            serialized = json.dumps(state)
            self.client.set(key, serialized, ex=(ttl or self.DEFAULT_TTL))
            logger.info(f"Agent {agent_id} state saved ({len(serialized)} bytes).")
            return True
        except Exception as e:
            logger.error(f"Failed to save agent state for {agent_id}: {e}")
            return False

    def load_state(self, agent_id: str) -> Optional[dict]:
        """Loads the full agent state blob. Returns None if missing/expired."""
        if not self.client:
            return None
        try:
            key = self._key(agent_id, "state")
            raw = self.client.get(key)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to load agent state for {agent_id}: {e}")
            return None

    def delete_state(self, agent_id: str) -> bool:
        """Removes the entire agent state from the store."""
        if not self.client:
            return False
        try:
            self.client.delete(self._key(agent_id, "state"))
            # Also clean up known sub-fields
            for field in ("status", "plan", "variables", "checkpoint"):
                self.client.delete(self._key(agent_id, field))
            logger.info(f"Agent {agent_id} state cleared.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete agent state for {agent_id}: {e}")
            return False

    # ------------------------------------------------------------------ #
    # Individual field operations (for lightweight reads/writes)
    # ------------------------------------------------------------------ #

    def set_field(self, agent_id: str, field: str, value, ttl: int = None) -> bool:
        """Sets a single named field on the agent's state namespace."""
        if not self.client:
            return False
        try:
            key = self._key(agent_id, field)
            serialized = json.dumps(value) if not isinstance(value, str) else value
            self.client.set(key, serialized, ex=(ttl or self.DEFAULT_TTL))
            return True
        except Exception as e:
            logger.error(f"Failed to set field '{field}' for agent {agent_id}: {e}")
            return False

    def get_field(self, agent_id: str, field: str):
        """Gets a single named field. Attempts JSON parse, falls back to raw string."""
        if not self.client:
            return None
        try:
            key = self._key(agent_id, field)
            raw = self.client.get(key)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return raw
        except Exception as e:
            logger.error(f"Failed to get field '{field}' for agent {agent_id}: {e}")
            return None

    # ------------------------------------------------------------------ #
    # Workflow pause / resume helpers
    # ------------------------------------------------------------------ #

    def pause_agent(self, agent_id: str, plan_json: str, current_step_idx: int) -> bool:
        """
        Snapshots the agent's execution state so it can be resumed later.
        Stores the serialized plan and the index of the step to resume from.
        """
        success = True
        success &= self.set_field(agent_id, "status", "paused")
        success &= self.set_field(agent_id, "plan", plan_json)
        success &= self.set_field(agent_id, "checkpoint", json.dumps({
            "step_index": current_step_idx,
            "paused_at": time.time(),
        }))
        if success:
            logger.info(f"Agent {agent_id} paused at step {current_step_idx}.")
        return success

    def resume_agent(self, agent_id: str) -> Optional[dict]:
        """
        Retrieves the paused agent's checkpoint so the runtime can resume.
        Returns dict with 'plan' and 'checkpoint' keys, or None if not paused.
        """
        status = self.get_field(agent_id, "status")
        if status != "paused":
            logger.warning(f"Agent {agent_id} is not paused (status={status}). Cannot resume.")
            return None

        plan = self.get_field(agent_id, "plan")
        checkpoint = self.get_field(agent_id, "checkpoint")

        if plan is None or checkpoint is None:
            logger.error(f"Agent {agent_id} checkpoint data is incomplete.")
            return None

        self.set_field(agent_id, "status", "running")
        logger.info(f"Agent {agent_id} resumed from checkpoint.")
        return {"plan": plan, "checkpoint": checkpoint}

    def list_agents(self, pattern: str = "agent:*:status") -> list:
        """Lists all agent IDs that have a status field in the store."""
        if not self.client:
            return []
        try:
            keys = self.client.keys(pattern)
            agent_ids = []
            for k in keys:
                k_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                # Extract agent_id from "agent:{id}:status"
                parts = k_str.split(":")
                if len(parts) >= 3:
                    agent_ids.append(parts[1])
            return agent_ids
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []
