---
slug: apex-forex-eod-review-pipeline
title: APEX Forex — EOD Review Pipeline
steps:
- description: 'Run Forex Performance Monitor: read FOREX_PAPER_LEDGER, FOREX_SIGNALS,
    FOREX_VETO_REPORT, FOREX_MARKET_REGIME from memory. Compute all metrics (Sharpe,
    Calmar, Sortino, win rate, profit factor, max drawdown, per-pair/strategy/regime
    P&L, strategy decay). Send richly formatted daily performance email to sujaysn6@gmail.com.
    Output PERFORMANCE_STRING for memory.'
  agent_id: agt_069ad6ac99c87ee180003961720881eb
  agent_slug: forex-performance-monitor
  format_guide: 'Send email with subject: APEX Forex Paper Trading Report - [DATE]
    | Daily P&L: INR [AMOUNT] | Win Rate: [%]. Include session summary, positions
    table, per-strategy metrics, risk-adjusted metrics, veto summary, decay alerts,
    ASCII P&L chart, SEBI compliance footer. Also output PERFORMANCE_STRING: date:<ISO>|sharpe:<val>|calmar:<val>|sortino:<val>|win_rate:<val>|profit_factor:<val>|max_drawdown:<val>|daily_pnl:<val>|total_trades:<val>|decay_flags:<strategy_name
    or NONE>'
- description: Write FOREX_PERFORMANCE_SNAPSHOT to memory
  agent_slug: nebula
  format_guide: 'Read PERFORMANCE_STRING from $prev. Call manage_memories: key=FOREX_PERFORMANCE_SNAPSHOT,
    value=PERFORMANCE_STRING, category=user_preference, scope=global. Plain string
    only. Output memory_write_status.'
- description: 'Run APEX Forex Self-Evolution Engine: read FOREX_PAPER_LEDGER, FOREX_SIGNALS,
    FOREX_VETO_REPORT from memory. Analyze strategy performance across last 5 sessions.
    Detect regime-strategy mismatches. Compute updated confidence multipliers. Flag
    underperforming strategies for pause. On Sundays only, send weekly evolution email.
    Output WEIGHTS_STRING and EVOLUTION_LOG_STRING — do NOT call manage_memories yourself.'
  agent_id: agt_069ad50fa2ef7adf800029ec9f17de44
  agent_slug: forex-self-evolution-engine
  format_guide: 'Output WEIGHTS_STRING: strategy_id:<weight_multiplier>|strategy_id:<weight_multiplier>...
    (multipliers 0.5-1.5). Output EVOLUTION_LOG_STRING: timestamp:<ISO>|strategies_updated:<count>|strategies_paused:<list
    or NONE>|weight_changes:<strategy>:<old>-><new>;<next...>|regime_accuracy:<val>|recommendations:<text>'
- description: Write FOREX_STRATEGY_WEIGHTS and append to FOREX_EVOLUTION_LOG in memory
  agent_slug: nebula
  format_guide: 'Read WEIGHTS_STRING and EVOLUTION_LOG_STRING from $prev. Call manage_memories
    twice: (1) key=FOREX_STRATEGY_WEIGHTS, value=WEIGHTS_STRING, category=user_preference,
    scope=global. (2) key=FOREX_EVOLUTION_LOG, value=EVOLUTION_LOG_STRING, category=user_preference,
    scope=global. Plain strings only. Output memory_write_status for both.'
---
