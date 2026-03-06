---
slug: apex-15-min-live-update-to-channel
title: APEX — 15-Min Live Update to Channel
steps:
- description: Classify current market regime
  agent_slug: india-market-regime-engine
  format_guide: Read APEX_TRADING memory for GLOBAL_SENTIMENT_COMPOSITE. Fetch fresh
    India VIX, PCR, FII/DII flow data. Classify regime as TRENDING_UP/TRENDING_DOWN/RANGE_BOUND/HIGH_VOLATILITY
    with confidence 0-100. Write MARKET_REGIME to memory with label, confidence, vix_band,
    fii_flow, bias, timestamp. Output regime summary.
- description: Generate options trade signals based on current regime
  agent_slug: options-strategy-engine
  format_guide: Read MARKET_REGIME from memory (). Generate 1-3 NIFTY/BANKNIFTY
    options signals with symbol, strategy, strikes, expiry, entry_price, stop_loss,
    target, confidence, rationale. Write TRADE_SIGNALS to memory.
- description: Risk veto — approve or reject each signal
  agent_slug: trading-risk-veto-authority
  format_guide: Read TRADE_SIGNALS and PAPER_LEDGER from memory. Apply 2% daily loss
    circuit breaker, 0.5% per-trade risk, max 3 concurrent positions, Kelly sizing.
    APPROVE or VETO each signal with reason. Write APPROVED_SIGNALS and VETO_REPORT
    to memory.
- description: Paper trade execution and SL/target monitoring
  agent_slug: dhan-paper-trade-engine
  format_guide: Read PAPER_LEDGER open positions. Fetch live LTP via Dhan API. Check
    SL/target hits, close triggered positions. Execute APPROVED_SIGNALS as new paper
    trades at mid-price. Update PAPER_LEDGER and PAPER_STATS with MTM P&L. Output
    position status table.
- description: 'Post live update to #apex-live-trading channel'
  agent_slug: nebula
  format_guide: 'Read MARKET_REGIME, APPROVED_SIGNALS, VETO_REPORT, PAPER_LEDGER from
    memory. Get current IST time (UTC+5:30). Post using send_channel_message with
    channel_id=''thrd_069aa5f60dcd7c0580006addd4eab20d'' (NEVER use channel name —
    always use this channel_id). Format:

    **APEX LIVE — [HH:MM IST]**
    **REGIME:** [label] | Conf: [X]% | Bias: [bias] | VIX: [band]
    **MACRO:** Score [score] [label] | Crude: [price] | DXY: [level]
    **SIGNALS:** [APPROVED/VETOED] [symbol] [strategy] — Entry:[price] SL:[price] Tgt:[price] Conf:[X]%
    **POSITIONS:**
    | Symbol | Entry | LTP | MTM | SL dist | Tgt dist | DTE |
    **P&L:** Total:[amt] | Realized:[amt] | Unrealized:[amt] | WinRate:[X]% | DailyDD:[X]%'
---

Runs every 15 minutes during NSE market hours (09:15–15:30 IST) via cron */15 9-15 * * 1-5. Each trigger fires one full pipeline cycle: regime classification → signal generation → risk veto → paper trade execution → live channel post to #apex-live-trading.
