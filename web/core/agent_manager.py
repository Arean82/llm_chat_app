import subprocess
import os
import sys
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Singleton Orchestrator to manage persistent background Hermes Agent processes for tenants.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Maps user_id -> subprocess.Popen object
        self.active_agents: Dict[str, subprocess.Popen] = {}
        
    def start_agent(self, user_id: str, api_key: str, gateway_url: str) -> bool:
        """
        Starts the Hermes Agent process for a specific tenant.
        Injects the internal SaaS API Gateway and the tenant's API token so that 
        the agent uses the BYOK credentials transparently.
        """
        if user_id in self.active_agents and self.active_agents[user_id].poll() is None:
            logger.warning(f"Agent for user {user_id} is already running.")
            return True
            
        # We need to construct the environment for the Hermes agent
        env = os.environ.copy()
        
        # Inject the SaaS API routing so Hermes transparently uses BYOK
        # The agent will direct its OpenAI-compatible requests to the internal Universal API Gateway
        env["OPENAI_BASE_URL"] = gateway_url
        env["OPENAI_API_KEY"] = api_key
        env["TENANT_USER_ID"] = str(user_id)
        
        # Determine the agent entry point (assuming it will be placed in server/logic/agents)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        agent_script = os.path.join(root_dir, "server", "logic", "agents", "hermes_runner.py")
        
        try:
            # We use python executable to launch the agent
            process = subprocess.Popen(
                [sys.executable, agent_script],
                env=env,
                stdout=subprocess.DEVNULL, # In a real implementation, we would route this to a tenant-specific log file
                stderr=subprocess.DEVNULL
            )
            self.active_agents[user_id] = process
            logger.info(f"Started Hermes Agent for tenant {user_id} with PID {process.pid}")
            return True
        except Exception as e:
            logger.error(f"Failed to start agent for tenant {user_id}: {e}")
            return False

    def stop_agent(self, user_id: str) -> bool:
        """Stops the background agent process for a tenant."""
        process = self.active_agents.get(user_id)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            del self.active_agents[user_id]
            logger.info(f"Stopped Hermes Agent for tenant {user_id}")
            return True
        return False
        
    def get_status(self, user_id: str) -> str:
        """Returns the current process status of the tenant's agent."""
        process = self.active_agents.get(user_id)
        if process:
            if process.poll() is None:
                return "RUNNING"
            else:
                return "STOPPED"
        return "NOT_STARTED"
