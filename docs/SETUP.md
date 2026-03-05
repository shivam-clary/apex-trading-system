# APEX Trading System — Setup Guide

> Complete instructions for deploying the APEX Autonomous Trading System on Nebula's multi-agent platform.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Platform Setup — Nebula](#2-platform-setup--nebula)
3. [Broker & API Connections](#3-broker--api-connections)
4. [Agent Configuration](#4-agent-configuration)
5. [Memory Namespace Initialization](#5-memory-namespace-initialization)
6. [Trigger Activation](#6-trigger-activation)
7. [Paper Trading First Run](#7-paper-trading-first-run)
8. [Going Live — Checklist](#8-going-live--checklist)
9. [Environment Variables Reference](#9-environment-variables-reference)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### Accounts Required

| Service | Purpose | Free Tier? |
|---------|---------|------------|
| [Nebula](https://nebula.gg) | Multi-agent orchestration platform | Yes |
| [Dhan](https://dhan.co) | NSE/BSE broker — live order execution | Yes (trading account) |
| [Indian API](https://indianapi.in) | Historical NSE data, option chain | Paid |
| Dhan Market Data API | Live quotes, option chain streaming | Included with Dhan account |

### Optional (for enhanced intelligence)

| Service | Purpose |
|---------|---------|
| StockTwits Whisperer | Social sentiment feed for Indian markets |
| AssemblyAI | Call transcription for earnings intelligence |
| Fireflies.ai | Meeting intelligence integration |

### Knowledge Requirements

- Basic understanding of options trading (calls, puts, spreads)
- Familiarity with NSE instruments: NIFTY, BANKNIFTY, FINNIFTY
- Python not required — system runs entirely on Nebula platform

---

## 2. Platform Setup — Nebula

### Step 1: Create a Nebula Account

1. Go to [nebula.gg](https://nebula.gg) and sign up
2. Verify your email address
3. Complete onboarding — you will land on the main chat interface

### Step 2: Fork / Import This Repository

This repo contains documentation only — the actual agents and triggers live inside Nebula. Use the docs here as the blueprint for recreating the system.

### Step 3: Connect Required Apps

In Nebula, navigate to **Settings > Connected Apps** and connect:

```
1. Dhan (broker)         — OAuth or API key
2. Indian API            — API key
3. Gmail / Email         — For EOD report delivery
```

Each app connection is done once. All agents share the same OAuth tokens automatically.

---

## 3. Broker & API Connections

### Dhan API Setup

1. Log in to your Dhan account at [dhan.co](https://dhan.co)
2. Go to **API & Developer Tools**
3. Generate your **Client ID** and **Access Token**
4. Note: Dhan access tokens expire every 24 hours — regenerate daily or use Dhan's token refresh flow

```
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token   # regenerate daily
```

**Important:** APEX reads `DHAN_ACCESS_TOKEN` from agent memory at execution time. Update this variable daily before 09:00 IST.

### Indian API Setup

1. Register at [indianapi.in](https://indianapi.in)
2. Subscribe to the **Options + Historical** plan
3. Copy your API key

```
INDIANAPI_API_KEY=your_api_key
```

### StockTwits Whisperer (Optional)

1. Register for the StockTwits Whisperer API
2. Get your Bearer Token and API Key

```
STOCKTWITS_WHISPERER_API_BEARERTOKEN=your_bearer_token
STOCKTWITS_WHISPERER_API_KEY=your_api_key
```

---

## 4. Agent Configuration

APEX uses **13 specialized agents** on Nebula. Each must be created with the correct identity, tools, and memory access. Below is the recommended creation order (dependencies first).

### Creation Order

```
1.  india-trading-central-command     (master orchestrator — create first)
2.  global-macro-intelligence-scanner
3.  india-market-regime-engine
4.  sentiment-intelligence-engine
5.  nse-option-chain-monitor
6.  options-strategy-engine
7.  trading-risk-veto-authority       (create before execution agents)
8.  dhan-paper-trade-engine
9.  dhan-live-order-executor
10. live-trade-performance-monitor
11. nse-strategy-validation-engine
12. nse-option-chain-monitor
13. india-trading-central-command     (configure cross-references last)
```

### Setting Agent Variables

For each agent, set required variables via **Nebula Agent Settings > Variables**:

#### dhan-paper-trade-engine
```
DHAN_CLIENT_ID           = <your client id>
DHAN_ACCESS_TOKEN        = <your token>
PAPER_MODE               = true        # set false for live trading
```

#### dhan-live-order-executor
```
DHAN_CLIENT_ID           = <your client id>
DHAN_ACCESS_TOKEN        = <your token>
MAX_ORDER_VALUE          = 50000       # per-order cap in INR
```

#### india-market-regime-engine
```
INDIANAPI_API_KEY        = <your key>
REGIME_LOOKBACK_BARS     = 20
```

#### sentiment-intelligence-engine
```
STOCKTWITS_WHISPERER_API_BEARERTOKEN = <token>
STOCKTWITS_WHISPERER_API_KEY         = <key>
```

#### trading-risk-veto-authority
```
DAILY_LOSS_LIMIT_PCT     = 2.0         # % of capital
PER_TRADE_RISK_PCT       = 0.5
MAX_CONCURRENT_POSITIONS = 3
PAPER_MODE               = true
```

---

## 5. Memory Namespace Initialization

APEX uses Nebula's shared memory under the `APEX_TRADING` namespace. Before first run, initialize the kill switch and paper ledger.

### Initialize via Nebula Chat

Paste the following into the Nebula chat to bootstrap memory:

```
Initialize APEX_TRADING memory namespace with:
- KILL_SWITCH: {"active": false, "reason": "", "set_by": "manual_init", "timestamp": "<now>"}
- PAPER_LEDGER: {"cash_balance": 750000, "positions": [], "realized_pnl": 0, "total_charges": 0, "trade_count": 0}
- DAILY_PNL: {"date": "<today>", "realized": 0, "unrealized": 0, "charges": 0, "net": 0, "risk_budget_used_pct": 0}
```

**Capital allocation:** Default is Rs 7,50,000 (750K INR). Adjust `cash_balance` to match your actual capital.

### Key Memory Keys

| Key | Description | Writer |
|-----|-------------|--------|
| `GLOBAL_SENTIMENT` | Pre-session macro score (-1 to +1) | global-macro-intelligence-scanner |
| `GLOBAL_SENTIMENT_USOPEN` | US open sentiment | global-macro-intelligence-scanner |
| `GLOBAL_SENTIMENT_ASIA` | Asia/overnight sentiment | global-macro-intelligence-scanner |
| `MARKET_STATE` | Current regime + bias | india-market-regime-engine |
| `OPTIONS_STATE` | Live OI, PCR, IV data | nse-option-chain-monitor |
| `TRADE_SIGNAL` | Pending approved signals | options-strategy-engine |
| `EXECUTION_RECORD` | Trade fills and records | dhan-paper-trade-engine |
| `PAPER_LEDGER` | Running P&L and positions | dhan-paper-trade-engine |
| `DAILY_PNL` | Today's performance summary | live-trade-performance-monitor |
| `KILL_SWITCH` | Emergency halt flag | india-trading-central-command |

---

## 6. Trigger Activation

APEX runs on 6 scheduled triggers. Activate them in this order after all agents are configured.

### Full Trigger Schedule

| Trigger | IST Time | UTC Cron | Days |
|---------|----------|----------|------|
| Asia/Pre-Europe Scan | 02:00 IST | `0 20 * * 0-4` | Sun-Thu |
| Daily Session Pipeline | 08:00 IST | `0 2 * * 1-5` | Mon-Fri |
| 15-Min Regime + Signal Loop | Every 15 min | `*/15 9-15 * * 1-5` | Mon-Fri |
| SL/Target Monitor | Every 5 min | `*/5 9-15 * * 1-5` | Mon-Fri |
| EOD Reconciliation | 15:35 IST | `5 10 * * 1-5` | Mon-Fri |
| US Market Open Scan | 21:30 IST | `0 16 * * 1-5` | Mon-Fri |

**Note:** All crons are in UTC. India Standard Time = UTC + 5:30.

### Create Triggers via Nebula Chat

```
"Create a cron trigger that runs at 0 20 * * 0-4 UTC using recipe 
tasks/apex-asia-pre-europe-scan/TASK.md"
```

Repeat for each trigger in the table above.

---

## 7. Paper Trading First Run

Once all agents and triggers are configured, verify the system with a manual end-to-end test.

### Verification Sequence

**Step 1: Trigger macro scan manually**
```
Ask Nebula: "Run the global macro intelligence scanner and write GLOBAL_SENTIMENT to memory"
```

**Step 2: Run regime classification**
```
Ask Nebula: "Run india-market-regime-engine and classify today's market regime"
```

**Step 3: Generate a signal**
```
Ask Nebula: "Run options-strategy-engine against current OPTIONS_STATE and generate a trade signal"
```

**Step 4: Veto check**
```
Ask Nebula: "Run trading-risk-veto-authority against the latest TRADE_SIGNAL"
```

**Step 5: Paper execute**
```
Ask Nebula: "Run dhan-paper-trade-engine to execute any APPROVED TRADE_SIGNALs in paper mode"
```

**Step 6: Verify ledger**
```
Ask Nebula: "Show me the current PAPER_LEDGER — positions, cash balance, and P&L"
```

If all 6 steps succeed without errors, your system is operational.

---

## 8. Going Live — Checklist

**DO NOT switch to live trading until every item below is checked.**

### Technical Readiness

- [ ] Paper trading running for minimum 30 sessions
- [ ] Win rate > 50% over last 20 sessions
- [ ] Max drawdown < 8% in paper mode
- [ ] Sharpe ratio > 1.0 (validated by nse-strategy-validation-engine)
- [ ] All 6 triggers firing correctly with no missed runs
- [ ] DHAN_ACCESS_TOKEN refresh process automated or calendared daily
- [ ] Emergency KILL_SWITCH tested and confirmed working

### Capital & Risk

- [ ] Dedicated trading capital allocated (separate from savings)
- [ ] Daily loss limit set to 2% of capital in trading-risk-veto-authority
- [ ] Per-trade risk set to 0.5% max
- [ ] Max 3 concurrent positions confirmed in veto agent
- [ ] EOD email reports verified to your inbox

### Switch to Live

1. Set `PAPER_MODE = false` in dhan-paper-trade-engine variables
2. Set `PAPER_MODE = false` in trading-risk-veto-authority variables
3. Confirm `DHAN_ACCESS_TOKEN` is fresh (less than 24 hours old)
4. Run a manual veto check to confirm all gates pass
5. Let the 09:15 trigger fire naturally — do not manually trigger on first live day

---

## 9. Environment Variables Reference

| Variable | Agent | Required | Description |
|----------|-------|----------|-------------|
| `DHAN_CLIENT_ID` | paper-trade, live-executor | Yes | Dhan account client ID |
| `DHAN_ACCESS_TOKEN` | paper-trade, live-executor | Yes | Daily-refresh Dhan token |
| `INDIANAPI_API_KEY` | regime-engine, strategy-validator | Yes | Indian API access key |
| `STOCKTWITS_WHISPERER_API_BEARERTOKEN` | sentiment-engine, macro-scanner | Optional | Social sentiment feed |
| `STOCKTWITS_WHISPERER_API_KEY` | sentiment-engine, macro-scanner | Optional | Social sentiment key |
| `PAPER_MODE` | paper-trade, risk-veto | Yes | `true` = paper, `false` = live |
| `DAILY_LOSS_LIMIT_PCT` | risk-veto | Yes | Default: `2.0` |
| `PER_TRADE_RISK_PCT` | risk-veto | Yes | Default: `0.5` |
| `MAX_CONCURRENT_POSITIONS` | risk-veto | Yes | Default: `3` |
| `MAX_ORDER_VALUE` | live-executor | Yes | Per-order INR cap |
| `ASSEMBLYAI_API_KEY` | call-intelligence | Optional | Call transcription |
| `FIREFLIES_API_KEY` | call-intelligence | Optional | Meeting intelligence |

---

## 10. Troubleshooting

### "HTTP 401 Unauthorized" from Dhan API

**Cause:** `DHAN_ACCESS_TOKEN` expired (tokens expire every 24 hours).
**Fix:** Log in to dhan.co, generate a new access token, update the variable in both `dhan-paper-trade-engine` and `dhan-live-order-executor` agent settings.

### Trigger fires but no signal generated

**Cause 1:** Market is closed or it is a public holiday — regime engine returns `NO_TRADE`.
**Cause 2:** `OPTIONS_STATE` in memory is stale (more than 20 minutes old).
**Fix:** Check memory freshness. Ask Nebula: *"Show me the timestamp on OPTIONS_STATE in APEX_TRADING memory"*

### KILL_SWITCH is active — all trades blocked

**Cause:** Daily loss limit hit, or manually activated.
**Fix:** Ask Nebula: *"Show me KILL_SWITCH in APEX_TRADING memory"* and check the `reason` field.
**Reset (only after root cause resolved):** *"Set KILL_SWITCH active=false in APEX_TRADING memory"*

### Regime classified as AVOID / NO_TRADE

This is correct behavior. The system is designed to sit out when conditions are unfavorable. Do not override manually.

### EOD email not received

**Cause:** Gmail not connected, or `india-trading-central-command` lacks email access.
**Fix:** Reconnect email in Nebula Settings > Connected Apps, then re-delegate EOD task manually to confirm it works.

### Memory reads returning null / stale data

**Cause:** An upstream agent in the pipeline failed silently.
**Fix:** Run each pipeline stage manually in sequence (Steps 1-6 from Section 7) to identify which agent is failing.

---

## Support & References

- Nebula Platform: [nebula.gg](https://nebula.gg)
- APEX Architecture: [APEX_ARCHITECTURE.md](./APEX_ARCHITECTURE.md)
- Risk Framework: [RISK_FRAMEWORK.md](./RISK_FRAMEWORK.md)
- Memory Schema: [MEMORY_SCHEMA.md](./MEMORY_SCHEMA.md)
- Multi-Market Expansion: [MARKETS.md](./MARKETS.md)