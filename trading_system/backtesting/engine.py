"""
BacktestEngine — event-driven backtester for Indian equity F&O strategies.
Applies realistic slippage, brokerage, and NSE trading rules.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd


@dataclass
class BacktestConfig:
    initial_capital: float = 1_000_000.0
    commission_per_trade: float = 20.0       # Zerodha flat Rs 20
    stt_pct: float = 0.0001
    slippage_bps: float = 2.0
    lot_size: int = 50
    max_positions: int = 3
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class BacktestResult:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    total_costs: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    trade_log: List[Dict] = field(default_factory=list)


class BacktestEngine:
    """
    Vectorised + event-driven hybrid backtester.
    Accepts a strategy function that takes a bar and returns BUY/SELL/HOLD.
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

    def run(
        self,
        data: pd.DataFrame,
        strategy_fn: Callable[[pd.Series, Dict], str],
        strategy_params: Optional[Dict] = None,
    ) -> BacktestResult:
        """
        Run backtest over OHLCV data.
        strategy_fn(bar, state) -> 'BUY' | 'SELL' | 'HOLD'
        """
        params = strategy_params or {}
        capital = self.config.initial_capital
        peak = capital
        positions: List[Dict] = []
        result = BacktestResult()
        result.equity_curve.append(capital)
        state: Dict[str, Any] = {"positions": positions, "params": params}

        for idx, bar in data.iterrows():
            signal = strategy_fn(bar, state)
            cost = 0.0

            if signal == "BUY" and len(positions) < self.config.max_positions:
                entry = bar["close"] * (1 + self.config.slippage_bps / 10000)
                qty = self.config.lot_size
                cost = self._calc_cost(entry, qty)
                positions.append({
                    "entry": entry, "qty": qty,
                    "entry_time": idx, "cost": cost,
                })
                capital -= cost

            elif signal == "SELL" and positions:
                pos = positions.pop(0)
                exit_price = bar["close"] * (1 - self.config.slippage_bps / 10000)
                gross = (exit_price - pos["entry"]) * pos["qty"]
                exit_cost = self._calc_cost(exit_price, pos["qty"])
                net = gross - pos["cost"] - exit_cost
                capital += gross - exit_cost
                result.total_trades += 1
                result.gross_pnl += gross
                result.total_costs += pos["cost"] + exit_cost
                if net > 0:
                    result.winning_trades += 1
                    result.avg_win = (result.avg_win * (result.winning_trades - 1) + net) / result.winning_trades
                else:
                    result.losing_trades += 1
                    result.avg_loss = (result.avg_loss * (result.losing_trades - 1) + abs(net)) / result.losing_trades
                result.trade_log.append({
                    "entry_time": str(pos["entry_time"]), "exit_time": str(idx),
                    "entry": pos["entry"], "exit": exit_price,
                    "qty": pos["qty"], "pnl": net,
                })

            result.equity_curve.append(capital)
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak * 100
            if dd > result.max_drawdown_pct:
                result.max_drawdown_pct = dd

        result.net_pnl = capital - self.config.initial_capital
        result.win_rate_pct = (
            result.winning_trades / result.total_trades * 100
            if result.total_trades else 0
        )
        result.profit_factor = (
            (result.avg_win * result.winning_trades) /
            (result.avg_loss * result.losing_trades)
            if result.losing_trades and result.avg_loss else 0
        )
        return result

    def _calc_cost(self, price: float, qty: int) -> float:
        notional = price * qty
        return (
            self.config.commission_per_trade +
            notional * self.config.stt_pct +
            notional * (self.config.slippage_bps / 10000)
        )
