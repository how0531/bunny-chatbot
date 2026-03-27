"""
Sophia Orchestrator - The Chief Coordinator Agent.
Now includes unified intent routing (moved from routes.py).
"""
import re
import logging
from typing import List, Dict, Any, Optional

from backend.app.services.stock_service import StockService
from backend.app.services.report_formatter import ReportFormatter
from backend.app.agents.finrobot_agents import FinRobotAnalyst
from backend.app.core.config import Config

# Try to import MCP tools
try:
    from backend.app.services.mcp_service import web_search_tool, scrape_url_tool, get_realtime_quote_tool
except ImportError:
    web_search_tool = scrape_url_tool = get_realtime_quote_tool = None

logger = logging.getLogger(__name__)


class AgentSophia:
    """Project Manager & Orchestrator - Routes intents and coordinates agents."""

    def __init__(self, service: StockService):
        self.service = service
        self.formatter = ReportFormatter(service)
        self.finrobot = FinRobotAnalyst(service)

    # ════════════════════ UNIFIED INTENT ROUTER ════════════════════

    def route_intent(self, message: str) -> Dict[str, Any]:
        """
        Parse user message and route to the correct handler.
        Returns dict with 'response', optionally 'chart_type', 'chart_data', 'bg_class'.
        """
        clean = message.strip()

        # ── Parse days command (近N日) ──
        days_match = re.search(r"(?:近|最近|進)?\s*(\d+)\s*(?:日|天)", message)
        requested_days = int(days_match.group(1)) if days_match else 20

        # ── 0. Concept Stock Query (highest priority for specific keyword) ──
        if "概念股" in message or ("族群" in message and "強勢" not in message):
            keyword = message.replace("概念股", "").replace("族群", "").replace("有哪些", "").replace("找", "").replace("請問", "").strip()
            if keyword:
                return {'response': self.service.get_concept_stocks(keyword)}

        # ── 1. Research Intent (web search) ──
        if re.search(r'搜尋|傳聞|即時|最新|新聞|法說會|消息|為什麼(漲|跌)|search|news|rumor', message, re.I) and len(message) > 4:
            return {'response': self.handle_market_research(message)}

        # ── 2. Batch Query (comma-separated IDs) ──
        if ',' in message:
            result = self._handle_batch_query(message)
            if result:
                return result

        # ── 3. Morning Report ──
        if any(k in message for k in ["投資早報", "早安", "盤前", "morning", "報告"]):
            return self._handle_morning_report(days_match, requested_days)

        # ── 4. Strong Sectors ──
        if any(k in message for k in ["強勢族群", "族群分析"]):
            return self._handle_sector_analysis(requested_days)

        # ── 5. Market Strength ──
        if any(k in message for k in ['市場強度', '市場大方向', 'market']):
            return self._handle_market_strength(requested_days)

        # ── 6. Market Trend ──
        if any(k in message for k in ["近期趨勢", "繪製趨勢", "市場趨勢", "trend"]):
            return self._handle_market_trend(requested_days)

        # ── 7. Compound Screening (Dynamic Rule Engine) ──
        if re.search(r'(找出|篩選|挑選|選股).*(且|and|條件|>|<|大於|小於)', message, re.I):
            return {'response': self.handle_custom_screening(message)}

        # ── 8. Trust Buy Ratio (simple query) ──
        if any(k in message for k in ["投信", "買超比重", "認養"]) and not re.search(r'(且|and|>|<)', message):
            limit = 10
            match = re.search(r"[前]\s*(\d+)", message)
            if match:
                limit = int(match.group(1))
            return {'response': self.handle_trust_selection(limit=limit)}

        # ── 9. Stock-specific query ──
        stock_id = self.service.extract_stock_id(message)
        if stock_id:
            return self._handle_stock_query(stock_id, message)

        # ── 10. Fallback: Concept Search (MongoDB Hotwords) ──
        results = self.service.search_by_concept(message)
        if results:
            resp = f"🔍 **搜尋「{message}」相關概念股：**\n\n" + "、".join(results) + "\n\n(輸入代號查看詳細分析)"
            return {'response': resp}

        return {'response': f"找不到與「{message}」相關的內容，請嘗試輸入代號或產業關鍵字。"}

    # ════════════════════ INTENT HANDLERS ════════════════════

    def _handle_batch_query(self, message: str) -> Optional[Dict]:
        stock_ids = [s.strip() for s in message.split(',')]
        stock_ids = [s for s in stock_ids if s.isdigit() and len(s) >= 3]
        if not stock_ids:
            return None

        results = []
        for sid in stock_ids[:5]:
            name = self.service.get_stock_name(sid)
            _, analysis = self.service.analyze_stock(sid)

            sentiment = "⚪"
            if "🟢" in analysis: sentiment = "🟢"
            elif "🔴" in analysis: sentiment = "🔴"
            elif "🟡" in analysis: sentiment = "🟡"
            elif "🔥" in analysis: sentiment = "🔥"

            lines = analysis.split('\n')
            summary_text = ""
            for line in lines:
                if "上漲原因" in line:
                    summary_text = line.replace("📈 上漲原因:", "").replace("上漲原因:", "").strip()
                    break
            if not summary_text:
                for line in lines:
                    if any(k in line for k in ["情緒指標", "個股資訊", "綜合評分", "獨家熱點"]): continue
                    if not line.strip(): continue
                    summary_text = line.strip()
                    break

            summary_text = summary_text.replace('|', ' ')
            results.append({
                'id': sid, 'name': name, 'sentiment': sentiment,
                'summary': summary_text[:30] + "..." if len(summary_text) > 30 else summary_text
            })

        response_text = f"📊 **批次查詢結果 ({len(results)} 檔)**\n\n"
        response_text += "| 代號 | 名稱 | 情緒 | 摘要 |\n|------|------|------|------|\n"
        for r in results:
            response_text += f"| {r['id']} | {r['name']} | {r['sentiment']} | {r['summary']} |\n"
        response_text += "\n💡 輸入單一代號可查看完整分析"
        return {'response': response_text}

    def _handle_morning_report(self, days_match, requested_days: int) -> Dict:
        try:
            morning_days = int(days_match.group(1)) if days_match else 2
            snapshot = self.service.metabase.get_market_snapshot()
            inst_flow = self.service.metabase.get_institutional_flow_aggregated()
            sector_data = self.service.metabase.get_sector_analysis_data(days=morning_days)
            report = self.formatter.generate_report(snapshot, inst_flow, sector_data, days=morning_days)
            return {'response': report}
        except Exception as e:
            logger.error(f"Morning report error: {e}", exc_info=True)
            return {'response': f"⚠️ 生成報表失敗：{str(e)}"}

    def _handle_sector_analysis(self, days: int) -> Dict:
        try:
            sector_data = self.service.metabase.get_sector_analysis_data(days=days)
            report = self.formatter._format_strong_sectors(sector_data.get('strong_sectors', []), days=days)
            return {'response': report}
        except Exception as e:
            logger.error(f"Sector analysis error: {e}", exc_info=True)
            return {'response': "⚠️ 讀取族群分析失敗"}

    def _handle_market_strength(self, days: int) -> Dict:
        market_data = self.service.get_market_strength_data()
        if "error" in market_data:
            return {'response': f"無法取得市場強度 ({market_data['error']})"}
        response_text = f"目前市場強度：{market_data['status']} {market_data['bar']} ({market_data['display_score']:.1f})"
        trend_data = self.service.get_market_trend(days=days)
        return {
            'response': response_text,
            'chart_type': 'line',
            'chart_data': trend_data[::-1],
            'bg_class': market_data.get('bg_class')
        }

    def _handle_market_trend(self, days: int) -> Dict:
        trend_data = self.service.get_market_trend(days=days)
        return {
            'response': f"📊 **近 {days} 趨勢分析**\n正在為您渲染動態趨勢圖表...",
            'chart_type': 'line',
            'chart_data': trend_data[::-1]
        }

    def _handle_stock_query(self, stock_id: str, message: str) -> Dict:
        """Handle individual stock analysis with enriched data."""
        # Historical analysis
        if '歷史' in message or 'history' in message.lower():
            name = self.service.get_stock_name(stock_id)
            historical = self.service.get_historical_analysis(stock_id, limit=5)
            return {'response': f"**{name} ({stock_id}) 歷史熱點記錄**\n\n{historical or '目前無記錄'}"}

        # Detect deep analysis mode
        mode = 'standard'
        if any(k in message for k in ['分析', '深度', '專業', 'cot', 'finrobot']):
            mode = 'finrobot'

        result = self.handle_stock_analysis(stock_id, mode=mode, output_format='carousel')
        return {'response': result}

    # ════════════════════ CORE ANALYSIS METHODS ════════════════════

    def handle_stock_analysis(self, stock_id: str, mode: str = 'standard', output_format: str = 'text') -> Any:
        """Orchestrate full stock analysis with all agents."""
        logger.info(f"Sophia: {mode} analysis for {stock_id} (Format: {output_format})")

        if mode == 'finrobot':
            cot_data = self.finrobot.analyze_with_cot(stock_id)
            tw_info = self.service.get_twstock_info(stock_id)
            text_report = self.formatter.format_stock_focus(cot_data, tw_info)
            if output_format == 'carousel':
                chips = self.service.get_chips_history(stock_id)
                funds = self.service.get_fundamentals_data(stock_id)
                # ── NEW: Add peer comparison card ──
                peers = self._get_peer_comparison_card(stock_id)
                cards = [
                    {"title": "消息面", "content": text_report, "type": "markdown"},
                    {"title": "籌碼面", "data": chips, "type": "chart_chips"},
                    {"title": "基本面", "data": funds, "type": "grid_fundamentals"},
                ]
                if peers:
                    cards.append({"title": "同業比較", "content": peers, "type": "markdown"})
                return {"type": "carousel", "cards": cards}
            return text_report

        # Standard mode
        arthur = AgentArthur(self.service)
        oscar = AgentOscar(self.service)

        analysis_data = arthur.analyze(stock_id)

        max_retries = 2
        for i in range(max_retries):
            review_result = oscar.review(analysis_data)
            if review_result['status'] == 'APPROVED':
                analysis_data = review_result['data']
                break
            else:
                logger.warning(f"Oscar rejected: {review_result['reason']}. Retrying...")
                analysis_data = arthur.analyze(stock_id, cleanup_mode=True)

        tw_info = self.service.get_twstock_info(stock_id)
        analysis_data['source'] = "Sophia Managed (Arthur-Oscar-V2)"

        tw_info_for_text = "" if output_format == 'carousel' else tw_info
        final_report = self.formatter.format_stock_focus(analysis_data, tw_info_for_text)

        # Proactive Fallback
        if analysis_data.get('source') == 'System Fallback' or not analysis_data.get('recent_news'):
            logger.info(f"Sophia: proactive research for {stock_id}")
            if web_search_tool and Config.TAVILY_API_KEY:
                research_query = f"最近關於 {analysis_data.get('name')}({stock_id}) 的重大新聞、營收表現或漲跌分析"
                research_report = self.handle_market_research(research_query)
                final_report += f"\n\n---\n🔍 **Sophia 自動補位：本地數據庫暫無此個股新聞，已啟動實時網路研究...**\n\n{research_report}"

        if output_format == 'carousel':
            chips = self.service.get_chips_history(stock_id)
            funds = self.service.get_fundamentals_data(stock_id)
            peers = self._get_peer_comparison_card(stock_id)
            cards = [
                {"title": "消息面", "content": final_report, "type": "markdown"},
                {"title": "籌碼面", "data": chips, "type": "chart_chips"},
                {"title": "基本面", "data": funds, "type": "grid_fundamentals"},
            ]
            if peers:
                cards.append({"title": "同業比較", "content": peers, "type": "markdown"})
            return {"type": "carousel", "cards": cards}

        return final_report

    def _get_peer_comparison_card(self, stock_id: str) -> Optional[str]:
        """Generate peer comparison markdown card."""
        try:
            profile = self.service.pipeline.enrich(stock_id, include_peers=True)
            peers = profile.get('peers', [])
            if not peers:
                return None

            yf_data = profile.get('yfinance', {})
            name = profile.get('name', stock_id)

            report = f"### 📊 {name}({stock_id}) 同業比較\n\n"
            report += "| 代號 | 名稱 | 本益比 | 殖利率 | 股價淨值比 |\n"
            report += "| :--- | :--- | ---: | ---: | ---: |\n"

            # Add current stock first (highlighted)
            pe = yf_data.get('pe', '-')
            dy = yf_data.get('yield_rate', '-')
            pb = yf_data.get('pb', '-')
            report += f"| **{stock_id}** | **{name}** ⬅️ | **{pe}** | **{dy}** | **{pb}** |\n"

            for p in peers[:5]:
                p_pe = p.get('本益比', '-')
                p_dy = p.get('殖利率', '-')
                p_pb = p.get('股價淨值比', '-')
                pe_str = f"{float(p_pe):.1f}" if p_pe and p_pe != '-' else '-'
                dy_str = f"{float(p_dy):.2f}%" if p_dy and p_dy != '-' else '-'
                pb_str = f"{float(p_pb):.2f}" if p_pb and p_pb != '-' else '-'
                report += f"| {p.get('股票代號','')} | {p.get('股票名稱','')} | {pe_str} | {dy_str} | {pb_str} |\n"

            return report
        except Exception as e:
            logger.error(f"Peer comparison error: {e}")
            return None

    def handle_market_research(self, query: str) -> str:
        """Sophia delegates market research to ResearchAgent."""
        logger.info(f"Sophia: market research for: {query}")
        try:
            from backend.app.agents.finrobot_agents import get_research_agent
            agent = get_research_agent()
            return agent.analyze_news(query)
        except Exception as e:
            logger.error(f"Market research failed: {e}")
            return f"⚠️ 執行市場研究時發生技術錯誤: {str(e)}"

    def handle_trust_selection(self, limit: int = 10) -> str:
        """Handle investment trust buy ratio selection."""
        logger.info(f"Sophia: Trust selection (Limit: {limit})")
        try:
            top_list = self.service.get_top_trust_buy_ratio(limit)
            if not top_list:
                return "❌ 暫時無法取得投信買超比重資料。"

            latest_date = self.service.get_latest_twstock_date()
            date_str = latest_date if latest_date else "最新"

            report = f"### 🎯 投信認養清單 (資料日期: {date_str})\n"
            report += f"根據 **投信買超比重** 篩選出前 {len(top_list)} 名標的：\n\n"
            report += "| 排名 | 代碼 | 公司 | 投信買超(張) | **買超比重(%)** |\n"
            report += "| :--- | :--- | :--- | :--- | :--- |\n"

            for i, item in enumerate(top_list, 1):
                rank_str = f"**{i}**" if i <= 3 else str(i)
                report += f"| {rank_str} | {item['stock_id']} | {item['name']} | {item['trust_buy_lots']} | **{item['ratio']}%** |\n"

            report += "\n> [!TIP]\n> **買超比重** 是觀察投信「認養度」的核心指標。\n"
            report += "---\n*💡 輸入股票代碼（如 `2330`）可進一步查看詳細分析*"
            return report
        except Exception as e:
            logger.error(f"Trust selection error: {e}")
            return f"❌ 執行選股分析時發生錯誤: {e}"

    def handle_custom_screening(self, query: str) -> str:
        """Handle compound stock screening via Dynamic Rule Engine."""
        logger.info(f"Sophia: custom screening: {query}")
        try:
            from backend.app.services.rule_engine import DynamicScreener
            screener = DynamicScreener(self.service)
            results, parsed = screener.screen(query)
            return screener.format_results(results, parsed, query)
        except Exception as e:
            logger.error(f"Custom screening error: {e}")
            return f"❌ 執行自訂選股時發生錯誤: {e}"


class AgentArthur:
    """The Data Miner & LLM Analyst."""
    def __init__(self, service: StockService):
        self.service = service

    def analyze(self, stock_id: str, cleanup_mode: bool = False) -> Dict[str, Any]:
        return self.service.get_stock_reason_analysis(stock_id, cleanup_mode=cleanup_mode)


class AgentOscar:
    """The Integrity Guardian (QA)."""
    def __init__(self, service: StockService):
        self.service = service

    def review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        stock_id = data.get('stock_id')
        news = data.get('recent_news', [])

        unrelated_noise = False
        reason = "OK"

        for n in news:
            title = n.get('title', '')
            if "台積電" in title and stock_id != "2330" and stock_id not in title:
                unrelated_noise = True
                reason = "發現非關聯權值股噪音"
                break

        if unrelated_noise:
            return {'status': 'REJECTED', 'reason': reason, 'data': data}
        return {'status': 'APPROVED', 'reason': 'Pass', 'data': data}


# Global singleton
_orchestrator = None

def get_orchestrator(service: StockService):
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentSophia(service)
    return _orchestrator
