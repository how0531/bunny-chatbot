
"""
Search Utilities Module.
Provides web search capabilities using Tavily API.
"""
from typing import List, Dict, Any
from backend.app.core.config import Config
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

TAVILY_AVAILABLE = False
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    pass

def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Perform a web search using Tavily.
    """
    if not TAVILY_AVAILABLE:
        logger.warning("Tavily client not installed.")
        return []
    
    if not Config.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set.")
        return []

    try:
        tavily = TavilyClient(api_key=Config.TAVILY_API_KEY)
        response = tavily.search(
            query=query, 
            search_depth="advanced", 
            max_results=max_results,
            include_answer=True 
        )
        return response.get('results', [])
    except Exception as e:
        logger.error(f"Tavily search failed for '{query}': {e}")
        return []

def format_search_results(results: List[Dict[str, Any]]) -> str:
    """
    Format search results into a markdown list.
    """
    if not results:
        return "無相關搜尋結果"
    
    summary = []
    for r in results:
        title = r.get('title', 'No Title')
        content = r.get('content', '')[:200]
        summary.append(f"• [{title}] {content}...")
        
    return "\n".join(summary)
