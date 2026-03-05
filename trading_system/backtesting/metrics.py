"""
PerformanceMetrics — computes all standard quant performance metrics
from an equity curve and trade log.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional


class PerformanceMetrics:
    """Stateless metrics calculator. Pass equity curve and trade list."""

    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.065   # 6.5% India 10Y Gsec

    @classmethod
    def compute_all(
        cls,
        equity_curve: List[float],
        trade_log: List[Dict],
        initial_capital: float,
    ) -> Dict:
        returns = cls._daily_returns(equity_curve)
        return {
            "sharpe_ratio": cls.sharpe(returns),
            "sortino_ratio": cls.sortino(returns),
            "calmar_ratio": cls.calmar(equity_curve, returns),
            "max_drawdown_pct": cls.max_drawdown(equity_curve),
            "cagr_pct": cls.cagr(equity_curve, initial_capital),
            "win_rate_pct": cls.win_rate(trade_log),
            "profit_factor": cls.profit_factor(trade_log),
            "avg_win": cls.avg_win(trade_log),
            "avg_loss": cls.avg_loss(trade_log),
            "expectancy": cls.expectancy(trade_log),
            "total_trades": len(trade_log),
            "net_pnl": equity_curve[-1] - initial_capital if equity_curve else 0,
            "return_pct": (equity_curve[-1] - initial_capital) / initial_capital * 100 if equity_curve else 0,
        }

    @classmethod
    def sharpe(cls, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0
        if std == 0:
            return 0.0
        daily_rfr = cls.RISK_FREE_RATE / cls.TRADING_DAYS_PER_YEAR
        return (mean_r - daily_rfr) / std * math.sqrt(cls.TRADING_DAYS_PER_YEAR)

    @classmethod
    def sortino(cls, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        daily_rfr = cls.RISK_FREE_RATE / cls.TRADING_DAYS_PER_YEAR
        downside = [r for r in returns if r < daily_rfr]
        if not downside:
            return float('inf')
        downside_var = sum((r - daily_rfr) ** 2 for r in downside) / len(downside)
        downside_std = math.sqrt(downside_var)
        if downside_std == 0:
            return 0.0
        return (mean_r - daily_rfr) / downside_std * math.sqrt(cls.TRADING_DAYS_PER_YEAR)

    @classmethod
    def max_drawdown(cls, equity_curve: List[float]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]
        max_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @classmethod
    def calmar(cls, equity_curve: List[float], returns: List[float]) -> float:
        cagr = cls.cagr(equity_curve, equity_curve[0] if equity_curve else 1)
        mdd = cls.max_drawdown(equity_curve)
        return cagr / mdd if mdd > 0 else 0.0

    @classmethod
    def cagr(cls, equity_curve: List[float], initial: float) -> float:
        if not equity_curve or initial == 0:
            return 0.0
        n_years = len(equity_curve) / cls.TRADING_DAYS_PER_YEAR
        if n_years == 0:
            return 0.0
        return ((equity_curve[-1] / initial) ** (1 / n_years) - 1) * 100

    @classmethod
    def win_rate(cls, trades: List[Dict]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
        return wins / len(trades) * 100

    @classmethod
    def profit_factor(cls, trades: List[Dict]) -> float:
        gross_win = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
        return gross_win / gross_loss if gross_loss > 0 else 0.0

    @classmethod
    def avg_win(cls, trades: List[Dict]) -> float:
        wins = [t["pnl"] for t in trades if t.get("pnl", 0) > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @classmethod
    def avg_loss(cls, trades: List[Dict]) -> float:
        losses = [abs(t["pnl"]) for t in trades if t.get("pnl", 0) < 0]
        return sum(losses) / len(losses) if losses else 0.0

    @classmethod
    def expectancy(cls, trades: List[Dict]) -> float:
        if not trades:
            return 0.0
        wr = cls.win_rate(trades) / 100
        aw = cls.avg_win(trades)
        al = cls.avg_loss(trades)
        return wr * aw - (1 - wr) * al

    @classmethod
    def _daily_returns(cls, equity_curve: List[float]) -> List[float]:
        if len(equity_curve) < 2:
            return []
        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]
            if prev != 0:
                returns.append((equity_curve[i] - prev) / prev)
        return returns
