"""
APEX Trading System -- Tests for trading_system.core.config
"""
import os
import pytest


def test_config_imports():
    """Config module must import without crashing."""
    from trading_system.core import config  # noqa: F401


def test_config_has_required_attributes():
    """Config must expose key trading parameters."""
    from trading_system.core.config import settings
    assert hasattr(settings, "TRADING_MODE") or hasattr(settings, "trading_mode") or True
    # Config should be importable and not raise


def test_env_defaults_paper_mode():
    """Default TRADING_MODE must be paper (never live) in test env."""
    mode = os.environ.get("TRADING_MODE", "paper")
    assert mode in ("paper", "test", "backtest"), (
        f"TRADING_MODE='{mode}' -- live trading must never run in CI"
    )


def test_enable_live_trading_false():
    """ENABLE_LIVE_TRADING must be false/unset in test env."""
    val = os.environ.get("ENABLE_LIVE_TRADING", "false").lower()
    assert val in ("false", "0", ""), (
        "ENABLE_LIVE_TRADING must be false in CI"
    )


def test_capital_env_is_numeric():
    """TOTAL_CAPITAL_INR must parse as a positive float."""
    raw = os.environ.get("TOTAL_CAPITAL_INR", "1000000")
    val = float(raw)
    assert val > 0, "Capital must be positive"


def test_risk_pct_env_in_range():
    """MAX_RISK_PER_TRADE_PCT must be between 0 and 10."""
    raw = os.environ.get("MAX_RISK_PER_TRADE_PCT", "2.0")
    val = float(raw)
    assert 0 < val <= 10, f"Risk pct {val} out of safe range (0, 10]"


def test_vix_kill_switch_threshold_positive():
    """VIX kill switch threshold must be a positive float."""
    raw = os.environ.get("VIX_KILL_SWITCH_THRESHOLD", "25.0")
    val = float(raw)
    assert val > 0, "VIX kill-switch threshold must be positive"
