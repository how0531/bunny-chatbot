"""
BunnyGood Scoring Engine - Comprehensive stock evaluation model.
Extracted from stock_service.py for modularity.
"""
from typing import Dict, Any, Optional
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


class BunnyGoodScorer:
    """
    Arthur's BunnyGood Comprehensive Scoring Model (0-10).
    Combines: Technical(20%) + Chips(30%) + Fundamentals(40%) + Sentiment(10%)
    """

    # Factor weights
    WEIGHTS = {
        'technical': 0.20,
        'chips': 0.30,
        'fundamentals': 0.40,
        'sentiment': 0.10,
    }

    def calculate_score(
        self,
        hotword_doc: Optional[Dict] = None,
        sentiment_score: float = 0,
        days_diff: int = 0,
        yf_data: Optional[Dict] = None,
        tech_data: Optional[Dict] = None,
        chips_data: Optional[Dict] = None,
        target_price: Optional[float] = None,
    ) -> float:
        """
        Calculate comprehensive BunnyGood score (0-10).
        """
        score = 5.0  # Neutral base

        # ── 1. Sentiment & Heat (Max ±2.5 pts) ──
        score += self._score_sentiment(hotword_doc, sentiment_score)

        # ── 2. Chips / Institutional Flow (Max ±3 pts) ──
        score += self._score_chips(chips_data)

        # ── 3. Fundamentals / Valuation (Max ±3 pts) ──
        score += self._score_fundamentals(yf_data, target_price)

        # ── 4. Technical (Max ±2 pts) ──
        score += self._score_technical(tech_data)

        # ── 5. Freshness Penalty (Max -3 pts) ──
        score += self._penalty_freshness(days_diff)

        final = max(0.0, min(10.0, score))
        logger.debug(f"BunnyGood Score: {final:.2f} (raw: {score:.2f})")
        return final

    # ─────────── Sub-scorers ───────────

    @staticmethod
    def _score_sentiment(hotword_doc: Optional[Dict], sentiment_score: float) -> float:
        pts = 0.0
        if hotword_doc:
            try:
                h_val = float(hotword_doc.get('豐搜熱度', 0))
                if h_val > 8: pts += 1.5
                elif h_val > 5: pts += 1.0
                elif h_val > 2: pts += 0.5
            except (ValueError, TypeError):
                pass

        if sentiment_score > 0:
            pts += min(sentiment_score * 0.5, 2.5)
        elif sentiment_score < 0:
            pts -= min(abs(sentiment_score) * 0.5, 2.5)
        return pts

    @staticmethod
    def _score_chips(chips_data: Optional[Dict]) -> float:
        if not chips_data:
            return 0.0
        pts = 0.0
        foreign = chips_data.get('foreign_net', 0)
        trust = chips_data.get('trust_net', 0)
        foreign_days = chips_data.get('foreign_consecutive_days', 0)
        trust_days = chips_data.get('trust_consecutive_days', 0)

        # Raw flow direction
        if foreign > 0 and trust > 0: pts += 1.5
        elif foreign > 0 or trust > 0: pts += 0.8
        if foreign < 0 and trust < 0: pts -= 1.5
        elif foreign < 0 or trust < 0: pts -= 0.5

        # Consecutive days bonus
        if foreign_days >= 5: pts += 0.8
        elif foreign_days >= 3: pts += 0.5
        if trust_days >= 5: pts += 0.8
        elif trust_days >= 3: pts += 0.5

        return pts

    @staticmethod
    def _score_fundamentals(yf_data: Optional[Dict], target_price: Optional[float]) -> float:
        if not yf_data:
            return 0.0
        pts = 0.0
        current_price = yf_data.get('price')

        # Target Price Upside
        if target_price and current_price:
            upside = (target_price - current_price) / current_price
            if upside > 0.3: pts += 1.5
            elif upside > 0.15: pts += 1.0
            elif upside > 0.05: pts += 0.5

        # ROE Quality
        roe_str = yf_data.get('roe', '')
        if roe_str:
            try:
                roe_val = float(str(roe_str).replace('%', ''))
                if roe_val > 20: pts += 1.0
                elif roe_val > 10: pts += 0.5
                elif roe_val < 0: pts -= 1.0
            except (ValueError, TypeError):
                pass

        # PB Overvaluation
        pb_str = yf_data.get('pb', '')
        if pb_str:
            try:
                if float(pb_str) > 5.0: pts -= 0.5
            except (ValueError, TypeError):
                pass

        return pts

    @staticmethod
    def _score_technical(tech_data: Optional[Dict]) -> float:
        if not tech_data:
            return 0.0
        pts = 0.0

        # MA Arrangement
        if tech_data.get('ma_bullish'): pts += 1.0
        elif tech_data.get('ma_bearish'): pts -= 1.0

        # RSI
        rsi = tech_data.get('rsi')
        if rsi:
            if rsi > 70: pts -= 0.5  # Overbought
            elif rsi < 30: pts += 0.5  # Oversold (potential reversal)

        # KD Golden Cross
        if tech_data.get('kd_golden_cross'): pts += 0.5

        # Volume surge
        vol_ratio = tech_data.get('volume_ratio', 1.0)
        if vol_ratio > 2.0: pts += 0.5

        return pts

    @staticmethod
    def _penalty_freshness(days_diff: int) -> float:
        if days_diff > 30: return -3.0
        elif days_diff > 14: return -1.5
        elif days_diff > 7: return -0.5
        return 0.0

    # ─────────── Display Helpers ───────────

    @staticmethod
    def score_to_stars(score: float) -> str:
        stars = "⭐" * int(score / 2)
        if score % 2 >= 1:
            stars += "✨"
        return stars

    @staticmethod
    def score_to_emoji(score: float) -> str:
        if score >= 8: return "🔥"
        elif score >= 6: return "🟢"
        elif score >= 4: return "🟡"
        else: return "🔴"
