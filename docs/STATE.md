# APEX State Management

## Primary State File
Path: data/APEX_STATE.json

This is the authoritative state store. All agents read from and write to this file.
Nebula memory is used as a secondary cache but is non-blocking on failure.

## State Keys
| Key | Owner Agent | Description |
|---|---|---|
| MARKET_REGIME | india-market-regime-engine | Current regime, confidence, bias, VIX, crude |
| SENTIMENT_SNAPSHOT | sentiment-intelligence-engine | NLP scores from 4 sources |
| OPTION_CHAIN_SNAPSHOT | nse-option-chain-monitor | PCR, GEX, IV rank for 4 indices |
| TRADE_SIGNALS | options-strategy-engine | Active and conditional signals |
| APPROVED_SIGNALS | trading-risk-veto-authority | Risk-vetted signals + gate audit |
| PAPER_LEDGER | dhan-paper-trade-engine | Positions, MTM, daily P&L |
| PERFORMANCE_SNAPSHOT | live-trade-performance-monitor | Sharpe, Calmar, decay flag |
| VALIDATION_RESULT | apex-validator-gate | Per-component PASS/WARN/FAIL |
| GLOBAL_SENTIMENT_ASIA | global-macro-intelligence-scanner | Overnight Asia + macro |
| HEALTH_STATUS | apex-system-health-monitor | System health + issues |
| ERROR_LOG | apex-error-monitor | All errors with recurrence counts |
| FIX_HISTORY | tony-autonomous-senior-dev | Fix attempts and outcomes |
| MONDAY_PREOPEN_WATCHLIST | india-trading-central-command | Monday priority queue |
| TRIGGER_REGISTRY | nebula-orchestrator | All 18 trigger definitions |

## Write Protocol
1. Agent reads full data/APEX_STATE.json
2. Agent updates only its own section key
3. Agent writes back via str_replace on that key
4. Agent attempts manage_memories write (non-blocking)
5. If manage_memories fails, file is still authoritative

## Known Issues
- manage_memories tool has serialization errors in triggered execution contexts
- File fallback is production-hardened and has been live since 2026-03-06
