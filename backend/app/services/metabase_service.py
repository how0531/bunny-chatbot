"""
Metabase API integration service.
Provides methods to interact with Metabase for ClickHouse data access.
"""
import requests
import yfinance as yf
from typing import List, Dict, Any, Optional
from backend.app.core.config import Config
from backend.app.core.logger import get_logger
from backend.app.core.exceptions import APIError
from cachetools import TTLCache, cached

# Cache Setup
us_indices_cache = TTLCache(maxsize=100, ttl=300)
tw_indices_cache = TTLCache(maxsize=100, ttl=300)
flow_cache = TTLCache(maxsize=100, ttl=300)
score_cache = TTLCache(maxsize=100, ttl=300)

logger = get_logger(__name__)

class MetabaseService:
    """Service for interacting with Metabase API."""
    
    def __init__(self):
        """Initialize Metabase service with configuration."""
        self.base_url = Config.METABASE_URL
        self.username = Config.METABASE_USERNAME
        self.password = Config.METABASE_PASSWORD
        self.session_token = None
        logger.info("MetabaseService initialized")
        
    def login(self) -> str:
        """
        Login to Metabase and get session token.
        
        Returns:
            Session token
            
        Raises:
            APIError: If login fails
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/session",
                json={"username": self.username, "password": self.password},
                timeout=10
            )
            response.raise_for_status()
            self.session_token = response.json()["id"]
            logger.info("Successfully logged in to Metabase")
            return self.session_token
        except Exception as e:
            logger.error(f"Failed to login to Metabase: {e}")
            raise APIError(f"Metabase login failed: {e}")
    
    def _ensure_session(self) -> None:
        """Ensure we have a valid session token."""
        if not self.session_token:
            self.login()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        self._ensure_session()
        return {
            "X-Metabase-Session": self.session_token,
            "Content-Type": "application/json"
        }
    
    def execute_query(
        self, 
        database_id: int, 
        sql_query: str
    ) -> List[Dict[str, Any]]:
        """
        Execute a native SQL query through Metabase.
        
        Args:
            database_id: Metabase database ID
            sql_query: SQL query string
            
        Returns:
            Query results as list of dictionaries
            
        Raises:
            APIError: If query execution fails
        """
        try:
            payload = {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": sql_query
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/dataset",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Convert to list of dictionaries
            columns = [col["name"] for col in result["data"]["cols"]]
            rows = result["data"]["rows"]
            
            data = [dict(zip(columns, row)) for row in rows]
            
            logger.info(f"Query executed successfully, returned {len(data)} rows")
            return data
            
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise APIError(f"Metabase query failed: {e}")
    
    def get_databases(self) -> List[Dict[str, Any]]:
        """
        Get list of all databases in Metabase.
        
        Returns:
            List of database information
            
        Raises:
            APIError: If request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/database",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            
            databases = response.json()["data"]
            logger.info(f"Retrieved {len(databases)} databases")
            return databases
            
        except Exception as e:
            logger.error(f"Failed to get databases: {e}")

    def get_database_metadata(self, database_id: int) -> Dict[str, Any]:
        """
        Get metadata for a specific database, including tables.
        
        Args:
            database_id: Database ID
            
        Returns:
            Database metadata including tables
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/database/{database_id}/metadata",
                headers=self._get_headers(),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get metadata for database {database_id}: {e}")
            return {}

    def get_analyst_target_prices(
        self,
        stock_id: str,
        months: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get analyst target prices for a specific stock.
        
        Args:
            stock_id: Stock ID
            months: Number of months to look back (default: 3)
            
        Returns:
            List of analyst ratings and target prices
        """
        try:
            # First, find the ClickHouse database ID
            databases = self.get_databases()
            ch_db = next((db for db in databases if db['engine'] == 'clickhouse'), None)
            
            if not ch_db:
                logger.warning("No ClickHouse database found")
                return []
                
            database_id = ch_db['id']
            
            # Construct query
            query = f"""
            SELECT 
                `日期`,
                `股票代號`,
                `股票名稱`,
                `券商名稱`,
                `投資評等`,
                `目標價`
            FROM cmoney.`個股機構績效評等`
            WHERE `股票代號` = '{stock_id}'
              AND `日期` >= today() - INTERVAL {months} MONTH
              AND `目標價` > 0
            ORDER BY `日期` DESC
            """
            
            return self.execute_query(database_id, query)
            
        except Exception as e:
            logger.error(f"Failed to get analyst target prices for {stock_id}: {e}")
            return []

    def get_market_snapshot(self) -> Dict[str, Any]:
        """Get snapshot of major market indices."""
        return {
            "us_indices": self.get_us_indices(),
            "tw_indices": self.get_tw_indices()
        }

    def get_institutional_flow_aggregated(self) -> Dict[str, Any]:
        """Get aggregated institutional flow data."""
        return {
            "institutional_flow": self.get_institutional_flow(),
            "retail_futures": "暫無數據" # Placeholder
        }

    def get_sector_analysis_data(self, days: int = 2) -> Dict[str, Any]:
        """Get aggregated sector analysis data."""
        return {
            "strong_sectors": self.get_strong_sectors(days=days)
        }

    @cached(cache=score_cache)
    def get_market_hedge_history(self, days: int = 20) -> List[Dict[str, Any]]:
        """
        Get market hedge score history for trend visualization.
        """
        self._ensure_session()
        try:
            db_id = self._get_clickhouse_db_id()
            if not db_id: return []
            
            query = f"""
            SELECT toString(tdate) as date, value as score
            FROM quant.hedge_index_v1
            WHERE name = 'hedge_score'
            ORDER BY tdate DESC
            LIMIT {days}
            """
            return self.execute_query(db_id, query)
        except Exception as e:
            logger.error(f"Failed to get market hedge history: {e}")
            return []

    @cached(cache=us_indices_cache)
    def get_us_indices(self) -> List[Dict[str, Any]]:
        """
        Get latest US indices data (DJI, GSPC, IXIC, SOX).
        Source: cmoney.Mm 美股日收盤還原表排行
        """
        self._ensure_session()
        try:
            db_id = self._get_clickhouse_db_id()
            if not db_id: return []
            
            query = """
            SELECT `日期`, `代號`, `名稱`, `收盤價`, `漲跌幅`
            FROM cmoney.`Mm 美股日收盤還原表排行`
            WHERE `代號` IN ('#DJI', '#GSPC', '#IXIC', '#SOXX')
            ORDER BY `日期` DESC
            LIMIT 4
            """

            data = self.execute_query(db_id, query)
            if not data:
                logger.warning("Metabase returned empty US indices, triggering fallback")
                return self._get_fallback_us_indices()
            return data
        except Exception as e:
            logger.error(f"Failed to get US indices from Metabase: {e}")
            logger.info("Attempting fallback to yfinance for US indices")
            return self._get_fallback_us_indices()

    def _get_fallback_us_indices(self) -> List[Dict[str, Any]]:
        """Fallback to fetch US indices from yfinance."""
        indices = {
            '#DJI': '^DJI', 
            '#GSPC': '^GSPC', 
            '#IXIC': '^IXIC', 
            '#SOXX': '^SOX'
        }
        names = {
            '#DJI': '道瓊工業', 
            '#GSPC': '標普500', 
            '#IXIC': '納茲達克', 
            '#SOXX': '費城半導體'
        }
        results = []
        for code, ticker in indices.items():
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if len(hist) >= 2:
                    last = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    change = (last['Close'] - prev['Close']) / prev['Close'] * 100
                    results.append({
                        '代號': code,
                        '名稱': names[code],
                        '收盤價': round(last['Close'], 2),
                        '漲跌幅': round(change, 2),
                        'source': 'yfinance'
                    })
            except Exception as e:
                logger.error(f"YFinance fallback failed for {ticker}: {e}")
        return results

    @cached(cache=tw_indices_cache)
    def get_tw_index_history(self, days: int = 20) -> List[Dict[str, Any]]:
        """
        Get historical TW index data (Weighted Index).
        """
        self._ensure_session()
        try:
            db_id = self._get_clickhouse_db_id()
            if not db_id: return []
            
            query = f"""
            SELECT toString(`日期`) as date, `收盤價` as price
            FROM cmoney.`日收盤表排行`
            WHERE `代號` = 'TWA00'
            ORDER BY `日期` DESC
            LIMIT {days}
            """
            data = self.execute_query(db_id, query)
            if not data:
                logger.warning("Metabase returned empty TW index history, triggering fallback")
                return self._get_fallback_tw_index_history(days)
            return data
        except Exception as e:
            logger.error(f"Failed to get TW index history: {e}")
            return self._get_fallback_tw_index_history(days)

    def _get_fallback_tw_index_history(self, days: int = 20) -> List[Dict[str, Any]]:
        """Fallback to fetch TW index history from yfinance."""
        try:
            # Weighted Index is ^TWII
            hist = yf.Ticker("^TWII").history(period=f"{days+10}d")
            results = []
            for date, row in hist.tail(days).iterrows():
                results.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'price': round(row['Close'], 2)
                })
            return sorted(results, key=lambda x: x['date'], reverse=True)
        except Exception as e:
            logger.error(f"YFinance fallback failed for TW index history: {e}")
            return []

    @cached(cache=tw_indices_cache)
    def get_tw_indices(self) -> List[Dict[str, Any]]:
        """
        Get latest TW indices data (Weighted, OTC).
        Source: cmoney.日收盤表排行
        """
        self._ensure_session()
        try:
            db_id = self._get_clickhouse_db_id()
            if not db_id: return []
            
            query = """
            SELECT `日期`, `代號`, `名稱`, `收盤價`, `漲跌幅`
            FROM cmoney.`日收盤表排行`
            WHERE `代號` IN ('TWA00', 'TWC00')
            ORDER BY `日期` DESC
            LIMIT 2
            """

            data = self.execute_query(db_id, query)
            if not data:
                logger.warning("Metabase returned empty TW indices, triggering fallback")
                return self._get_fallback_tw_indices()
            return data
        except Exception as e:
            logger.error(f"Failed to get TW indices from Metabase: {e}")
            logger.info("Attempting fallback to yfinance for TW indices")
            return self._get_fallback_tw_indices()

    def _get_fallback_tw_indices(self) -> List[Dict[str, Any]]:
        """Fallback to fetch TW indices from yfinance."""
        indices = {
            'TWA00': '^TWII',  # Weighted Index
            'TWC00': '^TWO'    # OTC Index (Note: Yahoo support for TPEX is spotty, sometimes ^TWO)
        }
        names = {
            'TWA00': '加權指數',
            'TWC00': '櫃買指數'
        }
        results = []
        for code, ticker in indices.items():
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if len(hist) >= 2:
                    last = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    change = (last['Close'] - prev['Close']) / prev['Close'] * 100
                    results.append({
                        '代號': code,
                        '名稱': names[code],
                        '收盤價': round(last['Close'], 2),
                        '漲跌幅': round(change, 2),
                        'source': 'yfinance'
                    })
            except Exception as e:
                logger.error(f"YFinance fallback failed for {ticker}: {e}")
        return results

    @cached(cache=flow_cache)
    def get_institutional_flow(self) -> List[Dict[str, Any]]:
        """
        Get latest institutional buying/selling flow.
        Source: cmoney.三大法人買賣超
        """
        self._ensure_session()
        try:
            db_id = self._get_clickhouse_db_id()
            if not db_id: return []
            
            # Determine if we should exclude today's data (Before 17:00)
            from datetime import datetime
            
            date_condition = ""
            if datetime.now().hour < 17:
                today_str = datetime.now().strftime('%Y-%m-%d')
                date_condition = f"AND `日期` < '{today_str}'"

            query = f"""
            SELECT `日期`, `名稱` AS `法人名稱`, 
                   (COALESCE(`上市買賣超金額(百萬)`, 0) + COALESCE(`上櫃買賣超金額(百萬)`, 0)) / 100 AS `合計買賣超(億)`
            FROM cmoney.`三大法人買賣超`
            WHERE `代號` IN ('A001', 'A002', 'A003')
              AND `日期` = (SELECT MAX(`日期`) FROM cmoney.`三大法人買賣超` WHERE 1=1 {date_condition})
            """
            return self.execute_query(db_id, query)
        except Exception as e:
            logger.error(f"Failed to get institutional flow: {e}")
            return []

    @cached(cache=score_cache)
    def get_strong_sectors(self, days: int = 2, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Get top performing concept stock sectors.
        
        Args:
            days: Number of days to calculate return (default: 2)
            top_n: Number of top sectors to return (default: 3)
            
        Returns:
            List of stocks in top sectors with their returns
        """
        self._ensure_session()
        try:
            db_id = self._get_clickhouse_db_id()
            if not db_id: return []
            
            query = f"""
            WITH unique_dates AS (
                SELECT DISTINCT `日期`
                FROM cmoney.`日收盤還原表排行`
                ORDER BY `日期` DESC
                LIMIT {days + 1}
            ),
            latest_date AS (
                SELECT MAX(`日期`) as max_date FROM unique_dates
            ),
            past_date AS (
                SELECT MIN(`日期`) as past_date FROM unique_dates
            ),
            stock_returns AS (
                SELECT 
                    p_latest.`股票代號`,
                    (p_latest.`收盤價` / NULLIF(p_past.`收盤價`, 0) - 1) * 100 as return_pct
                FROM cmoney.`日收盤還原表排行` p_latest
                JOIN cmoney.`日收盤還原表排行` p_past 
                    ON p_latest.`股票代號` = p_past.`股票代號`
                WHERE p_latest.`日期` = (SELECT max_date FROM latest_date)
                  AND p_past.`日期` = (SELECT past_date FROM past_date)
                  AND p_past.`收盤價` > 0
            ),
            sector_avg AS (
                SELECT 
                    cs.tag as sector_name,
                    AVG(sr.return_pct) as avg_return,
                    COUNT(DISTINCT cs.code) as stock_count
                FROM public.concept_stocks cs
                JOIN stock_returns sr ON cs.code = sr.`股票代號`
                WHERE cs.source = 'statementdog'
                GROUP BY cs.tag
                HAVING COUNT(DISTINCT cs.code) > 3
                ORDER BY avg_return DESC
                LIMIT {top_n}
            ),
            top_sectors AS (
                SELECT sector_name FROM sector_avg
            )
            SELECT DISTINCT
                cs.tag as `概念名稱`,
                cs.code as `股票代號`,
                COALESCE(comp.`股票名稱`, '') as `股票名稱`,
                sr.return_pct as `漲跌幅`
            FROM public.concept_stocks cs
            JOIN top_sectors ts ON cs.tag = ts.sector_name
            JOIN stock_returns sr ON cs.code = sr.`股票代號`
            LEFT JOIN cmoney.`上市櫃公司基本資料` comp ON cs.code = comp.`股票代號`
            WHERE cs.source = 'statementdog'
            ORDER BY cs.tag, sr.return_pct DESC
            """
            
            return self.execute_query(db_id, query)
        except Exception as e:
            logger.error(f"Failed to get strong sectors: {e}")
            return []

    def get_concept_stocks(self, concept_name: str) -> List[Dict[str, Any]]:
        """
        Get stocks belonging to a specific concept/industry.
        
        Args:
            concept_name: Name of the concept (e.g., '封測')
            
        Returns:
            List of stocks in the concept
        """
        self._ensure_session()
        try:
            # Input validation
            if not concept_name or not concept_name.strip():
                logger.warning("Empty concept_name provided")
                return []
            
            # Sanitize input to prevent SQL injection
            sanitized_name = concept_name.strip().replace("'", "").replace(";", "").replace("--", "")
            
            if len(sanitized_name) > 50:
                logger.warning(f"Concept name too long: {len(sanitized_name)} chars")
                return []
            
            db_id = self._get_clickhouse_db_id()
            if not db_id: return []
            
            # Optimized query with exact match first, then fuzzy match
            # This allows index usage when exact match is found
            query = f"""
            SELECT 
                cs.tag as `概念名稱`,
                cs.code as `股票代號`,
                COALESCE(comp.`股票名稱`, '') as `股票名稱`,
                comp.`產業類別` as `產業`,
                comp.`本益比` as `本益比`,
                comp.`殖利率` as `殖利率`
            FROM public.concept_stocks cs
            LEFT JOIN cmoney.`上市櫃公司基本資料` comp ON cs.code = comp.`股票代號`
            WHERE cs.source = 'statementdog'
              AND (
                cs.tag = '{sanitized_name}'  -- Exact match (can use index)
                OR cs.tag ILIKE '%{sanitized_name}%'  -- Fuzzy match
              )
            ORDER BY 
                CASE WHEN cs.tag = '{sanitized_name}' THEN 0 ELSE 1 END,  -- Exact matches first
                cs.code
            LIMIT 50
            """
            
            results = self.execute_query(db_id, query)
            
            if results:
                logger.info(f"Found {len(results)} stocks for concept: {concept_name}")
            else:
                logger.info(f"No stocks found for concept: {concept_name}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get concept stocks for '{concept_name}': {type(e).__name__} - {e}")
            return []

    def _get_clickhouse_db_id(self) -> Optional[int]:
        """Helper to find ClickHouse DB ID."""
        databases = self.get_databases()
        ch_db = next((db for db in databases if db['engine'] == 'clickhouse'), None)
        return ch_db['id'] if ch_db else None
