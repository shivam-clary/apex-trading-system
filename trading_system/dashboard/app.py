"""
APEX Trading System — Streamlit Dashboard
Real-time monitoring UI for signals, positions, P&L, and risk metrics.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone

try:
    import streamlit as st
    import pandas as pd
except ImportError:
    raise ImportError("Install streamlit and pandas: pip install streamlit pandas")


def render_header():
    st.set_page_config(
        page_title="APEX Trading System",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("📈 APEX Trading System")
    st.caption(f"Live dashboard — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")


def render_system_status(sidebar):
    sidebar.header("System Status")
    sidebar.metric("Engine", "RUNNING", delta=None)
    sidebar.metric("Agents Active", "20")
    sidebar.metric("Market", "OPEN")
    if sidebar.button("EMERGENCY STOP", type="primary"):
        sidebar.error("Emergency stop triggered!")


def render_risk_metrics(col):
    col.subheader("Risk Metrics")
    c1, c2, c3, c4 = col.columns(4)
    c1.metric("Daily P&L", "Rs 0", delta="0%")
    c2.metric("Drawdown", "0.0%")
    c3.metric("Kill Switch", "OFF")
    c4.metric("Open Positions", "0 / 6")


def render_signals(col):
    col.subheader("Agent Signals")
    sample_signals = [
        {"Agent": "TechnicalAnalysis", "Direction": "BULLISH", "Confidence": 0.72},
        {"Agent": "MarketRegime", "Direction": "NEUTRAL", "Confidence": 0.55},
        {"Agent": "OptionsDerivatives", "Direction": "BEARISH", "Confidence": 0.61},
        {"Agent": "FIIDIIFlow", "Direction": "BULLISH", "Confidence": 0.68},
        {"Agent": "SentimentPositioning", "Direction": "NEUTRAL", "Confidence": 0.48},
    ]
    df = pd.DataFrame(sample_signals)
    col.dataframe(df, use_container_width=True, hide_index=True)


def render_positions(col):
    col.subheader("Open Positions")
    col.info("No open positions")


def render_equity_curve(col):
    col.subheader("Equity Curve (Today)")
    col.line_chart({"Capital": [1_000_000] * 10})


def render_trade_log(col):
    col.subheader("Recent Trades")
    col.info("No trades today")


def main():
    render_header()
    sidebar = st.sidebar
    render_system_status(sidebar)

    top = st.container()
    with top:
        render_risk_metrics(top)

    col1, col2 = st.columns(2)
    render_signals(col1)
    render_positions(col2)

    col3, col4 = st.columns(2)
    render_equity_curve(col3)
    render_trade_log(col4)

    # Auto-refresh every 5 seconds
    time.sleep(5)
    st.rerun()


if __name__ == "__main__":
    main()
