# APEX Trading System

**Autonomous Prediction & Execution System** — A fully autonomous AI-powered intraday options trading system for Indian markets (NSE/BSE), built on Nebula's multi-agent orchestration platform.

> **Status:** Paper Trading (PAPER_MODE=true) | Sessions: 18 | Latest Win Rate: 100%

---

## What Is APEX?

APEX is a 24/7 autonomous trading system that:
- Monitors global macro events overnight (US open, Asia session, pre-Europe)
- Classifies Indian market regime every 15 minutes during market hours
- Generates options trade signals based on live option chain + sentiment + macro data
- Routes every signal through a mandatory risk veto gate before execution
- Paper trades on NSE/BSE via Dhan API with realistic slippage simulation
- Sends EOD performance reports by email every day at 15:35 IST

No human intervention required. The system runs fully autonomously from 02:00 IST overnight through 15:35 IST market close.

---

## Architecture

```
02:00 IST   Asia/Pre-Europe Scan    -> GLOBAL_SENTIMENT_COMPOSITE
08:00 IST   Global Macro Scan       -> GLOBAL_SENTIMENT
09:00 IST   Regime Classification   -> MARKET_STATE
09:15 IST   Option Chain Monitor    -> OPTIONS_STATE  (every 3 sec)
            Sentiment Engine        -> SENTIMENT_STATE (every 5 min)

Every 15 min (09:15-15:30):
  Regime Engine -> Options Strategy Engine -> Risk Veto -> Paper Trade Engine

Every 5 min (09:15-15:30):
  Paper Trade Engine -> SL/Target checks -> MTM P&L update

15:35 IST   EOD Reconciliation -> DAILY_REPORT -> Email digest

21:30 IST   US Market Open Scan    -> GLOBAL_SENTIMENT_USOPEN
```

---

## Agent Network (13 Agents)

| Agent | Role |
|---|---|
| `india-trading-central-command` | Master orchestrator, morning briefing, EOD, KILL_SWITCH owner |
| `global-macro-intelligence-scanner` | Bloomberg/Reuters/CNBC/FT/Twitter macro scan |
| `india-market-regime-engine` | VIX/PCR/FII/SGX regime classifier (every 15 min) |
| `nse-option-chain-monitor` | OI/IV/GEX/Max Pain poller (every 3 sec) |
| `sentiment-intelligence-engine` | ET/MoneyControl/Twitter NLP sentiment |
| `options-strategy-engine` | Signal generator (6 strategy types) |
| `trading-risk-veto-authority` | Mandatory risk gate, Kelly sizing, kill switch |
| `dhan-paper-trade-engine` | Paper fills at mid-price, full ledger |
| `dhan-live-order-executor` | Live bracket/super orders (standing by) |
| `live-trade-performance-monitor` | Sharpe/Calmar/Sortino, EOD email |
| `nse-strategy-validation-engine` | 5yr backtest with real costs |
| `india-market-regime-engine` | Also runs standalone every 15 min |
| `polymarket-trading-agent` | Prediction market CLOB trading (parallel) |

---

## Automation Triggers (6 Active)

| Trigger | Schedule | What It Does |
|---|---|---|
| Daily Session Pipeline | 08:00 IST weekdays | 8-step full session: macro -> regime -> signal -> veto -> execute -> EOD |
| 15-Min Regime + Signal Loop | Every 15 min, market hours | Regime reclassify -> signal -> veto -> paper execute |
| SL/Target Monitor | Every 5 min, market hours | Check SL/target hits, update MTM P&L |
| EOD Reconciliation | 15:35 IST weekdays | Close positions, final P&L, email report |
| US Market Open Scan | 21:30 IST weekdays | NYSE open macro intelligence |
| Asia/Pre-Europe Scan | 02:00 IST Sun-Thu | SGX/Nikkei/Hang Seng overnight scan |

---

## Shared Memory Protocol

All agents communicate via **Nebula shared memory** under the `APEX_TRADING` namespace. No direct agent-to-agent calls.

```
GLOBAL_SENTIMENT        -> score [-1.0 to +1.0], label, directional_bias   (TTL: 4h)
GLOBAL_SENTIMENT_USOPEN -> US open scan output                              (TTL: session)
GLOBAL_SENTIMENT_ASIA   -> Asia scan output + composite                     (TTL: session)
MARKET_STATE            -> regime, VIX, PCR, FII/DII, strategy_type        (TTL: 20min)
OPTIONS_STATE           -> OI, IV rank, GEX walls, max pain, PCR            (TTL: 5min)
SENTIMENT_STATE         -> NLP scores by sector                             (TTL: 10min)
TRADE_SIGNAL            -> full leg spec, SL, target, confidence            (TTL: until executed)
APPROVED_SIGNALS        -> veto-passed signals ready for execution          (TTL: until executed)
EXECUTION_RECORD        -> fill prices, P&L, status                        (Permanent)
PAPER_LEDGER            -> running positions, MTM                           (Live)
DAILY_PNL               -> realized + unrealized, win/loss count            (Daily reset)
KILL_SWITCH             -> active bool, reason, activated_by                (Manual reset)
```

---

## Hard Rules (Cannot Be Overridden)

1. No signal valid if GLOBAL_SENTIMENT > 4h old
2. No signal valid if MARKET_STATE > 20min old
3. No order without TRADE_SIGNAL.status = APPROVED
4. KILL_SWITCH.active = true blocks everything immediately
5. Risk Veto checks KILL_SWITCH before any signal evaluation
6. Max 3 concurrent open positions
7. Only Central Command can reset KILL_SWITCH
8. No naked options -- ever
9. Half-Kelly sizing on all positions
10. Daily loss circuit breaker at -2% of capital

---

## Risk Framework

- **Per-trade risk:** 0.5% of capital max
- **Daily loss limit:** 2% of capital (triggers KILL_SWITCH)
- **Position sizing:** Half-Kelly Criterion
- **Max concurrent:** 3 positions
- **Naked options:** Hard rejected always

---

## Instruments

| Index | Lot Size | Expiry | Status |
|---|---|---|---|
| NIFTY 50 | 75 | Weekly Thu | Active |
| BANKNIFTY | 30 | Weekly Wed | Active |
| BANKEX | 15 | Weekly Mon | Active |
| FINNIFTY | 40 | Weekly Tue | Monitored |
| MIDCPNIFTY | 75 | Monthly | Monitored |

---

## Performance (Paper -- Sessions 1-18)

| Metric | Value |
|---|---|
| Net P&L (latest session) | +Rs 4,880.80 (+0.651%) |
| Gross Realized | +Rs 6,259.50 |
| Charges | -Rs 331.70 |
| Win Rate | 100% (2/2 closed) |
| Risk Budget Used | 45.9% |
| Open Overnight Positions | 2 |

---

*Built with Nebula multi-agent orchestration. PAPER_MODE=true -- no real capital at risk.*
