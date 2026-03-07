"""
GlobalNews Agent — monitors US Fed minutes, ECB policy, geopolitical events,
and global macro news headlines for overnight risk-on/risk-off bias.
"""
from __future__ import annotations
from typing import Any, Dict, List
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class GlobalNewsAgent(APEXBaseAgent):
    """
    Layer 4 Sentiment Agent: geopolitical risk scoring, Fed/ECB rhetoric parsing,
    war/conflict escalation detection, and global trade flow monitoring.
    """

    AGENT_NAME = "GlobalNewsAgent"
    AGENT_LAYER = 4
    SIGNAL_WEIGHT = 0.06

    RISK_OFF_KEYWORDS = [
        "war escalation", "nuclear", "sanctions", "trade war", "tariff",
        "bank failure", "credit crisis", "recession", "default sovereign",
        "fed hike surprise", "inflation surge", "stagflation",
        "pandemic", "lockdown", "supply shock",
    ]

    RISK_ON_KEYWORDS = [
        "ceasefire", "peace deal", "fed pause", "rate cut", "stimulus",
        "trade deal", "china reopening", "soft landing", "strong jobs",
        "earnings beat", "gdp beat", "manufacturing expansion",
    ]

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        global_headlines = market_data.get("global_headlines", [])
        geopolitical_risk = market_data.get("geopolitical_risk_index", 50)
        vix_level = market_data.get("vix_us", 20)

        headline_score = self._score_headlines(global_headlines)
        geo_score = self._score_geopolitical_risk(geopolitical_risk)
        vix_score = self._score_vix(vix_level)

        total = headline_score * 0.50 + geo_score * 0.30 + vix_score * 0.20
        direction = (
            SignalDirection.BULLISH if total > 10
            else SignalDirection.BEARISH if total < -10
            else SignalDirection.NEUTRAL
        )

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total) / 40, 1.0),
            timeframe=SignalTimeframe.SHORT_TERM,
            asset_class=AssetClass.INDEX,
            reasoning=(
                f"Headlines: {headline_score:.1f} | Geo-risk: {geo_score:.1f} | VIX: {vix_score:.1f}"
            ),
            metadata={
                "headline_score": headline_score,
                "geo_score": geo_score,
                "vix_score": vix_score,
                "vix_level": vix_level,
                "geopolitical_risk": geopolitical_risk,
            },
        )

    def _score_headlines(self, headlines: List[Dict]) -> float:
        score = 0.0
        for item in headlines:
            text = (
                item.get(
                    "title",
                    "") +
                " " +
                item.get(
                    "summary",
                    "")).lower()
            for kw in self.RISK_OFF_KEYWORDS:
                if kw in text:
                    score -= 12
                    break
            for kw in self.RISK_ON_KEYWORDS:
                if kw in text:
                    score += 10
                    break
        return max(min(score, 40), -40)

    def _score_geopolitical_risk(self, risk_index: float) -> float:
        if risk_index > 200:
            return -30
        elif risk_index > 150:
            return -20
        elif risk_index > 100:
            return -10
        elif risk_index < 50:
            return 15
        return 0

    def _score_vix(self, vix: float) -> float:
        if vix > 35:
            return -30
        elif vix > 25:
            return -15
        elif vix > 20:
            return -5
        elif vix < 15:
            return 20
        elif vix < 18:
            return 10
        return 0
