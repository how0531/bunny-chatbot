"""
FinRobot Agents - Wraps analysis capabilities.
Gemini API removed: ResearchAgent now directly formats Tavily search results.
FinRobotAnalyst now produces structured reports from existing StockService data.
"""
import logging
from typing import Dict, Any

from backend.app.services.stock_service import StockService

logger = logging.getLogger(__name__)


class FinRobotAnalyst:
    """
    Wrapper for structured Financial Chain-of-Thought (CoT) analysis.
    Produces report from existing StockService data (no LLM required).
    """
    def __init__(self, stock_service: StockService):
        self.service = stock_service

    def analyze_with_cot(self, stock_id: str) -> Dict[str, Any]:
        """
        Execute a structured Financial CoT analysis for a given stock.
        Uses StockService data directly and formats a structured report.
        """
        stock_name = self.service.get_stock_name(stock_id)
        logger.info(f"FinRobotAnalyst starting CoT for {stock_name} ({stock_id})")

        # 1. Retrieve all data from existing services
        analysis_data = self.service.get_stock_reason_analysis(stock_id)
        tw_info = self.service.get_twstock_info(stock_id)
        history = self.service.get_historical_analysis(stock_id, limit=2) or "暫無歷史資料"

        reason = analysis_data.get("reason", "暫無明確上漲原因")
        recent_news = analysis_data.get("recent_news", [])
        concepts = analysis_data.get("concepts", [])

        # 2. Format structured CoT report
        report_lines = []
        report_lines.append(f"### 📋 {stock_name}({stock_id}) 基礎分析報告\n")

        # Data interpretation
        report_lines.append("**1. 基礎數據解讀**")
        report_lines.append(tw_info if tw_info else "暫無基礎數據")

        # Catalyst
        report_lines.append("**2. 核心催化劑**")
        report_lines.append(f"📈 {reason}")

        # Recent news
        if recent_news:
            report_lines.append("\n**3. 近期新聞**")
            for n in recent_news[:3]:
                report_lines.append(f"- [{n.get('date', '')}] {n.get('title', '')}")

        # Concepts
        if concepts:
            report_lines.append(f"\n**相關概念**：{', '.join(concepts)}")

        # Historical
        report_lines.append(f"\n**4. 歷史研究紀錄**\n{history}")

        analysis_text = "\n".join(report_lines)

        return {
            "stock_id": stock_id,
            "name": stock_name,
            "cot_report": analysis_text,
            "source": "FinRobot-Direct-Analysis"
        }


class ResearchAgent:
    """
    Agent responsible for market research using web search.
    Formats Tavily search results directly (no LLM summarization required).
    """
    def __init__(self):
        # Reuse the web search tool from MCP service
        from backend.app.services.mcp_service import web_search_tool
        self.search_tool = web_search_tool

    def analyze_news(self, query: str) -> str:
        """
        Search for news related to the query and return formatted results.
        """
        logger.info(f"ResearchAgent analyzing news for: {query}")

        # 1. Web Search
        search_results = self.search_tool(query)

        if "error" in search_results:
            return f"⚠️ 搜尋服務暫時無法使用: {search_results['error']}"

        results = []
        if isinstance(search_results, dict) and "results" in search_results:
            results = search_results["results"]

        if not results:
            return "🔍 找不到相關的公開新聞資訊。"

        # 2. Direct formatting (no LLM required)
        lines = [f"### 🔍 市場研究：{query}\n"]

        bullish = []
        bearish = []
        sources = []

        for item in results:
            title = item.get("title", "No Title")
            content = item.get("content", "")
            url = item.get("url", "")
            pub_date = item.get("published_date", "")

            # Simple keyword-based sentiment classification
            if any(k in title + content for k in ["利多", "上漲", "突破", "買超", "獲利", "成長", "看好", "上調"]):
                bullish.append(f"- {title}")
            elif any(k in title + content for k in ["利空", "下跌", "風險", "警示", "虧損", "衰退", "看壞", "下調"]):
                bearish.append(f"- {title}")
            else:
                # Neutral news as core point
                snippet = content[:120] + "..." if len(content) > 120 else content
                lines.append(f"**{title}**\n{snippet}\n")

            if url:
                date_str = f" ({pub_date[:10]})" if pub_date else ""
                sources.append(f"- [{title[:40]}...]({url}){date_str}")

        # Add bullish/bearish sections
        if bullish or bearish:
            lines.append("**多空因素**")
            if bullish:
                lines.append("🟢 **利多**：")
                lines.extend(bullish[:3])
            if bearish:
                lines.append("🔴 **利空**：")
                lines.extend(bearish[:3])

        # Sources
        if sources:
            lines.append("\n**資料來源**：")
            lines.extend(sources[:5])

        lines.append("\n> ⚠️ 以上資訊僅供參考，投資決策請自行判斷。")

        return "\n".join(lines)


def get_research_agent() -> ResearchAgent:
    return ResearchAgent()
