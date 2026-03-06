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

1. Log in to Dhan at [https://dhan.co](https://dhan.co)
2. Go to **My Profile > API Access**
3. Generate Access Token
4. Copy your **Client ID** and **Access Token**
5. Add to `.env`:

```
DHAN_CLIENT_ID=your_client_id_here
DHAN_ACCESS_TOKEN=your_access_token_here
```

**Important:** Dhan access tokens expire every 24 hours — regenerate daily or use Dhan's token refresh flow. APEX reads `DHAN_ACCESS_TOKEN` from agent memory at execution time. Update this variable daily in Nebula Secrets.

### Indian API Setup

1. Register at [indianapi.in](https://indianapi.in)
2. Generate an API key
3. Add to Nebula secrets: `INDIAN_API_KEY`

---

## 4. Agent Configuration

All agents use a shared configuration structure. Set the following in Nebula Secrets:

```
# Core
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token

# Data APIs
INDIAN_API_KEY=your_indian_api_key

# Risk Limits
MAX_DAILY_LOSS_PCT=5.0
MAX_POSITION_SIZE_PCT=10.0
VIX_KILL_SWITCH_THRESHOLD=25.0

# Capital
TOTAL_CAPITAL_INR=1000000

# Mode
PAPER_TRADE_MODE=true
ENABLE_LIVE_TRADING=false
```

---

## 5. Memory Namespace Initialization

Before the first run, initialize the `APEX_TRADING` memory namespace:

```python
from nebula_sdk import memory

memory.set("APEX_TRADING", "KILL_SWITCH", "FALSE")
memory.set("APEX_TRADING", "PAPER_LEDGER", "{}")
memory.set("APEX_TRADING", "DAILY_PNL", "0.0")
```

Or, in the Nebula chat:

```
Initialize APEX_TRADING memory namespace with KILL_SWITCH=FALSE, PAPER_LEDGER={}, DAILY_PNL=0.0
```

---

## 6. Trigger Activation

Activate triggers in this order:

1. **Trigger06** — EOD Reconciliation (test manually first)
2. **Trigger01** — Overnight macro scanner
3. **Trigger02** — Morning pre-session brief
4. **Trigger03** — Option chain refresh
5. **Trigger05** — Position monitor
   - Start 30 minutes after Trigger03
6. **Trigger04** **(last)** — Core trading loop
   - Only activate after all others are running

---

## 7. Paper Trading First Run

1. Verify `PAPER_TRADE_MODE=true` in secrets
2. Manually trigger Trigger02 at 08:00 IST and check output:
   - Should see `GLOBAL_SENTIMENT` and `MARKET_DATA` written to memory
3. At 09:15 IST, Trigger04 should produce first signals
4. Check `PAPER_LEDGER` in memory for positions
5. At 15:35 IST, Trigger06 produces EOD report via email

---

## 8. Going Live — Checklist

- [ ] Paper trading > 20 sessions with > 60% win rate
- [ ] Dhan API v2 Client ID and Access Token configured
- [ ] Risk limits reviewed and set
- [ ] Emergency kill switch tested
- [ ] Alerts (WhatsApp + email) configured
- [ ] Set `ENABLE_LIVE_TRADING=true` in Nebula secrets
- [ ] Set `PAPER_TRADE_MODE=false` in Nebula secrets

---

## 9. Environment Variables Reference

| Variable | Required | Default | Description |
|---------|----------|---------|-------------|
| DHAN_CLIENT_ID | Yes | - | Dhan account client ID |
| DHAN_ACCESS_TOKEN | Yes | - | Dhan API access token (regenerate daily) |
| INDIAN_API_KEY | Yes | - | IndianAPI key for NSE data |
| OPENAI_API_KEY | Yes | - | OpenAI GPT-4o for agent LLM |
| ANTHROPIC_API_KEY | No | - | Claude fallback LLM |
| MAX_DAILY_LOSS_PCT | No | 5.0 | Daily loss limit % |
| MAX_POSITION_SIZE_PCT | No | 10.0 | Max single position size % |
| VIX_KILL_SWITCH_THRESHOLD | No | 25.0 | VIX level to halt trading |
| TOTAL_CAPITAL_INR | No | 1000000 | Trading capital in INR |
| PAPER_TRADE_MODE | No | true | Enable paper trading mode |
| ENABLE_LIVE_TRADING | No | false | Enable live order execution |

---

## 10. Troubleshooting

### Common Issues

**Trigger04 produces no signals**
- Check that Trigger02 ran successfully and wrote to memory
- Verify `MARKET_STATE` is not stale (TTL: 20min)
- Ensure VIX_KILL_SWITCH_THRESHOLD is not triggered

**Orders not executing**
- Verify `DHAN_ACCESS_TOKEN` is fresh (regenerate daily)
- Check `KILL_SWITCH` is `FALSE` in memory
- Confirm `ENABLE_LIVE_TRADING` is `true` for live mode

**Memory read errors**
- Re-initialize the APEX_TRADING namespace
- Check Nebula memory quota

**Dhan API errors**
- Token expired: regenerate at dhan.co > My Profile > API Access
- Rate limit: Dhan API v2 allows 10 req/sec by default
