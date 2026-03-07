"""
APEX Agent 10: FIIDIIFlowAgent
Tracks FII/DII buying/selling in cash and F&O markets.
FII flows are the single biggest driver of Indian market direction.
"""
from __future__ import annotations
from typing import Dict, Any
import pandas as pd

from ..core.base_agent import APEXBaseAgent
from ..core.signal_schema import AgentSignal, SignalDirection, SignalTimeframe, AssetClass


class FIIDIIFlowAgent(APEXBaseAgent):
    """
    Data sources:
    - NSE FII/DII provisional data (daily after 6 PM)
    - NSE India API for equity + derivative flows
    """

    def __init__(self, config=None):
        super().__init__("FIIDIIFlowAgent", "1.0.0", config)

    async def _fetch_data(self) -> Dict[str, Any]:
        import httpx
        data = {}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"}
        async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
            try:
                await client.get("https://www.nseindia.com", timeout=10)
                resp = await client.get(
                    "https://www.nseindia.com/api/fiidiiTradeReact",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data["fii_dii"] = resp.json()
            except Exception as e:
                self.logger.warning(f"NSE FII/DII fetch failed: {e}")
        return data

    def _analyze_flows(self, flow_data) -> Dict[str, Any]:
        if not flow_data:
            return {}
        rows = flow_data if isinstance(
            flow_data, list) else flow_data.get(
            "data", [])
        if not rows:
            return {}
        df = pd.DataFrame(rows)
        latest = df.iloc[0] if not df.empty else {}
        fii_net = float(str(latest.get("FII_NET", "0")).replace(
            ",", "")) if latest.get("FII_NET") else 0.0
        dii_net = float(str(latest.get("DII_NET", "0")).replace(
            ",", "")) if latest.get("DII_NET") else 0.0
        # 5-day rolling
        fii_5d = 0.0
        dii_5d = 0.0
        try:
            fii_col = [float(str(r.get("FII_NET", "0")).replace(",", ""))
                       for r in rows[:5]]
            dii_col = [float(str(r.get("DII_NET", "0")).replace(",", ""))
                       for r in rows[:5]]
            fii_5d = sum(fii_col)
            dii_5d = sum(dii_col)
        except Exception:
            pass
        return {"fii_net_today": fii_net, "dii_net_today": dii_net,
                "fii_5d": fii_5d, "dii_5d": dii_5d}

    async def analyze(self) -> AgentSignal:
        data = await self._fetch_data()
        flows = self._analyze_flows(data.get("fii_dii"))
        if not flows:
            return self._no_signal("FII/DII data unavailable")

        fii_net = flows.get("fii_net_today", 0)
        dii_net = flows.get("dii_net_today", 0)
        fii_5d = flows.get("fii_5d", 0)
        combined_net = fii_net * 1.5 + dii_net  # FII weighted more

        key_factors = [
            f"FII today: {'+' if fii_net > 0 else ''}{fii_net:.0f} Cr",
            f"DII today: {'+' if dii_net > 0 else ''}{dii_net:.0f} Cr",
            f"FII 5-day: {'+' if fii_5d > 0 else ''}{fii_5d:.0f} Cr",
        ]

        if combined_net > 2000:
            direction, confidence = SignalDirection.STRONG_BUY, 0.80
        elif combined_net > 500:
            direction, confidence = SignalDirection.BUY, 0.65
        elif combined_net < -2000:
            direction, confidence = SignalDirection.STRONG_SELL, 0.80
        elif combined_net < -500:
            direction, confidence = SignalDirection.SELL, 0.65
        else:
            direction, confidence = SignalDirection.NEUTRAL, 0.35

        return self._make_signal(
            direction=direction,
            confidence=confidence,
            symbol="NIFTY 50",
            reasoning=f"FII net={fii_net:.0f}Cr, DII net={dii_net:.0f}Cr, Combined={combined_net:.0f}Cr",
            key_factors=key_factors,
            timeframe=SignalTimeframe.SWING,
            asset_class=AssetClass.INDEX,
            supporting_data=flows,
        )
