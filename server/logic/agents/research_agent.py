# logic/agents/research_agent.py
import logging
from server.logic.agents.base_agent import BaseAgent

logger = logging.getLogger("QuantumResearchAgent")

class ResearchAgent(BaseAgent):
    """
    5.2.a — Research Agent
    Equipped with web-search capabilities (simulated/mocked for now) to gather
    information and synthesize it into consolidated summaries.
    """
    def __init__(self, agent_id=None, llm_client=None):
        super().__init__(agent_id, llm_client)

    def _mock_web_search(self, query: str) -> str:
        """Simulates web search results."""
        logger.info(f"ResearchAgent executing mock web search for: '{query}'")
        return f"[MOCK SEARCH RESULTS FOR: {query}]\n- Result 1: Relevant technical documentation.\n- Result 2: Open source examples of {query}."

    def run(self, task_payload: dict) -> dict:
        topic = task_payload.get("topic", "general inquiry")
        logger.info(f"ResearchAgent started research on: {topic}")
        
        self.save_checkpoint({"status": "searching", "topic": topic})
        
        search_data = self._mock_web_search(topic)
        
        if self.llm_client:
            sys_msg = "You are a senior technical researcher. Summarize the provided search data into a concise markdown report."
            prompt = f"Topic: {topic}\nSearch Data:\n{search_data}"
            try:
                summary = self.llm_client._run_completion_internal(
                    system_msg=sys_msg,
                    user_msg=prompt,
                    max_tokens=800,
                    temperature=0.3
                )
            except Exception as e:
                logger.error(f"ResearchAgent LLM error: {e}")
                summary = f"Error generating summary: {e}"
        else:
            summary = f"# Research Report on {topic}\n\n{search_data}"

        self.save_checkpoint({"status": "completed", "topic": topic})
        
        return {
            "success": True,
            "agent_id": self.agent_id,
            "report": summary
        }
