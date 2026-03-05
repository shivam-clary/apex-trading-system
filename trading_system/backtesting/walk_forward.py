"""
WalkForwardOptimizer — rolling in-sample / out-of-sample backtest
to detect overfitting and validate strategy robustness.
"""
from __future__ import annotations
import pandas as pd
from typing import Any, Callable, Dict, List, Optional, Tuple
from .engine import BacktestEngine, BacktestConfig, BacktestResult


class WalkForwardOptimizer:
    """
    Walk-forward analysis:
    1. Split data into N folds
    2. For each fold: train on in-sample, validate on out-of-sample
    3. Aggregate OOS results to measure real-world performance decay
    """

    def __init__(
        self,
        n_folds: int = 5,
        train_ratio: float = 0.70,
        config: Optional[BacktestConfig] = None,
    ):
        self.n_folds = n_folds
        self.train_ratio = train_ratio
        self.config = config or BacktestConfig()

    def run(
        self,
        ohlcv: pd.DataFrame,
        signal_fn_factory: Callable[[pd.DataFrame], Callable],
    ) -> Dict[str, Any]:
        """
        signal_fn_factory(train_df) -> signal_fn(df, idx)
        Allows parameter optimisation on train data before OOS test.
        """
        folds = self._create_folds(ohlcv)
        oos_results: List[BacktestResult] = []
        fold_summaries = []

        for i, (train_df, oos_df) in enumerate(folds):
            signal_fn = signal_fn_factory(train_df)
            engine = BacktestEngine(self.config)
            oos_result = engine.run(oos_df, signal_fn)
            oos_results.append(oos_result)
            fold_summaries.append({
                "fold": i + 1,
                "train_bars": len(train_df),
                "oos_bars": len(oos_df),
                "oos_return_pct": oos_result.total_return_pct,
                "oos_sharpe": oos_result.sharpe_ratio,
                "oos_max_dd_pct": oos_result.max_drawdown_pct,
                "oos_win_rate_pct": oos_result.win_rate_pct,
                "oos_trades": oos_result.total_trades,
            })

        combined_return = sum(r.total_return_pct for r in oos_results)
        avg_sharpe = sum(r.sharpe_ratio for r in oos_results) / len(oos_results)
        avg_max_dd = sum(r.max_drawdown_pct for r in oos_results) / len(oos_results)
        positive_folds = sum(1 for r in oos_results if r.total_return_pct > 0)

        return {
            "n_folds": self.n_folds,
            "combined_oos_return_pct": combined_return,
            "avg_sharpe": avg_sharpe,
            "avg_max_drawdown_pct": avg_max_dd,
            "positive_folds": positive_folds,
            "fold_consistency_pct": positive_folds / self.n_folds * 100,
            "fold_summaries": fold_summaries,
            "is_robust": positive_folds >= self.n_folds * 0.6 and avg_sharpe > 0.5,
        }

    def _create_folds(
        self, df: pd.DataFrame
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        total = len(df)
        fold_size = total // self.n_folds
        folds = []
        for i in range(self.n_folds):
            start = i * fold_size
            end = start + fold_size if i < self.n_folds - 1 else total
            window = df.iloc[start:end].reset_index(drop=True)
            train_end = int(len(window) * self.train_ratio)
            train = window.iloc[:train_end]
            oos = window.iloc[train_end:]
            if len(train) > 10 and len(oos) > 5:
                folds.append((train, oos))
        return folds
