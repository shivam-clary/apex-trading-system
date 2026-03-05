"""
Commodities Agent — tracks crude oil, gold, silver, natural gas, copper, and agri.
Maps commodity moves to Indian sector impacts (OMCs, metals, infra, fertilizers).
"""
from __future__ import annotations
from typing import Any, Dict
from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class CommoditiesAgent(APEXBaseAgent):
    """
    Monitors global commodity prices and translates them into
    Indian equity market sector-level impacts.
    """

    AGENT_NAME = "CommoditiesAgent"
    AGENT_LAYER = 1
    SIGNAL_WEIGHT = 0.06

    CRUDE_BREAKEVENS = {"bullish": 70, "bearish": 90}
    GOLD_SAFE_HAVEN_THRESHOLD = 2.0

    async def analyze(self, market_data: Dict[str, Any]) -> AgentSignal:
        crude_score = self._score_crude(market_data)
        gold_score = self._score_gold(market_data)
        metals_score = self._score_base_metals(market_data)
        agri_score = self._score_agri(market_data)

        total = crude_score * 0.40 + gold_score * 0.25 + metals_score * 0.25 + agri_score * 0.10
        direction = (
            SignalDirection.BULLISH if total > 10
            else SignalDirection.BEARISH if total < -10
            else SignalDirection.NEUTRAL
        )

        sector_impacts = self._get_sector_impacts(market_data)

        return AgentSignal(
            agent_name=self.AGENT_NAME,
            direction=direction,
            confidence=min(abs(total) / 40, 1.0),
            timeframe=SignalTimeframe.SHORT_TERM,
            asset_class=AssetClass.COMMODITY,
            reasoning=(
                f"Crude: {crude_score:.1f} | Gold: {gold_score:.1f} | "
                f"Metals: {metals_score:.1f} | Agri: {agri_score:.1f}"
            ),
            metadata={
                "scores": {
                    "crude": crude_score, "gold": gold_score,
                    "metals": metals_score, "agri": agri_score, "total": total,
                },
                "sector_impacts": sector_impacts,
            },
        )

    def _score_crude(self, data: Dict) -> float:
        crude = data.get("crude_oil_wti", 75)
        crude_change_pct = data.get("crude_1d_change_pct", 0)
        score = 0.0
        if crude < self.CRUDE_BREAKEVENS["bullish"]:
            score += 20
        elif crude > self.CRUDE_BREAKEVENS["bearish"]:
            score -= 20
        if crude_change_pct > 3:
            score -= 15
        elif crude_change_pct < -3:
            score += 10
        return max(min(score, 30), -30)

    def _score_gold(self, data: Dict) -> float:
        gold_change_pct = data.get("gold_1d_change_pct", 0)
        if gold_change_pct > self.GOLD_SAFE_HAVEN_THRESHOLD:
            return -20
        elif gold_change_pct < -self.GOLD_SAFE_HAVEN_THRESHOLD:
            return 10
        return 0

    def _score_base_metals(self, data: Dict) -> float:
        copper_change = data.get("copper_1d_change_pct", 0)
        aluminium_change = data.get("aluminium_1d_change_pct", 0)
        score = copper_change * 3 + aluminium_change * 2
        return max(min(score, 20), -20)

    def _score_agri(self, data: Dict) -> float:
        food_inflation = data.get("india_food_inflation", 5.0)
        if food_inflation > 8:
            return -15
        elif food_inflation > 6:
            return -5
        return 5

    def _get_sector_impacts(self, data: Dict) -> Dict[str, str]:
        crude = data.get("crude_oil_wti", 75)
        impacts = {}
        if crude > 90:
            impacts["OMCs"] = "NEGATIVE — margin squeeze"
            impacts["Airlines"] = "NEGATIVE — fuel cost surge"
            impacts["Paints"] = "NEGATIVE — raw material inflation"
        elif crude < 70:
            impacts["OMCs"] = "POSITIVE — inventory gains"
            impacts["Airlines"] = "POSITIVE — lower fuel costs"
        copper_change = data.get("copper_1d_change_pct", 0)
        if copper_change > 2:
            impacts["Metals"] = "POSITIVE — copper rally"
            impacts["Infra"] = "POSITIVE — economic growth signal"
        return impacts
