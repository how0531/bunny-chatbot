from fastmcp import FastMCP
from typing import List, Dict, Any, Optional
from backend.app.services.metabase_service import MetabaseService
from backend.app.services.stock_service import StockService
from backend.app.core.config import Config
import yfinance as yf
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

try:
    from crawl4ai import AsyncWebCrawler
    CRAWL_AVAILABLE = True
except ImportError:
    CRAWL_AVAILABLE = False

# Initialize FastMCP Server
mcp = FastMCP("Bunny Chatbot")

# Initialize Services
metabase_service = MetabaseService()

# Initialize Tavily
tavily = TavilyClient(api_key=Config.TAVILY_API_KEY) if TAVILY_AVAILABLE and Config.TAVILY_API_KEY else None

# StockService needs metabase_service for market strength, and assumes Mongo connection via env
try:
    stock_service = StockService(metabase_service)
except Exception as e:
    print(f"Warning: StockService failed to initialize. Stock-related tools will be unavailable. Error: {e}")
    stock_service = None

def web_search_tool(query: str) -> Dict[str, Any]:
    """Internal logic for web search with in-memory caching."""
    if not tavily:
        return {"error": "Tavily Search is not configured. Please set TAVILY_API_KEY."}
    
    # 1. Check Cache (Provided by StockService if available)
    if stock_service:
        cached_data = stock_service.get_search_cache(query)
        if cached_data:
            print(f"DEBUG: Search Cache Hit for '{query}'")
            return cached_data['results']

    try:
        # 2. Call Tavily API
        response = tavily.search(query=query, search_depth="advanced", max_results=5)
        results = {"results": response.get('results', [])}
        
        # 3. Save to Cache for next 24 hours
        if stock_service and results.get('results'):
            stock_service.save_search_cache(query, results)
            
        return results
    except Exception as e:
        return {"error": f"Search failed: {e}"}

@mcp.tool()
def web_search(query: str) -> Dict[str, Any]:
    """
    Search the web for real-time market news, rumors, or detailed company info.
    """
    return web_search_tool(query)

async def scrape_url_tool(url: str) -> Dict[str, Any]:
    """Internal logic for scraping."""
    if not CRAWL_AVAILABLE:
        return {"error": "Crawl4AI is not installed."}
    
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return {
                "url": url,
                "markdown": result.markdown[:5000]
            }
    except Exception as e:
        return {"error": f"Scraping failed: {e}"}

@mcp.tool()
async def scrape_url(url: str) -> Dict[str, Any]:
    """
    Scrape a specific URL and convert the content to clean Markdown for analysis.
    """
    return await scrape_url_tool(url)

def get_realtime_quote_tool(stock_id: str) -> Dict[str, Any]:
    """Internal logic for realtime quotes."""
    ticker_id = stock_id
    if stock_id.isdigit() and len(stock_id) >= 4:
         ticker_id = f"{stock_id}.TW"
    
    try:
        ticker = yf.Ticker(ticker_id)
        info = ticker.fast_info
        return {
            "symbol": ticker_id,
            "last_price": info.last_price,
            "day_high": info.day_high,
            "day_low": info.day_low,
            "volume": info.last_volume,
            "timestamp": info.timezone
        }
    except Exception as e:
        return {"error": f"Failed to get quote for {stock_id}: {e}"}

@mcp.tool()
def get_realtime_quote(stock_id: str) -> Dict[str, Any]:
    """
    Get the absolute latest real-time stock price and day statistics from yfinance.
    """
    return get_realtime_quote_tool(stock_id)

def get_market_snapshot_data() -> Dict[str, Any]:
    """
    Get a snapshot of major market indices (US & TW).
    Returns a dictionary with 'us_indices' and 'tw_indices'.
    """
    us_data = metabase_service.get_us_indices()
    tw_data = metabase_service.get_tw_indices()
    return {
        "us_indices": us_data,
        "tw_indices": tw_data
    }

@mcp.tool()
def get_market_snapshot() -> Dict[str, Any]:
    """
    Get a snapshot of major market indices (US & TW).
    """
    return get_market_snapshot_data()

def get_institutional_flow_data() -> Dict[str, Any]:
    """
    Get institutional buy/sell flow data.
    """
    flow_data = metabase_service.get_institutional_flow()
    return {
        "institutional_flow": flow_data,
        "retail_futures": "PENDING_USER_INPUT"  # Placeholder
    }

@mcp.tool()
def get_institutional_flow() -> Dict[str, Any]:
    """
    Get institutional buy/sell flow data.
    """
    return get_institutional_flow_data()

def get_sector_analysis_data(days: int = 2) -> Dict[str, Any]:
    """
    Get analysis of top performing sectors.
    """
    sectors_data = metabase_service.get_strong_sectors(days=days, top_n=3)
    return {
        "strong_sectors": sectors_data
    }

@mcp.tool()
def get_sector_analysis() -> Dict[str, Any]:
    """
    Get analysis of top performing sectors.
    """
    return get_sector_analysis_data()

@mcp.tool()
def get_market_focus_stocks() -> Dict[str, Any]:
    """
    Get list of market spotlight stocks.
    Currently a placeholder.
    """
    return {
        "focus_stocks": "PENDING_USER_INPUT"
    }

@mcp.tool()
def get_stock_target_price(stock_id: str) -> Dict[str, Any]:
    """
    Get institutional target price and potential upside for a specific stock.
    Args:
        stock_id: The stock ticker symbol (e.g., '2330').
    """
    if not stock_service:
        return {"error": "StockService unavailable (DB Connection Failed)"}

    # Reuse StockService logic
    # Reuse StockService logic
    # Database connection is handled in StockService.__init__
    info = stock_service.get_twstock_info(stock_id)
    return {
        "stock_id": stock_id,
        "info": info
    }

@mcp.tool()
def get_stock_reason(stock_id: str) -> Dict[str, Any]:
    """
    Get the reason for a stock's recent movement using News + LLM.
    Args:
        stock_id: The stock ticker symbol.
    """
    if not stock_service:
        return {"error": "StockService unavailable (DB Connection Failed)"}
        
    return stock_service.get_stock_reason_analysis(stock_id)

@mcp.tool()
def get_market_strength_score() -> Dict[str, Any]:
    """
    Get the current market strength score (0-10), status, and visual bar.
    """
    if not stock_service:
         return {"error": "StockService unavailable (DB Connection Failed)"}

    strength_info = stock_service.get_market_strength_data()
    return {
        "strength_report": strength_info
    }

if __name__ == "__main__":
    # Standard way to run FastMCP
    mcp.run()
