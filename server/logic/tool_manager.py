# logic/tool_manager.py
import datetime
import platform
import sys
import traceback
from duckduckgo_search import DDGS

class ToolManager:
    """
    Orchestrates pre-inference grounding routines such as real-time web searching 
    and operational environment injection.
    """
    
    @staticmethod
    def get_live_os_context() -> str:
        """Generates instantaneous systemic state for LLM grounding."""
        now = datetime.datetime.now()
        context = [
            f"--- LIVE SYSTEM AWARENESS ---",
            f"Current UTC-Local Time: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Day of Week: {now.strftime('%A')}",
            f"Platform: {platform.system()} {platform.release()}",
            f"Python Version: {sys.version.split(' ')[0]}"
        ]
        return "\n".join(context)
    
    @staticmethod
    def execute_web_search(query: str, limit: int = 5) -> str:
        """Performs instantaneous DuckDuckGo scrape to retrieve temporal information."""
        if not query or len(query.strip()) < 2:
            return ""
            
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=limit))
                
            if not results:
                return "⚠️ Web Search yielded no instantaneous results."
                
            formatted = [f"--- LIVE WEB SEARCH RESULTS FOR: '{query}' ---"]
            for i, res in enumerate(results, 1):
                title = res.get('title', 'Untitled')
                body = res.get('body', '')
                href = res.get('href', 'N/A')
                formatted.append(f"[{i}] Source: {href}\n    Snippet: {body}")
                
            return "\n\n".join(formatted)
        except Exception as e:
            return f"⚠️ Web Search Tool Fault: {str(e)}"
