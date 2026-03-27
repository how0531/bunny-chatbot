"""
StockService - Facade pattern.
Delegates to DataAccess, ScoringEngine, and EnrichmentPipeline.
Maintains backward-compatible API so routes.py and other callers keep working.
"""
import re
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any

from backend.app.core.config import Config
from backend.app.core.logger import setup_logger, get_logger
import backend.app.core.constants as const

from backend.app.services.data_access import MongoDataAccess, YFinanceDataAccess
from backend.app.services.scoring_engine import BunnyGoodScorer
from backend.app.services.metabase_service import MetabaseService

logger = setup_logger(__name__, log_file=Config.LOG_FILE, level=Config.get_log_level())


class StockService:
    """
    Thin facade that provides the same public API as before,
    but delegates heavy logic to specialised modules.
    """

    def __init__(self, metabase_service=None):
        # Data Access Layer
        self.mongo = MongoDataAccess()
        self.yf = YFinanceDataAccess
        self.scorer = BunnyGoodScorer()
        self.metabase = metabase_service if metabase_service else MetabaseService()

        # Expose underlying collections for backward compat (rule_engine, etc.)
        self.twstock_col = self.mongo.twstock_col
        self.hotwords_col = self.mongo.hotwords_col
        self.collection = self.mongo.news_col
        self.alphamemo_col = self.mongo.alphamemo_col

        # Lazy-init enrichment pipeline
        self._pipeline = None

        logger.info("StockService (Facade) initialized")

    @property
    def pipeline(self):
        """Lazy init to avoid circular imports."""
        if self._pipeline is None:
            from backend.app.services.enrichment_pipeline import StockEnrichmentPipeline
            self._pipeline = StockEnrichmentPipeline(self.mongo, self.metabase)
        return self._pipeline

    # ═══════════════════════════ Forward Methods ══════════════════════════
    # These maintain backward compatibility with routes.py and agents.

    def get_stock_name(self, stock_id: str) -> str:
        return self.mongo.get_stock_name(stock_id)

    def get_id_by_name(self, name: str) -> Optional[str]:
        return self.mongo.get_id_by_name(name)

    def extract_stock_id(self, text: str) -> Optional[str]:
        return self.mongo.extract_stock_id(text)

    def search_by_concept(self, keyword: str) -> List[str]:
        return self.mongo.search_by_concept(keyword)

    def get_historical_analysis(self, stock_id: str, limit: int = 3) -> Optional[str]:
        return self.mongo.get_historical_analysis(stock_id, limit)

    def get_search_cache(self, query: str):
        return self.mongo.get_search_cache(query)

    def save_search_cache(self, query: str, results: Dict):
        self.mongo.save_search_cache(query, results)

    def get_latest_twstock_date(self) -> Optional[str]:
        return self.mongo.get_latest_twstock_date()

    def get_shares_outstanding(self, stock_id: str) -> Optional[int]:
        return self.yf.get_shares_outstanding(stock_id)

    # ═══════════════════════════ YFinance ═════════════════════════════════

    def _get_yfinance_data(self, stock_id: str) -> Dict:
        """Backward-compatible yfinance wrapper."""
        return self.yf.get_stock_data(stock_id)

    # ═══════════════════════════ TWStock Info ═════════════════════════════

    def get_twstock_info(self, stock_id: str) -> str:
        """Generate formatted twstock info string (backward compat)."""
        tw_doc = self.mongo.get_twstock_doc(stock_id)
        yf_data = self.yf.get_stock_data(stock_id)
        tech_data = self.yf.get_technical_data(stock_id)

        pe = None
        yield_rate = None
        buysell = {}

        if tw_doc:
            buysell = tw_doc.get('買賣超', {})
            # Try nested path
            chips_node = tw_doc.get('籌碼面', {})
            if chips_node.get(const.FIELD_BUY_SELL):
                buysell = chips_node[const.FIELD_BUY_SELL]
            pe = tw_doc.get('本益比')
            yield_rate = tw_doc.get('殖利率')

        # Fill from yfinance
        current_price = yf_data.get('price')
        if not pe: pe = yf_data.get('pe')
        if not yield_rate: yield_rate = yf_data.get('yield_rate')

        avg_target_price = self.get_average_target_price(stock_id)

        has_data = pe or yield_rate or buysell or avg_target_price or yf_data.get('mkt_cap') or tech_data
        if not has_data:
            return ""

        info = f"\n📊 **個股資訊**\n"

        # Market Cap & Beta
        if yf_data.get('mkt_cap'):
            info += f"- 市值: {yf_data['mkt_cap']}"
            if yf_data.get('beta'): info += f" | Beta: {yf_data['beta']}"
            info += "\n"

        # PE, PB & Yield
        metrics = []
        if pe: metrics.append(f"PE: {pe}")
        if yf_data.get('pb'): metrics.append(f"PB: {yf_data['pb']}")
        if yield_rate: metrics.append(f"殖利率: {yield_rate}")
        if metrics: info += f"- {' | '.join(metrics)}\n"

        # Profitability
        profit_info = []
        if yf_data.get('eps'): profit_info.append(f"EPS: ${yf_data['eps']}")
        if yf_data.get('roe'): profit_info.append(f"ROE: {yf_data['roe']}")
        if profit_info: info += f"- 獲利能力: {' | '.join(profit_info)}\n"

        # 52 Week Range
        if yf_data.get('52w_range'):
            info += f"- 52週區間: {yf_data['52w_range']}\n"

        # ── NEW: Technical Indicators ──
        if tech_data:
            tech_parts = []
            if tech_data.get('rsi'):
                rsi_val = tech_data['rsi']
                rsi_tag = "⚠️超買" if rsi_val > 70 else "💡超賣" if rsi_val < 30 else ""
                tech_parts.append(f"RSI: {rsi_val} {rsi_tag}")
            if tech_data.get('k_value') and tech_data.get('d_value'):
                tech_parts.append(f"K/D: {tech_data['k_value']}/{tech_data['d_value']}")
            if tech_data.get('ma_bullish') is True:
                tech_parts.append("均線多頭排列 ✅")
            elif tech_data.get('ma_bearish') is True:
                tech_parts.append("均線空頭排列 ⚠️")
            if tech_parts:
                info += f"- 技術面: {' | '.join(tech_parts)}\n"

        # ── NEW: Consecutive Buy Days ──
        foreign_days = self.mongo.calculate_consecutive_buy_days(stock_id, 'foreign')
        trust_days = self.mongo.calculate_consecutive_buy_days(stock_id, 'trust')

        # Institutional flow
        if buysell:
            flow_parts = []
            if const.FIELD_FOREIGN_BUY_SELL in buysell:
                foreign = buysell[const.FIELD_FOREIGN_BUY_SELL]
                streak = f" (連{foreign_days}日)" if foreign_days >= 2 else ""
                flow_parts.append(f"外資: {foreign}{streak}")
            if const.FIELD_TRUST_BUY_SELL in buysell:
                trust = buysell[const.FIELD_TRUST_BUY_SELL]
                streak = f" (連{trust_days}日)" if trust_days >= 2 else ""
                flow_parts.append(f"投信: {trust}{streak}")
            if flow_parts:
                info += f"- {' | '.join(flow_parts)}\n"

        # Target Price
        if avg_target_price:
            upside_str = ""
            if current_price:
                try:
                    upside = ((avg_target_price - current_price) / current_price) * 100
                    upside_str = f" (潛在漲幅: {upside:.1f}%)"
                except:
                    pass
            info += f"- 機構平均目標價: ${avg_target_price:.1f} (近3個月){upside_str}\n"

        return info + "\n"

    # ═══════════════════════════ Analysis ═════════════════════════════════

    def analyze_stock(self, stock_id: str, mode: str = 'compact') -> Tuple:
        """
        Analyze a stock - returns (context, formatted_text).
        Improved: uses enrichment pipeline for richer data.
        """
        tw_info = self.get_twstock_info(stock_id)

        # Get enriched profile
        profile = self.pipeline.enrich(stock_id, include_peers=False)

        hotword = profile.get('hotword', {})
        hotword_doc = hotword.get('doc')
        sentiment_indicator = profile.get('news', {}).get('sentiment_indicator', '⚪')

        score = profile.get('score', 5.0)
        stars = self.scorer.score_to_stars(score)

        if hotword_doc:
            rise_reason = hotword.get('rise_reason', '')
            market_news = hotword.get('market_news', '')
            concepts = hotword.get('concepts', '')
            date_str = hotword.get('date', '')
            days_diff = hotword.get('days_diff', 0)

            freshness_alert = ""
            if days_diff > 30:
                freshness_alert = f" ⚠️ (資料已過期 {days_diff} 天)"
            elif days_diff > 7:
                freshness_alert = f" ({days_diff} 天前)"

            if rise_reason or market_news:
                hotword_intro = f"【獨家熱點分析 ({date_str}){freshness_alert}】\n"
                hotword_intro += f"綜合評分: {score:.1f}/10 {stars}\n"
                hotword_intro += f"情緒指標: {sentiment_indicator}\n"

                if concepts:
                    hotword_intro += f"相關概念: {concepts}\n"
                if rise_reason:
                    hotword_intro += f"📈 上漲原因: {rise_reason}\n"

                if mode == 'detailed':
                    if market_news:
                        hotword_intro += f"📢 市場消息: {market_news}\n"

                hotword_intro += tw_info
                return None, hotword_intro

        # Fallback: news + LLM
        news_list = profile.get('news', {}).get('news_list', [])
        stock_name = profile.get('name', const.FALLBACK_STOCK_NAME)

        if not news_list:
            return None, "🔍 近期無特定個股重大消息。建議從產業面或技術面進行觀察。"

        # Earnings
        earnings_text = ""
        earnings = profile.get('earnings', {})
        if earnings.get('found'):
            highlights = earnings.get('highlights', '')
            date = earnings.get('date', '')
            earnings_text = f"\n【法說會重點 ({date})】\n{highlights}\n"

        # Fallback: use news titles directly (no LLM)
        news_list = profile.get('news', {}).get('news_list', [])
        stock_name = profile.get('name', const.FALLBACK_STOCK_NAME)

        if not news_list:
            return None, "🔍 近期無特定個股重大消息。建議從產業面或技術面進行觀察。"

        # Earnings
        earnings_text = ""
        earnings = profile.get('earnings', {})
        if earnings.get('found'):
            highlights = earnings.get('highlights', '')
            date = earnings.get('date', '')
            earnings_text = f"\n【法說會重點 ({date})】\n{highlights}\n"

        # Compose reason from news titles (first 1-2 most relevant)
        top_news = news_list[:2]
        if top_news:
            reason_parts = [n['title'] for n in top_news if n.get('title')]
            composed_reason = "；".join(reason_parts[:2]) if reason_parts else "近期有相關新聞動態"
        else:
            composed_reason = "近期有相關新聞動態"

        final_response = f"綜合評分: {score:.1f}/10 {stars}\n"
        final_response += f"情緒指標: {sentiment_indicator}\n\n"
        final_response += f"📈 **核心觀察**：{composed_reason}\n"
        if earnings_text:
            final_response += earnings_text
        final_response += tw_info

        news_context = "\n".join([
            f"新聞{i+1} [{n.get('date','')}] {n['title']}\n摘要:{n['summary']}\n"
            for i, n in enumerate(news_list[:3])
        ])
        return news_context, final_response

    # ═══════════════════════════ Scoring ══════════════════════════════════

    def calculate_score(self, hotword_doc, sentiment_score, days_diff, stock_id=None):
        """Backward compat wrapper for scoring."""
        yf_data = self.yf.get_stock_data(stock_id) if stock_id else {}
        tech_data = self.yf.get_technical_data(stock_id) if stock_id else {}

        chips_data = None
        if stock_id:
            tw_doc = self.mongo.get_twstock_doc(stock_id)
            if tw_doc:
                buysell = tw_doc.get('籌碼面', {}).get(const.FIELD_BUY_SELL, {})
                if not buysell:
                    buysell = tw_doc.get(const.FIELD_BUY_SELL, {})

                def p(raw):
                    try: return int(float(str(raw).replace(',', '').replace('張', '')))
                    except: return 0

                chips_data = {
                    'foreign_net': p(buysell.get(const.FIELD_FOREIGN_BUY_SELL, 0)),
                    'trust_net': p(buysell.get(const.FIELD_TRUST_BUY_SELL, 0)),
                    'foreign_consecutive_days': self.mongo.calculate_consecutive_buy_days(stock_id, 'foreign'),
                    'trust_consecutive_days': self.mongo.calculate_consecutive_buy_days(stock_id, 'trust'),
                }

        target = self.get_average_target_price(stock_id) if stock_id else None

        return self.scorer.calculate_score(
            hotword_doc=hotword_doc,
            sentiment_score=sentiment_score,
            days_diff=days_diff,
            yf_data=yf_data,
            tech_data=tech_data,
            chips_data=chips_data,
            target_price=target,
        )

    # ═══════════════════════════ Reason Analysis ═════════════════════════

    def get_stock_reason_analysis(self, stock_id: str, cleanup_mode: bool = False) -> Dict[str, Any]:
        """Get structured reason analysis for a stock."""
        stock_name = self.mongo.get_stock_name(stock_id)
        hotword_doc = self.mongo.get_hotword_doc(stock_id)

        reason = "暫無明確上漲原因"
        concepts = []

        if hotword_doc:
            reason = hotword_doc.get('股價上漲原因(熱度起始日)', reason)
            c_str = hotword_doc.get('豐搜新聞概念股', '')
            if c_str: concepts = c_str.split(';')

        news_list = self.mongo.get_recent_news(stock_id, stock_name, limit=10 if not cleanup_mode else 20)

        if (reason == "暫無明確上漲原因" or "無新聞資料" in reason) and not news_list:
            return {
                "stock_id": stock_id,
                "name": stock_name,
                "reason": "🔍 近期無特定個股重大消息。建議從產業面或同業表現進行觀察。",
                "concepts": concepts,
                "recent_news": [],
                "source": "System Fallback"
            }

        # Direct reason from news titles (no LLM)
        if (reason == "暫無明確上漲原因" or "無新聞資料" in reason) and news_list:
            try:
                top_titles = [n['title'] for n in news_list[:2] if n.get('title')]
                if top_titles:
                    reason = "；".join(top_titles[:2])
                    if len(reason) > 60:
                        reason = reason[:60] + "..."
            except Exception as e:
                logger.error(f"Direct reason extraction failed: {e}")

        return {
            "stock_id": stock_id,
            "name": stock_name,
            "reason": reason,
            "concepts": concepts,
            "recent_news": news_list,
            "source": "Arthur Analysis Engine"
        }

    # ═══════════════════════════ Target Price ═════════════════════════════

    def get_average_target_price(self, stock_id: str) -> Optional[float]:
        try:
            target_data = self.metabase.get_analyst_target_prices(stock_id)
            if not target_data: return None
            prices = [float(item['目標價']) for item in target_data if item.get('目標價')]
            return sum(prices) / len(prices) if prices else None
        except Exception as e:
            logger.error(f"get_average_target_price error {stock_id}: {e}")
            return None

    # ═══════════════════════════ Market Strength ═════════════════════════

    def get_market_strength_data(self) -> Dict[str, Any]:
        history = self.metabase.get_market_hedge_history(days=1)
        if not history:
            return {"error": "No data available"}

        score = float(history[0]['score'])
        display_score = round(10 - score, 1)

        if display_score >= 7:
            status, bg_class = "強", "bg-red-trans"
        elif display_score >= 4:
            status, bg_class = "觀望", "bg-grey-trans"
        else:
            status, bg_class = "弱", "bg-green-trans"

        bar_len = int(display_score)
        bar = "█" * bar_len + "░" * (10 - bar_len)

        return {
            "score": score, "display_score": display_score,
            "status": status, "bar": bar, "bg_class": bg_class
        }

    def get_market_strength(self) -> str:
        data = self.get_market_strength_data()
        if "error" in data:
            return f"無法取得市場強度 ({data['error']})"
        return f"目前市場強度：{data['status']} {data['bar']} ({data['display_score']:.1f})"

    def get_market_trend(self, days: int = 20) -> List[Dict]:
        score_history = self.metabase.get_market_hedge_history(days=days)
        index_history = self.metabase.get_tw_index_history(days=days)
        index_map = {item['date']: item['price'] for item in index_history}

        merged = []
        for item in score_history:
            date = item['date']
            raw_score = float(item['score'])
            display_score = round(10 - raw_score, 1)
            merged.append({
                'date': date,
                'score': display_score,
                'index_price': index_map.get(date)
            })
        return merged

    # ═══════════════════════════ Concept Stocks (ClickHouse) ══════════════

    def get_concept_stocks(self, concept_name: str) -> str:
        if not self.metabase:
            return "❌ Metabase 連線異常，無法查詢概念股。"
        try:
            stocks = self.metabase.get_concept_stocks(concept_name)
            if not stocks:
                return f"🔍 找不到屬於「{concept_name}」概念的股票。\n(請嘗試更通用的產業名稱，如：半導體、AI、電動車)"

            total = len(stocks)
            concepts_found = set(s['概念名稱'] for s in stocks if s.get('概念名稱'))

            report = f"🧩 **{concept_name} 概念股一覽** ({total} 檔)\n\n"
            if len(concepts_found) > 1:
                report += f"💡 相關概念: {', '.join(list(concepts_found)[:3])}\n\n"

            report += "| 代號 | 名稱 | 產業 | 本益比 | 殖利率 |\n| :--- | :--- | :--- | ---: | ---: |\n"

            for s in stocks[:30]:
                pe = s.get('本益比', '-')
                dy = s.get('殖利率', '-')
                pe_str = f"{float(pe):.1f}" if pe and pe != '-' else '-'
                yield_str = f"{float(dy):.2f}%" if dy and dy != '-' else '-'
                report += f"| {s['股票代號']} | {s['股票名稱']} | {s.get('產業', '-')} | {pe_str} | {yield_str} |\n"

            if total > 30:
                report += f"\n... 及其他 {total - 30} 檔股票"
            report += f"\n\n💡 輸入單一代號可查看完整分析"
            return report
        except Exception as e:
            logger.error(f"get_concept_stocks error {concept_name}: {e}")
            return f"❌ 查詢概念股時發生錯誤: {e}"

    # ═══════════════════════════ Chips & Fundamentals ═════════════════════

    def get_chips_history(self, stock_id: str, days: int = 10) -> List[Dict]:
        return self.pipeline.get_chips_history(stock_id, days)

    def get_fundamentals_data(self, stock_id: str) -> Dict:
        yf_data = self.yf.get_stock_data(stock_id)
        avg_target = self.get_average_target_price(stock_id)

        return {
            "eps": yf_data.get('eps', 'N/A'),
            "roe": yf_data.get('roe', 'N/A'),
            "revenue_yoy": yf_data.get('revenue_growth', 'N/A'),
            "target_price": f"${avg_target:.1f}" if avg_target else "N/A",
            "estimated_eps": "N/A"
        }

    # ═══════════════════════════ Trust Buy Ratio ══════════════════════════

    def get_top_trust_buy_ratio(self, limit: int = 10) -> List[Dict]:
        return self.pipeline.get_top_trust_buy_ratio(limit)

    # ═══════════════════════════ Recommendations ═════════════════════════

    def get_recommendations(self, stock_id: str, limit: int = 3) -> Optional[str]:
        doc = self.mongo.hotwords_col.find_one(
            {'股票代號': stock_id}, sort=[('資料日期', -1)]
        )
        if not doc: return None

        concepts_str = doc.get('豐搜新聞概念股', '')
        if not concepts_str: return None

        concepts = [c.strip() for c in concepts_str.replace('、', ',').split(',')]
        if not concepts: return None

        query = {
            '股票代號': {'$ne': stock_id},
            '$or': [{'豐搜新聞概念股': {'$regex': c, '$options': 'i'}} for c in concepts if c]
        }
        related_docs = list(self.mongo.hotwords_col.find(query).sort('豐搜熱度', -1).limit(limit))
        if not related_docs: return None

        result = "\n🎯 **相關推薦**\n"
        seen = set()
        for doc in related_docs:
            sid = doc.get('股票代號')
            name = doc.get('股票名稱')
            concept = doc.get('豐搜新聞概念股', '')
            if sid and sid not in seen:
                result += f"- {name}({sid}) - {concept}\n"
                seen.add(sid)
        return result if seen else None

    # ═══════════════════════════ Earnings Call ════════════════════════════

    def get_earnings_call_insights(self, stock_id: str) -> Dict:
        return self.pipeline._fetch_earnings(stock_id)
