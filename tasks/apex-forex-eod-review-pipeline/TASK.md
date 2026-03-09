---
slug: apex-forex-eod-review-pipeline
title: APEX Forex — EOD Review Pipeline
steps:
- description: 'Run Forex Performance Monitor: read FOREX_PAPER_LEDGER, FOREX_SIGNALS,
    FOREX_VETO_REPORT, FOREX_MARKET_REGIME from Upstash Redis DB1. Compute all metrics
    (Sharpe, Calmar, Sortino, win rate, profit factor, max drawdown, per-pair/strategy/regime
    P&L). Send richly formatted daily performance email to sujaysn6@gmail.com. Write
    FOREX_PERFORMANCE_SNAPSHOT directly to Upstash Redis DB2 (TTL 86400s).'
  agent_id: agt_069ad6ac99c87ee180003961720881eb
  agent_slug: forex-performance-monitor
  format_guide: 'Send email with subject: APEX Forex Paper Trading Report - [DATE] | Daily
    P&L: INR [AMOUNT] | Win Rate: [%]. Include session summary, positions table, per-strategy
    metrics, risk-adjusted metrics, veto summary, decay alerts, ASCII P&L chart, SEBI
    compliance footer.'
- description: 'Run APEX Forex Self-Evolution Engine: read FOREX_PAPER_LEDGER, FOREX_SIGNALS,
    FOREX_VETO_REPORT from Upstash Redis DB1. Analyze strategy performance across last
    5 sessions. Detect regime-strategy mismatches. Compute updated confidence multipliers.
    Flag underperforming strategies for pause. Write FOREX_STRATEGY_WEIGHTS and FOREX_EVOLUTION_LOG
    directly to Upstash Redis DB2 (TTL 604800s). On Sundays only, send weekly evolution email.'
  agent_id: agt_069ad50fa2ef7adf800029ec9f17de44
  agent_slug: forex-self-evolution-engine
---
