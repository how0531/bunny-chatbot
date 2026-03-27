"""
Stock Enrichment Pipeline - Unified data aggregation from all sources.
Merges MongoDB, YFinance, ClickHouse, and AlphaMemo into a single enriched profile.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.app.core.config import Config
from backend.app.core.logger import get_logger
from backend.app.services.data_access import MongoDataAccess, YFinanceDataAccess
from backend.app.services.scoring_engine import BunnyGoodScorer
from backend.app.services.metabase_service import MetabaseService
import backend.app.core.constants as const

logger = get_logger(__name__)


class StockEnrichmentPipeline:
    """
    Given a stock_id, this pipeline fetches and fuses data from:
      1. MongoDB (news, hotwords, twstock, alphamemo)
      2. YFinance (price, PE, ROE, technicals)
      3. ClickHouse via Metabase (analyst targets, concept tags, industry peers)
    Returns a fully enriched profile for Sophia/Arthur to consume.
    """

    def __init__(self, mongo: MongoDataAccess, metabase: MetabaseService):
        self.mongo = mongo
        self.yf = YFinanceDataAccess
        self.metabase = metabase
        self.scorer = BunnyGoodScorer()

    def enrich(self, stock_id: str, include_peers: bool = True) -> Dict[str, Any]:
        """
        Full enrichment pipeline - parallel data fetching.
        Returns a comprehensive stock profile dictionary.
        """
        profile: Dict[str, Any] = {"stock_id": stock_id}

        # ── Parallel Phase: fetch all independent data sources ──
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(self.mongo.get_stock_name, stock_id): 'name',
                executor.submit(self._fetch_yfinance, stock_id): 'yfinance',
                executor.submit(self._fetch_technicals, stock_id): 'technicals',
                executor.submit(self._fetch_chips, stock_id): 'chips',
                executor.submit(self._fetch_news_and_sentiment, stock_id): 'news',
                executor.submit(self._fetch_hotword, stock_id): 'hotword',
            }

            for future in as_completed(futures):
                key = futures[future]
                try:
                    profile[key] = future.result()
                except Exception as e:
                    logger.error(f"Enrichment error [{key}]: {e}")
                    profile[key] = {}

        # ── Sequential Phase: things that depend on name/data ──
        stock_name = profile.get('name', '個股')
        profile['name'] = stock_name

        # Target Price (depends on metabase)
        try:
            target_data = self.metabase.get_analyst_target_prices(stock_id)
            prices = [float(item['目標價']) for item in (target_data or []) if item.get('目標價')]
            profile['avg_target_price'] = sum(prices) / len(prices) if prices else None
        except Exception as e:
            logger.error(f"Target price error: {e}")
            profile['avg_target_price'] = None

        # Score
        hotword_doc = profile.get('hotword', {}).get('doc')
        sentiment_score = profile.get('news', {}).get('sentiment_score', 0)
        days_diff = profile.get('hotword', {}).get('days_diff', 0)

        profile['score'] = self.scorer.calculate_score(
            hotword_doc=hotword_doc,
            sentiment_score=sentiment_score,
            days_diff=days_diff,
            yf_data=profile.get('yfinance', {}),
            tech_data=profile.get('technicals', {}),
            chips_data=profile.get('chips', {}),
            target_price=profile.get('avg_target_price'),
        )
        profile['score_stars'] = self.scorer.score_to_stars(profile['score'])
        profile['score_emoji'] = self.scorer.score_to_emoji(profile['score'])

        # Peer Comparison (optional, can be slow)
        if include_peers:
            try:
                profile['peers'] = self._fetch_peers(stock_id, profile.get('yfinance', {}))
            except Exception as e:
                logger.error(f"Peer comparison error: {e}")
                profile['peers'] = []

        # Earnings Call
        try:
            profile['earnings'] = self._fetch_earnings(stock_id)
        except Exception as e:
            logger.error(f"Earnings error: {e}")
            profile['earnings'] = {'found': False}

        return profile

    # ════════════════════════════ Data Fetchers ════════════════════════════

    def _fetch_yfinance(self, stock_id: str) -> Dict:
        return self.yf.get_stock_data(stock_id)

    def _fetch_technicals(self, stock_id: str) -> Dict:
        return self.yf.get_technical_data(stock_id)

    def _fetch_chips(self, stock_id: str) -> Dict:
        """Fetch institutional flow with consecutive buy days."""
        tw_doc = self.mongo.get_twstock_doc(stock_id)
        if not tw_doc:
            return {}

        chips_node = tw_doc.get('籌碼面', {})
        buysell = chips_node.get(const.FIELD_BUY_SELL, {})
        if not buysell:
            buysell = tw_doc.get(const.FIELD_BUY_SELL, {})

        def parse_value(raw):
            try:
                return int(float(str(raw).replace(',', '').replace('張', '')))
            except (ValueError, TypeError):
                return 0

        foreign = parse_value(buysell.get(const.FIELD_FOREIGN_BUY_SELL, 0))
        trust = parse_value(buysell.get(const.FIELD_TRUST_BUY_SELL, 0))

        # Calculate consecutive buy days
        foreign_days = self.mongo.calculate_consecutive_buy_days(stock_id, 'foreign')
        trust_days = self.mongo.calculate_consecutive_buy_days(stock_id, 'trust')

        return {
            'foreign_net': foreign,
            'trust_net': trust,
            'foreign_consecutive_days': foreign_days,
            'trust_consecutive_days': trust_days,
            'date': tw_doc.get(const.FIELD_DATA_DATE, ''),
        }

    def _fetch_news_and_sentiment(self, stock_id: str) -> Dict:
        """Fetch news list + calculate sentiment."""
        stock_name = self.mongo.get_stock_name(stock_id)
        news_list = self.mongo.get_recent_news(stock_id, stock_name, limit=5)
        sentiment_score, indicator = self.mongo.calculate_sentiment_score(stock_id, stock_name)
        return {
            'news_list': news_list,
            'sentiment_score': sentiment_score,
            'sentiment_indicator': indicator,
        }

    def _fetch_hotword(self, stock_id: str) -> Dict:
        """Fetch hotword data + freshness check."""
        doc = self.mongo.get_hotword_doc(stock_id)
        if not doc:
            return {'doc': None, 'days_diff': 999}

        days_diff = 0
        date_str = doc.get('資料日期', '')
        try:
            data_date = datetime.strptime(date_str, "%Y-%m-%d")
            days_diff = (datetime.now() - data_date).days
        except (ValueError, TypeError):
            pass

        return {
            'doc': doc,
            'days_diff': days_diff,
            'date': date_str,
            'rise_reason': doc.get('股價上漲原因(熱度起始日)', ''),
            'market_news': doc.get('市場傳出消息(熱度起始日)', ''),
            'concepts': doc.get('豐搜新聞概念股', ''),
        }

    def _fetch_peers(self, stock_id: str, yf_data: Dict) -> List[Dict]:
        """Fetch peer comparison from same industry via ClickHouse."""
        try:
            db_id = self.metabase._get_clickhouse_db_id()
            if not db_id:
                return []

            # Get industry of the current stock
            query = f"""
            SELECT `產業類別`
            FROM cmoney.`上市櫃公司基本資料`
            WHERE `股票代號` = '{stock_id}'
            LIMIT 1
            """
            result = self.metabase.execute_query(db_id, query)
            if not result:
                return []

            industry = result[0].get('產業類別', '')
            if not industry:
                return []

            # Fetch top peers by the same industry
            peer_query = f"""
            SELECT
                `股票代號`,
                `股票名稱`,
                `產業類別`,
                `本益比`,
                `殖利率`,
                `股價淨值比`
            FROM cmoney.`上市櫃公司基本資料`
            WHERE `產業類別` = '{industry}'
              AND `股票代號` != '{stock_id}'
              AND `本益比` > 0
            ORDER BY `本益比` ASC
            LIMIT 5
            """
            peers = self.metabase.execute_query(db_id, peer_query)
            return peers or []
        except Exception as e:
            logger.error(f"Peer query error: {e}")
            return []

    def _fetch_earnings(self, stock_id: str) -> Dict:
        """Get earnings call data from cache or scraper."""
        cached = self.mongo.get_cached_alphamemo(stock_id)
        if cached:
            return {
                'found': True,
                'date': cached.get('date', ''),
                'highlights': '\n'.join(f"• {h}" for h in cached.get('highlights', [])),
                'revenue': '\n'.join(f"• {r}" for r in cached.get('revenue', [])),
                'profit': '\n'.join(f"• {p}" for p in cached.get('profit', [])),
                'outlook': '\n'.join(f"• {o}" for o in cached.get('outlook', [])),
            }

        # Try scraping
        try:
            import asyncio
            from backend.app.services.alphamemo_scraper import AlphaMemoScraper

            scraper = AlphaMemoScraper()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                transcripts = loop.run_until_complete(
                    scraper.get_recent_transcripts(stock_code=stock_id, limit=1)
                )
                if transcripts:
                    latest = transcripts[0]
                    summary_url = latest.get('summary_url')
                    if summary_url:
                        summary = loop.run_until_complete(
                            scraper.get_transcript_summary(summary_url)
                        )
                        # Cache to MongoDB
                        self.mongo.save_alphamemo(stock_id, {
                            'stock_code': stock_id,
                            'stock_name': latest.get('stock_name', ''),
                            'date': latest.get('date', ''),
                            'highlights': summary.get('highlights', []),
                            'revenue': summary.get('revenue', []),
                            'profit': summary.get('profit', []),
                            'outlook': summary.get('outlook', []),
                            'source': 'AlphaMemo'
                        })
                        return {
                            'found': True,
                            'date': latest.get('date', ''),
                            'highlights': '\n'.join(f"• {h}" for h in summary.get('highlights', [])),
                            'revenue': '\n'.join(f"• {r}" for r in summary.get('revenue', [])),
                            'profit': '\n'.join(f"• {p}" for p in summary.get('profit', [])),
                            'outlook': '\n'.join(f"• {o}" for o in summary.get('outlook', [])),
                        }
            finally:
                loop.close()
        except Exception as e:
            logger.debug(f"AlphaMemo scraping skipped for {stock_id}: {e}")

        # News Fallback
        try:
            from backend.app.core.search import search_web, format_search_results
            stock_name = self.mongo.get_stock_name(stock_id)
            query = f"{stock_id} {stock_name} 法說會 營收 展望"
            results = search_web(query)
            if results:
                return {
                    'found': True,
                    'date': datetime.now().strftime("%Y-%m-%d"),
                    'highlights': format_search_results(results),
                    'source': 'News Fallback'
                }
        except Exception:
            pass

        return {'found': False}

    # ════════════════════════════ Chips History (for charts) ═══════════════

    def get_chips_history(self, stock_id: str, days: int = 10) -> List[Dict]:
        """Fetch chart data for chips flow visualization."""
        docs = self.mongo.get_twstock_history(stock_id, days=days)
        history = []
        cum_f, cum_t = 0, 0

        for doc in reversed(docs):
            chips_node = doc.get('籌碼面', {})
            buysell = chips_node.get(const.FIELD_BUY_SELL, {})
            if not buysell:
                buysell = doc.get(const.FIELD_BUY_SELL, {})

            try:
                f_raw = str(buysell.get(const.FIELD_FOREIGN_BUY_SELL, 0)).replace(',', '').replace('張', '')
                t_raw = str(buysell.get(const.FIELD_TRUST_BUY_SELL, 0)).replace(',', '').replace('張', '')
                foreign = int(float(f_raw))
                trust = int(float(t_raw))
            except (ValueError, TypeError):
                foreign, trust = 0, 0

            cum_f += foreign
            cum_t += trust

            history.append({
                "date": doc.get(const.FIELD_DATA_DATE, "").replace("-", "/")[5:],
                "foreign": foreign,
                "trust": trust,
                "cum_foreign": cum_f,
                "cum_trust": cum_t,
            })
        return history

    # ════════════════════════════ Trust Buy Ratio ═════════════════════════

    def get_top_trust_buy_ratio(self, limit: int = 10) -> List[Dict]:
        """Calculate top stocks by investment trust buy ratio."""
        latest_date = self.mongo.get_latest_twstock_date()
        if not latest_date:
            return []

        docs = self.mongo.get_all_trust_buyers(latest_date)
        ratios = []

        for doc in docs:
            stock_id = doc.get(const.FIELD_STOCK_CODE)
            if not stock_id:
                continue

            buysell = doc.get('籌碼面', {}).get(const.FIELD_BUY_SELL, {})
            trust_raw = str(buysell.get(const.FIELD_TRUST_BUY_SELL, 0)).replace(',', '').replace('張', '')
            try:
                trust_buy_lots = float(trust_raw)
            except (ValueError, TypeError):
                continue
            if trust_buy_lots <= 0:
                continue

            shares = self.yf.get_shares_outstanding(stock_id)
            if not shares:
                continue

            total_lots = shares / 1000
            ratio = (trust_buy_lots / total_lots) * 100

            ratios.append({
                "stock_id": stock_id,
                "name": doc.get(const.FIELD_TWSTOCK_NAME, "未知"),
                "trust_buy_lots": int(trust_buy_lots),
                "ratio": round(ratio, 4),
            })

        return sorted(ratios, key=lambda x: x['ratio'], reverse=True)[:limit]
