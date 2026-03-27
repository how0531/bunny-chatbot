import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

from backend.app.core.config import Config
from backend.app.core.logger import get_logger
from backend.app.services.stock_service import StockService
from backend.app.services.metabase_service import MetabaseService

logger = get_logger(__name__)


class RuleParser:
    """Parses natural language stock screening rules into structured conditions."""
    
    SUPPORTED_FACTORS = {
        # 籌碼面 (Chips)
        "trust_buy_ratio": {"name": "投信買超比重", "unit": "%", "source": "mongodb"},
        "foreign_net_buy": {"name": "外資買賣超", "unit": "張", "source": "mongodb"},
        "foreign_buy_days": {"name": "外資連買天數", "unit": "天", "source": "mongodb"},
        "trust_buy_days": {"name": "投信連買天數", "unit": "天", "source": "mongodb"},
        
        # 技術面 (Technical)
        "price_change_pct": {"name": "漲跌幅", "unit": "%", "source": "yfinance"},
        "volume_ratio": {"name": "成交量倍數", "unit": "倍", "source": "yfinance"},
        "above_ma20": {"name": "站上月線", "unit": "bool", "source": "yfinance"},
        "above_ma60": {"name": "站上季線", "unit": "bool", "source": "yfinance"},
        
        # 基本面 (Fundamentals)
        "pe_ratio": {"name": "本益比", "unit": "", "source": "metabase"},
        "dividend_yield": {"name": "殖利率", "unit": "%", "source": "metabase"},
        "revenue_growth": {"name": "營收成長率", "unit": "%", "source": "metabase"},
    }
    
    def __init__(self):
        self.model = None
        logger.info("RuleParser initialized with Regex-based parser (no LLM required)")
    
    def parse(self, user_query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured conditions.
        Uses regex-based parser for reliable, offline operation.

        Args:
            user_query: Natural language screening rule

        Returns:
            Dictionary with parsed conditions
        """
        logger.info(f"Parsing query with Regex parser: {user_query}")
        return self._parse_fallback(user_query)

    def _parse_fallback(self, query: str) -> Dict[str, Any]:
        """
        Regex-based fallback parser for basic queries when LLM is unavailable.
        Supports patterns like "投信買超比重 > 0.3%" or "本益比 < 20".
        """
        conditions = []
        
        # Build mapping for factor names
        name_map = {}
        for key, info in self.SUPPORTED_FACTORS.items():
            name_map[info["name"]] = key
            name_map[key] = key
        
        # Create a regex pattern that matches any of the supported factor names
        # Sort by length desc to match longest names first (e.g. avoid partial matches if names overlap)
        sorted_names = sorted(name_map.keys(), key=len, reverse=True)
        factors_pattern = "|".join(map(re.escape, sorted_names))
        
        # Regex to find: (Factor) (Operator) (Value) (Optional %)
        # Allow flexible spacing
        pattern = f"({factors_pattern})\\s*(>=|<=|>|<|==|!=)\\s*([0-9.]+)(?:%)?"
        
        matches = re.finditer(pattern, query)
        
        for match in matches:
            name, op, val = match.groups()
            factor_key = name_map.get(name)
            
            if factor_key:
                try:
                    conditions.append({
                        "factor": factor_key,
                        "operator": op,
                        "value": float(val)
                    })
                except ValueError:
                    continue
        
        if conditions:
            logger.info(f"Fallback parser found {len(conditions)} conditions")
            return {
                "conditions": conditions,
                "sort_by": conditions[0]["factor"], # Default sort by first condition
                "sort_order": "desc",
                "limit": 10
            }
        
        return {"error": "無法解析規則，且 API 暫時不可用。請嘗試簡化語句，例如「投信買超比重 > 0.5」。"}


class RuleExecutor:
    """Executes parsed rules against data sources."""
    
    def __init__(self, stock_service: StockService = None):
        self.stock_service = stock_service or StockService()
        self.metabase = MetabaseService()
        logger.info("RuleExecutor initialized")
    
    def execute(self, parsed_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute parsed rules and return matching stocks.
        
        Args:
            parsed_rules: Output from RuleParser.parse()
            
        Returns:
            List of stocks matching all conditions
        """
        if "error" in parsed_rules:
            return []
        
        conditions = parsed_rules.get("conditions", [])
        sort_by = parsed_rules.get("sort_by", "trust_buy_ratio")
        sort_order = parsed_rules.get("sort_order", "desc")
        limit = parsed_rules.get("limit", 10)
        
        if not conditions:
            return []
        
        # Step 1: Get base stock universe
        # Start with trust buy ratio data as it's our most complete dataset
        base_stocks = self._get_base_universe()
        
        if not base_stocks:
            logger.warning("No base stocks found")
            return []
        
        # Step 2: Enrich with additional data sources
        enriched_stocks = self._enrich_stocks(base_stocks, conditions)
        
        # Step 3: Filter by conditions
        filtered_stocks = self._apply_conditions(enriched_stocks, conditions)
        
        # Step 4: Sort and limit
        reverse = sort_order == "desc"
        try:
            sorted_stocks = sorted(
                filtered_stocks, 
                key=lambda x: x.get(sort_by, 0) or 0, 
                reverse=reverse
            )
        except Exception as e:
            logger.error(f"Sorting failed: {e}")
            sorted_stocks = filtered_stocks
        
        return sorted_stocks[:limit]
    
    def _get_base_universe(self) -> List[Dict[str, Any]]:
        """Get base stock universe from trust buy ratio data."""
        try:
            # Reuse existing trust buy ratio logic
            return self.stock_service.get_top_trust_buy_ratio(limit=500)
        except Exception as e:
            logger.error(f"Failed to get base universe: {e}")
            return []
    
    def _enrich_stocks(
        self, 
        stocks: List[Dict[str, Any]], 
        conditions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich stock data with additional factors based on conditions."""
        
        # Determine which data sources we need
        needed_sources = set()
        for cond in conditions:
            factor = cond.get("factor", "")
            if factor in RuleParser.SUPPORTED_FACTORS:
                needed_sources.add(RuleParser.SUPPORTED_FACTORS[factor]["source"])
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        enriched = []
        
        # Determine if we need to fetch external data
        needs_yfinance = "yfinance" in needed_sources
        needs_metabase = "metabase" in needed_sources
        
        # Function to process a single stock
        def process_stock(stock):
            stock_id = stock.get("stock_id", "")
            enriched_stock = stock.copy()
            
            # Add yfinance data if needed
            if needs_yfinance:
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(f"{stock_id}.TW")
                    hist = ticker.history(period="5d")
                    
                    if len(hist) >= 2:
                        # Price change percentage (5 days)
                        pct_change = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
                        enriched_stock["price_change_pct"] = round(pct_change, 2)
                        
                        # Volume ratio
                        avg_vol = hist['Volume'].mean()
                        last_vol = hist['Volume'].iloc[-1]
                        enriched_stock["volume_ratio"] = round(last_vol / avg_vol, 2) if avg_vol > 0 else 1
                        
                        # MA checks (simplified)
                        enriched_stock["above_ma20"] = True 
                        enriched_stock["above_ma60"] = True
                except Exception as e:
                    logger.debug(f"yfinance enrichment failed for {stock_id}: {e}")
            
            # Add metabase data if needed
            if needs_metabase:
                try:
                    # Get PE ratio from twstock collection
                    twstock_info = self.stock_service.twstock_col.find_one(
                        {"股票代號": stock_id},
                        {"本益比": 1, "殖利率": 1}
                    )
                    if twstock_info:
                        pe = twstock_info.get("本益比")
                        if pe and pe != "-":
                            try:
                                enriched_stock["pe_ratio"] = float(pe)
                            except (ValueError, TypeError):
                                pass
                        
                        div_yield = twstock_info.get("殖利率")
                        if div_yield and div_yield != "-":
                            try:
                                enriched_stock["dividend_yield"] = float(div_yield)
                            except (ValueError, TypeError):
                                pass
                except Exception as e:
                    logger.debug(f"Metabase enrichment failed for {stock_id}: {e}")
            
            return enriched_stock

        # Execute in parallel
        # Limit max_workers to avoid hitting rate limits or overwhelming system
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_stock = {executor.submit(process_stock, stock): stock for stock in stocks}
            
            for future in as_completed(future_to_stock):
                try:
                    result = future.result()
                    enriched.append(result)
                except Exception as e:
                    logger.error(f"Stock processing failed: {e}")
                    # Append original stock if processing fails
                    enriched.append(future_to_stock[future])
        
        return enriched
    
    def _apply_conditions(
        self, 
        stocks: List[Dict[str, Any]], 
        conditions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter stocks by all conditions (AND logic)."""
        
        def matches_condition(stock: Dict, cond: Dict) -> bool:
            factor = cond.get("factor", "")
            operator = cond.get("operator", ">=")
            value = cond.get("value", 0)
            
            stock_value = stock.get(factor)
            
            # Handle ratio field mapping
            if factor == "trust_buy_ratio" and stock_value is None:
                stock_value = stock.get("ratio")
            
            if stock_value is None:
                return False
            
            try:
                stock_value = float(stock_value)
                value = float(value)
                
                if operator == ">":
                    return stock_value > value
                elif operator == ">=":
                    return stock_value >= value
                elif operator == "<":
                    return stock_value < value
                elif operator == "<=":
                    return stock_value <= value
                elif operator == "==":
                    return stock_value == value
                elif operator == "!=":
                    return stock_value != value
                else:
                    return False
            except (ValueError, TypeError):
                return False
        
        filtered = []
        for stock in stocks:
            if all(matches_condition(stock, cond) for cond in conditions):
                filtered.append(stock)
        
        return filtered


class DynamicScreener:
    """Main interface for dynamic stock screening."""
    
    def __init__(self, stock_service: StockService = None):
        self.parser = RuleParser()
        self.executor = RuleExecutor(stock_service)
        logger.info("DynamicScreener initialized")
    
    def screen(self, query: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Screen stocks based on natural language query.
        
        Args:
            query: Natural language screening rule
            
        Returns:
            Tuple of (results list, parsed rules dict)
        """
        # Parse the query
        parsed = self.parser.parse(query)
        
        if "error" in parsed:
            return [], parsed
        
        # Execute the rules
        results = self.executor.execute(parsed)
        
        return results, parsed
    
    def format_results(
        self, 
        results: List[Dict[str, Any]], 
        parsed: Dict[str, Any],
        original_query: str
    ) -> str:
        """Format screening results as Markdown."""
        
        if "error" in parsed:
            return f"❌ 規則解析失敗：{parsed['error']}"
        
        if not results:
            return "🔍 找不到符合所有條件的股票。請嘗試放寬篩選條件。"
        
        # Build condition description
        conditions_desc = []
        for cond in parsed.get("conditions", []):
            factor = cond.get("factor", "")
            factor_info = RuleParser.SUPPORTED_FACTORS.get(factor, {})
            factor_name = factor_info.get("name", factor)
            unit = factor_info.get("unit", "")
            operator = cond.get("operator", "")
            value = cond.get("value", "")
            conditions_desc.append(f"{factor_name} {operator} {value}{unit}")
        
        conditions_text = " **且** ".join(conditions_desc)
        
        # Build report
        report = f"### 🎯 自訂選股結果\n\n"
        report += f"**篩選條件**：{conditions_text}\n\n"
        report += f"共找到 **{len(results)}** 檔符合條件的股票：\n\n"
        
        # Table header
        report += "| 排名 | 代碼 | 公司 | 投信買超(張) | 買超比重(%) |"
        
        # Add dynamic columns based on conditions
        has_pe = any(c.get("factor") == "pe_ratio" for c in parsed.get("conditions", []))
        has_pct = any(c.get("factor") == "price_change_pct" for c in parsed.get("conditions", []))
        
        if has_pe:
            report += " 本益比 |"
        if has_pct:
            report += " 漲跌幅 |"
        report += "\n"
        
        # Table separator
        report += "| :--- | :--- | :--- | :--- | :--- |"
        if has_pe:
            report += " :--- |"
        if has_pct:
            report += " :--- |"
        report += "\n"
        
        # Table rows
        for i, stock in enumerate(results, 1):
            rank_str = f"**{i}**" if i <= 3 else str(i)
            ratio = stock.get("ratio", stock.get("trust_buy_ratio", 0))
            
            row = f"| {rank_str} | {stock.get('stock_id', '')} | {stock.get('name', '')} | "
            row += f"{stock.get('trust_buy_lots', 0)} | {ratio}% |"
            
            if has_pe:
                pe = stock.get("pe_ratio", "-")
                row += f" {pe} |"
            if has_pct:
                pct = stock.get("price_change_pct", "-")
                row += f" {pct}% |"
            
            report += row + "\n"
        
        report += "\n> [!TIP]\n"
        report += "> 您可以輸入其他條件組合，例如：「投信買超 > 0.2% 且 本益比 < 15」\n"
        
        return report
