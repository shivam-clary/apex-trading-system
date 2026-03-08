---
slug: nse-strategy-monthly-walk-forward-validation
title: NSE Strategy — Monthly Walk-Forward Validation
steps:
- description: Fetch latest 30 days of NSE market data (NIFTY, BANKNIFTY, FINNIFTY)
    and read current strategy configurations from memory (STRATEGY_LIBRARY, PAPER_STATS,
    EXECUTION_LOG)
  agent_id: agt_069a8e1487b6720a80009919272cb407
  agent_slug: nse-strategy-validation-engine
  format_guide: 'Read memory keys: STRATEGY_LIBRARY, PAPER_STATS, EXECUTION_LOG. Fetch
    NSE historical OHLCV data for NIFTY 50, BANKNIFTY, FINNIFTY for the past 30 calendar
    days via Dhan API or web. Output structured dict with: strategies (list with name,
    params), market_data (symbol -> OHLCV list), paper_stats (trades list with entry/exit/pnl)'
- description: Run walk-forward validation on each active strategy — compute Sharpe,
    Calmar, Sortino, max drawdown, win rate, profit factor with real NSE charges (brokerage
    0.03%, STT 0.1%, stamp duty 0.015%)
  agent_id: agt_069a8e1487b6720a80009919272cb407
  agent_slug: nse-strategy-validation-engine
  format_guide: 'For each strategy in $prev.strategies, run walk-forward backtest
    on $prev.market_data applying $prev.paper_stats slippage baseline. Apply charges:
    brokerage 0.03%, STT 0.1% on sell side, stamp duty 0.015%. Compute per-strategy:
    sharpe_ratio, calmar_ratio, sortino_ratio, max_drawdown_pct, win_rate_pct, profit_factor,
    total_trades. Apply hard gates: REJECT if sharpe < 1.0 OR max_drawdown > 15%.
    Output: validation_results (list), passed (list), rejected (list), overall_grade
    (A/B/C/D)'
- description: Recalibrate strategy confidence grades and produce the full validation
    report text
  agent_id: agt_069a8e1487b6720a80009919272cb407
  agent_slug: nse-strategy-validation-engine
  format_guide: 'Using $prev.validation_results, assign confidence grades: A (sharpe>2.0,
    dd<8%), B (sharpe>1.5, dd<12%), C (sharpe>1.0, dd<15%), D (below gates — flag
    for review). Produce: report_text (full narrative markdown), grades (dict strategy->grade,
    e.g. {S1: A, S2: D}), summary_line (one-sentence overall verdict). Do NOT call
    manage_memories — output only.'
- description: Write STRATEGY_VALIDATION_REPORT and STRATEGY_CONFIDENCE_GRADES to
    memory
  agent_slug: nebula
  format_guide: 'Read $prev.report_text (a markdown string) and $prev.grades (a dict
    like {S1: A, S2: D}). Call manage_memories twice using category=user_preference
    and scope=global: (1) key=STRATEGY_VALIDATION_REPORT, value=$prev.report_text
    as a plain string. (2) key=STRATEGY_CONFIDENCE_GRADES, value=the grades dict serialized
    as a pipe-delimited plain string like S1:A|S2:B|S3:D — NOT a JSON object. Value
    must be a plain scalar string only. Confirm both writes and output memory_write_status:
    success or failed with detail.'
- description: Send validation report email to sujaysn6@gmail.com with full results,
    grades, and any strategy rejections
  agent_id: agt_069a7092b6cf74318000264e0404edba
  agent_slug: inbox-agent
  action_key: send-nebula-email
  format_guide: 'Compose a detailed HTML email to sujaysn6@gmail.com with subject:
    ''[APEX] NSE Strategy Walk-Forward Validation — {current_month} {year}''. Body
    must include: 1) Overall grade summary table, 2) Per-strategy results (Sharpe,
    Calmar, drawdown, win rate, profit factor), 3) PASSED strategies list with grades,
    4) REJECTED strategies list with reasons, 5) Recommended parameter adjustments
    for next month. Use $prev.report_text and $prev.grades as source data.'
---
