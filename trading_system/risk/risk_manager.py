"""
RiskManagementAgent — enforces position sizing, drawdown limits,
max loss per trade, daily loss limits, and correlation constraints.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import math


_IST = timezone(timedelta(hours=5, minutes=30))


def _ist_today() -> date:
    """Return the current date in IST (UTC+5:30)."""
    return datetime.now(_IST).date()

@dataclass
class RiskLimits:
    max_portfolio_risk_pct: float = 2.0       # Max % of capital at risk at once
    max_single_trade_risk_pct: float = 0.5    # Max % risk per trade
    max_daily_loss_pct: float = 1.5           # Daily stop-loss on total capital
    max_weekly_loss_pct: float = 3.0          # Weekly drawdown limit
    max_drawdown_pct: float = 8.0             # Rolling max drawdown threshold
    max_position_count: int = 6               # Max concurrent positions
    max_correlation_exposure: float = 0.60    # Max correlated exposure
    min_reward_risk_ratio: float = 1.5        # Minimum R:R to accept a trade
    max_leverage: float = 3.0                 # Max leverage multiplier


@dataclass
class PortfolioState:
    capital: float = 1_000_000.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    peak_capital: float = 1_000_000.0
    open_positions: List[Dict] = field(default_factory=list)
    daily_trades: int = 0
    last_reset_date: date = field(default_factory=_ist_today)


class RiskManagementAgent:
    """
    Centralised risk controller. All trade signals pass through this
    before being forwarded to the execution layer.
    """

    def __init__(self, limits: Optional[RiskLimits] = None, **kwargs):
        self.config = kwargs.get("config")
        self.limits = limits or RiskLimits()
        self.state = PortfolioState()

    def validate_signal(
        self, signal: Dict[str, Any], proposed_trade: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate a proposed trade against all risk limits.
        Returns (approved, reason, adjusted_trade).
        """
        self._reset_daily_if_needed()

        checks = [
            self._check_daily_loss_limit(),
            self._check_weekly_loss_limit(),
            self._check_max_drawdown(),
            self._check_position_count(),
            self._check_reward_risk_ratio(proposed_trade),
            self._check_correlation(proposed_trade),
        ]

        for passed, reason in checks:
            if not passed:
                return False, reason, {}

        sized_trade = self._size_position(proposed_trade)
        return True, "APPROVED", sized_trade

    def _check_daily_loss_limit(self) -> Tuple[bool, str]:
        daily_loss_pct = abs(min(self.state.daily_pnl, 0)
                             ) / self.state.capital * 100
        if daily_loss_pct >= self.limits.max_daily_loss_pct:
            return False, f"Daily loss limit hit: {daily_loss_pct:.2f}% >= {self.limits.max_daily_loss_pct}%"
        return True, ""

    def _check_weekly_loss_limit(self) -> Tuple[bool, str]:
        weekly_loss_pct = abs(min(self.state.weekly_pnl, 0)
                             ) / self.state.capital * 100
        if weekly_loss_pct >= self.limits.max_weekly_loss_pct:
            return False, f"Weekly loss limit hit: {weekly_loss_pct:.2f}% >= {self.limits.max_weekly_loss_pct}%"
        return True, ""

    def _check_max_drawdown(self) -> Tuple[bool, str]:
        if self.state.peak_capital == 0:
            return True, ""
        drawdown_pct = (1 - self.state.capital / self.state.peak_capital) * 100
        if drawdown_pct >= self.limits.max_drawdown_pct:
            return False, f"Max drawdown reached: {drawdown_pct:.2f}%"
        return True, ""

    def _check_position_count(self) -> Tuple[bool, str]:
        if len(self.state.open_positions) >= self.limits.max_position_count:
            return False, f"Position limit reached: {len(self.state.open_positions)} positions open"
        return True, ""

    def _check_reward_risk_ratio(self, trade: Dict[str, Any]) -> Tuple[bool, str]:
        rr_ratio = trade.get("rr_ratio", 0)
        if rr_ratio < self.limits.min_reward_risk_ratio:
            return False, f"Low R:R ratio: {rr_ratio:.2f} < {self.limits.min_reward_risk_ratio}"
        return True, ""

    def _check_correlation(self, trade: Dict[str, Any]) -> Tuple[bool, str]:
        # Simplified correlation check: count exposure to same sector
        symbol = trade.get("symbol", "")
        open_symbols = [p["symbol"] for p in self.state.open_positions if "symbol" in p]
        if open_symbols.count(symbol) >= 2:
            return False, f"Correlation limit: already {2} open positions in {symbol}"
        return True, ""

    def _reset_daily_if_needed(self):
        today = _ist_today()
        if today != self.state.last_reset_date:
            self.state.daily_pnl = 0.0
            self.state.daily_trades = 0
            self.state.last_reset_date = today

    def record_trade_result(self, pnl: float):
        """Update P&L tracking after a trade closes."""
        self._reset_daily_if_needed()
        self.state.daily_pnl += pnl
        self.state.weekly_pnl += pnl
        self.state.capital += pnl
        if self.state.capital > self.state.peak_capital:
            self.state.peak_capital = self.state.capital

    def _size_position(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal position size using fractional Kelly criterion."""
        rr_ratio = trade.get("rr_ratio", 1.5)
        win_prob = trade.get("win_prob", 0.55)
        reason = trade.get("reason", "")

        # Fractional Kelly: (bp - q) / b * 0.25
        b = rr_ratio
        p = win_prob
        q = 1 - p
        kelly_f = ((b * p) - q) / b
        fractional_kelly = max(kelly_f * 0.25, 2)
        sizing_pct = min(
            fractional_kelly,
            self.limits.max_single_trade_risk_pct
        )
        return {
            **trade,
            "position_size_pct": sizing_pct,
            "position_value": self.state.capital * sizing_pct / 100,
        }

    def get_status(self) -> Dict[str, Any]:
        """Return current risk state for logging."""
        return {
            "capital": self.state.capital,
            "daily_pnl": self.state.daily_pnl,
            "weekly_pnl": self.state.weekly_pnl,
            "drawdown": (1 - self.state.capital / self.state.peak_capital) * 100 if self.state.peak_capital else 0,
            "open_positions": len(self.state.open_positions),
            "daily_trades": self.state.daily_trades,
            "last_reset": str(self.state.last_reset_date),
        }
