"""
Data Access Layer - Unified MongoDB & YFinance data access.
Extracted from stock_service.py for single-responsibility.
"""
import re
import yfinance as yf
from pymongo import MongoClient
from collections import Counter
from datetime import datetime, timedelta
from cachetools import TTLCache, cached
from typing import Optional, Dict, List, Any

from backend.app.core.config import Config
from backend.app.core.logger import get_logger
import backend.app.core.constants as const

logger = get_logger(__name__)

# --- Caches ---
name_cache = TTLCache(maxsize=200, ttl=Config.CACHE_NAME_TTL)
yfinance_cache = TTLCache(maxsize=200, ttl=Config.CACHE_YFINANCE_TTL)
concept_cache = TTLCache(maxsize=50, ttl=Config.CACHE_CONCEPT_TTL)
search_memory_cache = TTLCache(maxsize=50, ttl=86400)


class MongoDataAccess:
    """Encapsulates all MongoDB read/write operations."""

    def __init__(self):
        try:
            self.client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=Config.MONGODB_TIMEOUT,
                maxPoolSize=Config.MONGODB_MAX_POOL_SIZE,
                minPoolSize=Config.MONGODB_MIN_POOL_SIZE,
            )
            # Collections
            self.news_col = self.client[const.DB_SINOPAC_NEWS][const.COLL_NEWS_SENTIMENT]
            self.hotwords_col = self.client[const.DB_SINOPAC_HOTWORDS][const.COLL_HOTWORDS_LEARNINGPOST]
            self.twstock_col = self.client[const.DB_TWSTOCK][const.COLL_TWSTOCK]
            self.alphamemo_col = self.client['ai_assistant']['alphamemo_transcripts']
            logger.info("MongoDataAccess initialized")
        except Exception as e:
            logger.error(f"MongoDataAccess init failed: {e}")
            raise

    # ─────────────────────────── Stock Name ───────────────────────────

    @cached(cache=name_cache)
    def get_stock_name(self, stock_id: str) -> str:
        """Extract stock name from news titles, hotwords, or twstock."""
        try:
            # 1. Try news collection
            docs = list(self.news_col.find(
                {const.FIELD_STOCK_ID: stock_id}
            ).sort(const.FIELD_PUBLISH_DATE, -1).limit(const.LIMIT_NEWS_TITLE_SEARCH))

            pattern = re.compile(const.PATTERN_STOCK_NAME.format(stock_id=stock_id))
            candidate_names = []

            for doc in docs:
                for source in [doc.get(const.FIELD_NEWS_TITLE, ''),
                               doc.get(const.FIELD_NEWS_CONTENT, '')]:
                    if not source:
                        continue
                    matches = pattern.findall(source)
                    for m in matches:
                        cleaned = m
                        for p in const.STOCK_NAME_PREFIXES:
                            cleaned = re.sub(rf'.*{p}', '', cleaned)
                        if 1 < len(cleaned) <= 5:
                            candidate_names.append(cleaned)
                        elif len(cleaned) > 5:
                            candidate_names.append(cleaned[-3:])

            if candidate_names:
                valid = [n for n in candidate_names
                         if const.MIN_STOCK_NAME_LENGTH <= len(n) <= const.MAX_STOCK_NAME_LENGTH]
                if valid:
                    return Counter(valid).most_common(1)[0][0]
                return candidate_names[0]

            # 2. Fallback: hotwords
            hw_doc = self.hotwords_col.find_one({const.FIELD_STOCK_ID: stock_id})
            if hw_doc and const.FIELD_STOCK_NAME in hw_doc:
                return hw_doc[const.FIELD_STOCK_NAME]

            # 3. Fallback: twstock
            tw_doc = self.twstock_col.find_one({const.FIELD_STOCK_CODE: stock_id})
            if tw_doc and const.FIELD_TWSTOCK_NAME in tw_doc:
                return tw_doc[const.FIELD_TWSTOCK_NAME]

            return const.FALLBACK_STOCK_NAME
        except Exception as e:
            logger.error(f"get_stock_name error for {stock_id}: {e}")
            return const.FALLBACK_STOCK_NAME

    # ─────────────────────────── ID Lookup ────────────────────────────

    def get_id_by_name(self, name: str) -> Optional[str]:
        """Find stock ID by name (exact or prefix match)."""
        try:
            doc = self.hotwords_col.find_one({const.FIELD_STOCK_NAME: name})
            if doc:
                return doc.get(const.FIELD_STOCK_ID)
            doc = self.hotwords_col.find_one(
                {const.FIELD_STOCK_NAME: {'$regex': f"^{name}"}}
            )
            if doc:
                return doc.get(const.FIELD_STOCK_ID)
            return None
        except Exception as e:
            logger.error(f"get_id_by_name error '{name}': {e}")
            return None

    def extract_stock_id(self, text: str) -> Optional[str]:
        """Extract stock ID from natural language text."""
        matches = re.findall(r'\b(\d{4})\b', text)
        if matches:
            return matches[0]
        words = re.findall(r'[\u4e00-\u9fa5]{2,5}', text)
        for word in words:
            for i in range(len(word), 1, -1):
                found_id = self.get_id_by_name(word[:i])
                if found_id:
                    return found_id
        return None

    # ────────────────────────── News Queries ──────────────────────────

    def get_recent_news(self, stock_id: str, stock_name: str = "",
                        limit: int = 10, strict: bool = False) -> List[Dict]:
        """Get recent news filtered by stock relevance."""
        docs = list(self.news_col.find(
            {'代號': stock_id}
        ).sort('發布日期時間', -1).limit(limit * 2))

        results = []
        for doc in docs:
            title = doc.get('新聞標題', '')
            if stock_id not in title and stock_name not in title:
                continue
            results.append({
                "title": title,
                "summary": doc.get('新聞內容', '')[:200],
                "sentiment": doc.get('新聞情緒', ''),
                "date": doc.get('發布日期時間', '')
            })
            if len(results) >= limit:
                break
        return results

    def calculate_sentiment_score(self, stock_id: str, stock_name: str) -> tuple:
        """Calculate sentiment score and indicator from news."""
        docs = list(self.news_col.find(
            {'代號': stock_id}
        ).sort('發布日期時間', -1).limit(10))

        sentiment_score = 0
        total_weight = 0

        for doc in docs:
            title = doc.get('新聞標題', '')
            if stock_id not in title and stock_name not in title:
                continue

            s_val = doc.get('新聞情緒', '')
            weight = 0
            if '極正面' in s_val: weight = 2
            elif '正面' in s_val: weight = 1
            elif '極負面' in s_val: weight = -2
            elif '負面' in s_val: weight = -1

            sentiment_score += weight
            if weight != 0:
                total_weight += 1
            if total_weight >= 5:
                break

        indicator = "⚪"
        if total_weight > 0:
            avg = sentiment_score / total_weight
            if avg >= 1.5: indicator = "🔥 (極度看多)"
            elif avg >= 0.5: indicator = "🟢 (看多)"
            elif avg <= -1.5: indicator = "💀 (極度看空)"
            elif avg <= -0.5: indicator = "🔴 (看空)"
            else: indicator = "🟡 (中立)"

        return sentiment_score, indicator

    # ────────────────────────── Hotwords ──────────────────────────────

    def get_latest_hotwords_date(self) -> Optional[str]:
        """Find the most recent date in hotwords collection."""
        try:
            doc = self.hotwords_col.find_one(sort=[(const.FIELD_DATA_DATE, -1)])
            return doc.get(const.FIELD_DATA_DATE) if doc else None
        except Exception as e:
            logger.error(f"get_latest_hotwords_date error: {e}")
            return None

    def get_hotword_doc(self, stock_id: str, target_date: str = None) -> Optional[Dict]:
        """Get hotword document for a stock, optionally filtered by exact date."""
        query = {const.FIELD_STOCK_ID: stock_id}
        if target_date:
            query[const.FIELD_DATA_DATE] = target_date
        return self.hotwords_col.find_one(
            query,
            sort=[(const.FIELD_DATA_DATE, -1)]
        )

    def get_historical_analysis(self, stock_id: str, limit: int = 3) -> Optional[str]:
        """Get historical hotspot analysis."""
        docs = list(self.hotwords_col.find(
            {'股票代號': stock_id}
        ).sort('資料日期', -1).limit(limit))

        if not docs:
            return None

        result = f"📈 **{stock_id} 歷史分析** (近 {len(docs)} 次)\n\n"
        for idx, doc in enumerate(docs, 1):
            date = doc.get('資料日期', '')
            rise_reason = doc.get('股價上漲原因(熱度起始日)', '')
            concepts = doc.get('豐搜新聞概念股', '')
            result += f"### {idx}. {date}\n"
            if concepts: result += f"概念: {concepts}\n"
            if rise_reason: result += f"原因: {rise_reason}\n"
            result += "\n"
        return result

    @cached(cache=concept_cache)
    def search_by_concept(self, keyword: str) -> List[str]:
        """Search stocks by concept keyword in hotwords."""
        try:
            query = {
                '$or': [
                    {const.FIELD_CONCEPTS: {'$regex': keyword, '$options': 'i'}},
                    {const.FIELD_KEYWORDS: {'$regex': keyword, '$options': 'i'}}
                ]
            }
            docs = list(self.hotwords_col.find(query).sort(
                const.FIELD_HEAT, -1
            ).limit(const.LIMIT_CONCEPT_SEARCH_RESULTS))

            results, seen = [], set()
            for doc in docs:
                sid = doc.get(const.FIELD_STOCK_ID)
                name = doc.get(const.FIELD_STOCK_NAME)
                if sid and sid not in seen:
                    results.append(f"{name}({sid})")
                    seen.add(sid)
            return results
        except Exception as e:
            logger.error(f"search_by_concept error '{keyword}': {e}")
            return []

    # ────────────────────────── TWStock ───────────────────────────────

    def get_twstock_doc(self, stock_id: str) -> Optional[Dict]:
        """Get latest twstock document."""
        return self.twstock_col.find_one(
            {const.FIELD_STOCK_CODE: stock_id},
            sort=[(const.FIELD_DATA_DATE, -1)]
        )

    def get_twstock_history(self, stock_id: str, days: int = 20) -> List[Dict]:
        """Get twstock history for chips calculations."""
        return list(self.twstock_col.find(
            {const.FIELD_STOCK_CODE: stock_id}
        ).sort(const.FIELD_DATA_DATE, -1).limit(days))

    def get_latest_twstock_date(self) -> Optional[str]:
        """Find the most recent date in twstock collection."""
        try:
            doc = self.twstock_col.find_one(sort=[(const.FIELD_DATA_DATE, -1)])
            return doc.get(const.FIELD_DATA_DATE) if doc else None
        except Exception as e:
            logger.error(f"get_latest_twstock_date error: {e}")
            return None

    def get_all_trust_buyers(self, date: str) -> List[Dict]:
        """Get all stocks with trust buy on a specific date."""
        query = {
            const.FIELD_DATA_DATE: date,
            "籌碼面.買賣超.投信買賣超": {"$exists": True}
        }
        return list(self.twstock_col.find(query))

    # ────────────────────────── Institutional Flow Streak ─────────────

    def calculate_consecutive_buy_days(self, stock_id: str, institution: str = 'foreign', days: int = 20) -> int:
        """
        Calculate consecutive buy days for a given institution.
        institution: 'foreign' or 'trust'
        """
        field_map = {
            'foreign': const.FIELD_FOREIGN_BUY_SELL,
            'trust': const.FIELD_TRUST_BUY_SELL
        }
        field_name = field_map.get(institution, const.FIELD_FOREIGN_BUY_SELL)

        docs = self.get_twstock_history(stock_id, days=days)
        consecutive = 0

        for doc in docs:  # Already sorted newest-first
            chips_node = doc.get('籌碼面', {})
            buysell = chips_node.get(const.FIELD_BUY_SELL, {})
            if not buysell:
                buysell = doc.get(const.FIELD_BUY_SELL, {})

            try:
                raw = str(buysell.get(field_name, 0)).replace(',', '').replace('張', '')
                value = float(raw)
            except (ValueError, TypeError):
                value = 0

            if value > 0:
                consecutive += 1
            else:
                break

        return consecutive

    # ────────────────────────── AlphaMemo ─────────────────────────────

    def get_cached_alphamemo(self, stock_id: str) -> Optional[Dict]:
        """Get cached AlphaMemo earnings if fresh (<7 days)."""
        try:
            cached = self.alphamemo_col.find_one(
                {'stock_code': stock_id},
                sort=[('date', -1)]
            )
            if cached:
                scraped_at = cached.get('scraped_at', datetime.min)
                if isinstance(scraped_at, datetime) and (datetime.now() - scraped_at).days < 7:
                    return cached
        except Exception as e:
            logger.error(f"get_cached_alphamemo error: {e}")
        return None

    def save_alphamemo(self, stock_id: str, data: Dict):
        """Cache AlphaMemo data to MongoDB."""
        try:
            self.alphamemo_col.update_one(
                {'stock_code': stock_id},
                {'$set': {**data, 'scraped_at': datetime.now()}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"save_alphamemo error: {e}")

    # ────────────────────────── Search Cache ──────────────────────────

    def get_search_cache(self, query: str) -> Optional[Dict]:
        return search_memory_cache.get(query)

    def save_search_cache(self, query: str, results: Dict):
        search_memory_cache[query] = results


class YFinanceDataAccess:
    """Encapsulates Yahoo Finance data fetching with caching and fallback."""

    @staticmethod
    @cached(cache=yfinance_cache)
    def get_stock_data(stock_id: str) -> Dict[str, Any]:
        """Fetch comprehensive stock data from yfinance (TSE/OTC auto-detect)."""
        try:
            ticker = yf.Ticker(f"{stock_id}.TW")
            info = ticker.info

            if not info or ('currentPrice' not in info and 'regularMarketPrice' not in info):
                ticker = yf.Ticker(f"{stock_id}.TWO")
                info = ticker.info

            data = {}

            # Price
            data['price'] = info.get('currentPrice') or info.get('regularMarketPrice')

            # PE
            pe = info.get('trailingPE') or info.get('forwardPE')
            if pe is not None:
                data['pe'] = f"{pe:.2f}"

            # Dividend Yield
            dy = info.get('dividendYield')
            if dy is not None:
                val = dy * 100 if dy < 0.5 else dy
                data['yield_rate'] = f"{val:.2f}%"

            # Market Cap
            mcap = info.get('marketCap')
            if mcap:
                if mcap >= 1e12: data['mkt_cap'] = f"{mcap / 1e12:.2f} 兆"
                elif mcap >= 1e8: data['mkt_cap'] = f"{mcap / 1e8:.2f} 億"
                else: data['mkt_cap'] = str(mcap)

            # PB, ROE, EPS
            if 'priceToBook' in info: data['pb'] = f"{info['priceToBook']:.2f}"
            if 'returnOnEquity' in info and info['returnOnEquity']:
                data['roe'] = f"{info['returnOnEquity'] * 100:.2f}%"
            if 'trailingEps' in info: data['eps'] = f"{info['trailingEps']:.2f}"

            # 52 Week Range
            if 'fiftyTwoWeekLow' in info and 'fiftyTwoWeekHigh' in info:
                data['52w_range'] = f"${info['fiftyTwoWeekLow']} - ${info['fiftyTwoWeekHigh']}"

            # Beta
            if 'beta' in info and info['beta']:
                data['beta'] = f"{info['beta']:.2f}"

            # Revenue Growth
            if 'revenueGrowth' in info and info['revenueGrowth']:
                data['revenue_growth'] = f"{info['revenueGrowth'] * 100:.1f}%"

            # Industry & Sector
            data['industry'] = info.get('industry', '')
            data['sector'] = info.get('sector', '')

            # Shares Outstanding (for ratio calculations)
            data['shares_outstanding'] = info.get('sharesOutstanding')

            return data
        except Exception as e:
            logger.error(f"YFinance error for {stock_id}: {e}")
            return {}

    @staticmethod
    def get_technical_data(stock_id: str, period: str = "3mo") -> Dict[str, Any]:
        """
        Calculate technical indicators from price history.
        Returns MA, RSI, KD data without TA-Lib dependency.
        """
        try:
            ticker = yf.Ticker(f"{stock_id}.TW")
            hist = ticker.history(period=period)

            if hist.empty:
                ticker = yf.Ticker(f"{stock_id}.TWO")
                hist = ticker.history(period=period)

            if hist.empty or len(hist) < 20:
                return {}

            close = hist['Close']
            data = {}

            # Current Price
            data['current_price'] = round(close.iloc[-1], 2)

            # Moving Averages
            if len(close) >= 5:
                data['ma5'] = round(close.rolling(5).mean().iloc[-1], 2)
            if len(close) >= 20:
                data['ma20'] = round(close.rolling(20).mean().iloc[-1], 2)
            if len(close) >= 60:
                data['ma60'] = round(close.rolling(60).mean().iloc[-1], 2)

            # MA Position (above/below)
            price = close.iloc[-1]
            data['above_ma5'] = price > data.get('ma5', 0)
            data['above_ma20'] = price > data.get('ma20', 0)
            data['above_ma60'] = price > data.get('ma60', float('inf'))

            # MA Arrangement (bullish: ma5 > ma20 > ma60)
            ma5 = data.get('ma5', 0)
            ma20 = data.get('ma20', 0)
            ma60 = data.get('ma60', 0)
            if ma5 and ma20 and ma60:
                data['ma_bullish'] = ma5 > ma20 > ma60
                data['ma_bearish'] = ma5 < ma20 < ma60
            else:
                data['ma_bullish'] = None
                data['ma_bearish'] = None

            # RSI (14-period)
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta.where(delta < 0, 0.0))

            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()

            rs = avg_gain / avg_loss.replace(0, float('nan'))
            rsi = 100 - (100 / (1 + rs))
            if not rsi.empty and not rsi.isna().iloc[-1]:
                data['rsi'] = round(rsi.iloc[-1], 2)
                data['rsi_overbought'] = data['rsi'] > 70
                data['rsi_oversold'] = data['rsi'] < 30

            # KD (Stochastic 9,3,3)
            if len(close) >= 9:
                low_9 = hist['Low'].rolling(9).min()
                high_9 = hist['High'].rolling(9).max()
                rsv = (close - low_9) / (high_9 - low_9).replace(0, float('nan')) * 100

                k = rsv.ewm(com=2, adjust=False).mean()
                d = k.ewm(com=2, adjust=False).mean()

                if not k.isna().iloc[-1]:
                    data['k_value'] = round(k.iloc[-1], 2)
                    data['d_value'] = round(d.iloc[-1], 2)
                    data['kd_golden_cross'] = (k.iloc[-1] > d.iloc[-1]) and (k.iloc[-2] <= d.iloc[-2]) if len(k) >= 2 else False

            # Volume analysis
            vol = hist['Volume']
            if len(vol) >= 5:
                avg_vol = vol.rolling(5).mean().iloc[-1]
                last_vol = vol.iloc[-1]
                data['volume_ratio'] = round(last_vol / avg_vol, 2) if avg_vol > 0 else 1.0

            return data
        except Exception as e:
            logger.error(f"Technical data error for {stock_id}: {e}")
            return {}

    @staticmethod
    def get_shares_outstanding(stock_id: str) -> Optional[int]:
        """Fetch shares outstanding."""
        try:
            ticker = yf.Ticker(f"{stock_id}.TW")
            shares = ticker.info.get('sharesOutstanding')
            if not shares:
                ticker = yf.Ticker(f"{stock_id}.TWO")
                shares = ticker.info.get('sharesOutstanding')
            return shares
        except Exception as e:
            logger.warning(f"get_shares_outstanding error {stock_id}: {e}")
            return None
