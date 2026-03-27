"""
Application constants.
Centralized location for all magic numbers and strings.
"""

# Database Names
DB_SINOPAC_NEWS = 'sinopac_News'
DB_SINOPAC_HOTWORDS = 'sinopac_hotwords'
DB_TWSTOCK = 'twstock'

# Collection Names
COLL_NEWS_SENTIMENT = 'sinopac_News_Sentiment'
COLL_HOTWORDS_LEARNINGPOST = 'sinopac_hotwords_v2'
COLL_TWSTOCK = 'twstock'

# Field Names
FIELD_STOCK_ID = '股票代號'
FIELD_STOCK_CODE = '股票代碼'
FIELD_STOCK_NAME = '股票名稱'
FIELD_TWSTOCK_NAME = '公司'
FIELD_DATA_DATE = '資料日期'
FIELD_PUBLISH_DATE = '發布日期時間'
FIELD_NEWS_TITLE = '新聞標題'
FIELD_NEWS_CONTENT = '新聞內容'
FIELD_NEWS_SENTIMENT = '新聞情緒'
FIELD_RISING_REASON = '股價上漲原因(熱度起始日)'
FIELD_MARKET_NEWS = '市場傳出消息(熱度起始日)'
FIELD_CONCEPTS = '豐搜新聞概念股'
FIELD_LATEST_NEWS = '最新新聞'
FIELD_HEAT = '豐搜熱度'
FIELD_KEYWORDS = '關鍵字和專有名稱(熱度起始日)'
FIELD_PE_RATIO = '本益比'
FIELD_DIVIDEND_YIELD = '殖利率'
FIELD_BUY_SELL = '買賣超'
FIELD_FOREIGN_BUY_SELL = '外資買賣超'
FIELD_TRUST_BUY_SELL = '投信買賣超'

# Sentiment Indicators
SENTIMENT_POSITIVE = '🟢 (看多)'
SENTIMENT_NEGATIVE = '🔴 (看空)'
SENTIMENT_NEUTRAL = '🟡 (中立)'
SENTIMENT_UNKNOWN = '⚪'

# Analysis Limits
LIMIT_NEWS_FOR_ANALYSIS = 5
LIMIT_NEWS_TITLE_SEARCH = 50
LIMIT_CONCEPT_SEARCH_RESULTS = 10
LIMIT_RECOMMENDATIONS = 3

# Freshness Thresholds (in days)
FRESHNESS_ALERT_DAYS = 30
FRESHNESS_WARNING_DAYS = 7

# Text Limits
MAX_SUMMARY_LENGTH = 30
MAX_NEWS_CONTENT_LENGTH = 200

# Regex Patterns
PATTERN_STOCK_NAME = r"([\u4e00-\u9fa5]+)\s*[\(\uff08]{stock_id}[\)\uff09]"

# Stock Name Cleanup Prefixes
STOCK_NAME_PREFIXES = [
    '權值[王股哥]', '權王', '[一二三]哥', '龍頭', '雙虎', '三雄', '神山',
    '代工', 'IC設計', '類股', '總成交值在', '概念股', '族群', '大廠', '集團',
    '營建', '傳產', '金融', '電子', '航運', '生技'
]

# Stock Name Length Constraints
MIN_STOCK_NAME_LENGTH = 2
MAX_STOCK_NAME_LENGTH = 4
FALLBACK_STOCK_NAME = "個股"

# Score Calculation
BASE_SCORE = 5.0
MAX_HEAT_SCORE = 3.0
MAX_SENTIMENT_SCORE = 2.0
MAX_FRESHNESS_PENALTY = 3.0

HEAT_THRESHOLD_HIGH = 8.0
HEAT_THRESHOLD_MEDIUM = 5.0
HEAT_THRESHOLD_LOW = 2.0

# Star Ratings
STARS_PER_POINT = 2  # 2 points = 1 star
HALF_STAR = "✨"
FULL_STAR = "⭐"

# Yahoo Finance
YFINANCE_EXCHANGE_TSE = ".TW"
YFINANCE_EXCHANGE_OTC = ".TWO"
YFINANCE_YIELD_THRESHOLD = 0.5  # Values below this are treated as decimals (0.03 = 3%)

# Error Messages
ERROR_NO_DATA = "暫無摘要"
ERROR_NO_RECENT_NEWS = "近期無相關新聞"
ERROR_NO_HISTORICAL = "目前無歷史熱點記錄"
ERROR_AI_BUSY = "AI 分析暫時忙線或額度已滿"
ERROR_SYSTEM = "系統發生錯誤"

# UI Messages
MSG_BATCH_QUERY_HINT = "💡 輸入單一代號可查看完整分析"
MSG_CONCEPT_SEARCH_HINT = "(輸入代號查看詳細分析)"
MSG_CONCEPT_SEARCH_FAIL = "找不到與「{keyword}」相關的熱門概念股，請嘗試其他關鍵字（如：AI、銅箔、5G）。"
