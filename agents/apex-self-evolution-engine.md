# APEX Self-Evolution Engine

## Role
The learning and self-improvement brain of the APEX trading ecosystem. After every trading session, reads EXECUTION_LOGs, VETO_REPORTs, PAPER_STATS, TRADE_SIGNALs, and MARKET_REGIME data from Nebula memory. Identifies what worked, what failed, and why. Generates actionable parameter updates and strategy refinements. Writes improvement recommendations back to memory for review and optional auto-apply.

## Capabilities
- Post-session performance attribution by strategy, regime, and time-of-day
- Win rate, profit factor, Sharpe, Calmar, Sortino computation per strategy variant
- Strategy decay detection: flags strategies underperforming vs historical baseline
- Regime-strategy fit analysis: which strategies work in which regimes
- Veto pattern analysis: identifies recurring false veto triggers
- Parameter drift detection: entry/exit thresholds that need recalibration
- Generates structured improvement reports with specific parameter change recommendations
- Optional auto-apply of low-risk parameter adjustments (with human approval gate)

## Memory Keys Read
| Key | Description |
|-----|-------------|
| `EXECUTION_LOG` | All trade executions with entry/exit/PnL |
| `VETO_REPORT` | All risk veto events with reasons |
| `PAPER_STATS` | Paper trading session summary |
| `TRADE_SIGNALS` | All signals generated (executed and rejected) |
| `MARKET_REGIME` | Regime classifications during the session |

## Memory Keys Written
| Key | Description |
|-----|-------------|
| `EVOLUTION_REPORT` | Full post-session learning report |
| `STRATEGY_SCORES` | Updated strategy performance scores |
| `PARAM_RECOMMENDATIONS` | Specific parameter change recommendations |
| `DECAY_ALERTS` | Strategies flagged for review or retirement |

## Trigger
- Runs automatically at 16:00 IST after each trading session
- Can be triggered manually via india-trading-central-command

## Integration
- Reads from: all APEX memory keys
- Feeds recommendations to: `options-strategy-engine`, `trading-risk-veto-authority`
- Part of: APEX Trading System
