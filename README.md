# APEX Trading Intelligence System
### Autonomous Multi-Agent AI Trading System — Indian Markets (NSE/BSE F&O)

---

## Overview

APEX is an institutional-grade autonomous trading intelligence system built on a 16-agent AI network.
It trades Indian markets (NSE/BSE — equities, F&O, indices) using multi-agent consensus, hard risk enforcement,
and a fully Dhan API v2 native execution stack.

The system is designed for zero-human-intervention intraday and options trading, with a paper trading mode
for strategy validation before going live.

---

## Architecture

```
DhanDataFeed (WebSocket)
    |
    v
SignalBus (Redis pub/sub)
    |
    +-----> 16 Specialist Agents (run concurrently)
    |
    v
MasterDecisionMaker (consensus + conflict resolution)
    |
    v
RiskManager + VolatilityKillSwitch (hard veto)
    |
    v
SmartOrderRouter
    |
    v
DhanExecutor --> Dhan API v2
```

---

## Agent Network (16 Agents)

| Agent | Role |
|-------|------|
| IndianMarketDataAgent | NSE/BSE live prices and market data |
| GlobalMarketDataAgent | US markets, global indices |
| CommoditiesAgent | MCX commodities (crude, gold, silver) |
| TechnicalAnalysisAgent | TA indicators (RSI, MACD, Bollinger, etc.) |
| AlgoStrategyAgent | Algorithmic signal generation |
| OptionsDerivativesAgent | F&O analysis, Greeks, IV |
| MarketRegimeAgent | Trending/ranging/volatile regime detection |
| SGXPreMarketAgent | SGX Nifty pre-market gap analysis |
| FundamentalAnalysisAgent | Earnings, valuations, sector rotation |
| FIIDIIFlowAgent | FII/DII institutional flow tracking |
| RBIIndianMacroAgent | RBI policy, India macro indicators |
| GlobalMacroAgent | Fed, DXY, yields, global macro signals |
| IndianNewsEventsAgent | NSE/BSE announcements, India news |
| GlobalNewsAgent | Reuters, Bloomberg, global event scanning |
| SentimentPositioningAgent | Options PCR, market sentiment, positioning |
| ZeroDTEExpiryAgent | 0-DTE expiry strategy execution |

---

## Infrastructure Stack

| Component | Technology |
|-----------|-----------|
| Market Data Feed | Dhan API v2 WebSocket (`dhanhq.marketfeed`) |
| Order Execution | Dhan API v2 REST (`dhanhq.dhanhq`) |
| State / Pub-Sub | Redis |
| Event Streaming | Kafka |
| Control Plane API | FastAPI (port 8000) |
| Language | Python 3.10+ |

---

## Repository Structure

```
trading_system/
  agents/                    # 16 specialist trading agents
    algo_strategy.py
    commodities.py
    fii_dii_flow.py
    fundamental_analysis.py
    global_macro.py
    global_market_data.py
    global_news.py
    indian_market_data.py
    indian_news_events.py
    market_regime.py
    options_derivatives.py
    rbi_macro.py
    sentiment_positioning.py
    sgx_pre_market.py
    technical_analysis.py
    zero_dte_expiry.py
  core/
    config.py                # APEXConfig dataclass -- env-var driven
  data/
    redis_client.py          # Redis async client
    kafka_setup.py           # Kafka producer/consumer
    dhan_feed.py             # Dhan WebSocket market data feed
  signals/
    signal_bus.py            # Redis-backed async pub/sub
    conflict_detector.py     # Agent signal conflict resolution
    master_decision_maker.py # Consensus engine
    learning_engine.py       # Strategy performance feedback loop
  risk/
    risk_manager.py          # Position and daily loss limits
    volatility_kill_switch.py# Hard veto on extreme volatility
    portfolio_manager.py     # Portfolio-level position tracking
  execution/
    order_manager.py         # Order lifecycle management (OMS)
    dhan_executor.py         # Dhan API v2 order execution engine
    smart_router.py          # Smart order routing (limit/market)
  api/
    server.py                # FastAPI control plane
  main.py                    # APEXOrchestrator entrypoint
docs/
infrastructure/
tasks/
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install dhanhq redis kafka-python fastapi uvicorn
```

### 2. Set environment variables

```bash
# Dhan API (required)
export DHAN_CLIENT_ID="your_client_id"
export DHAN_ACCESS_TOKEN="your_access_token"

# Redis (defaults to localhost:6379)
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"

# Kafka (defaults to localhost:9092)
export KAFKA_BOOTSTRAP_SERVERS="localhost:9092"

# Risk limits
export MAX_DAILY_LOSS="50000"          # INR -- hard daily loss circuit breaker
export MAX_OPEN_POSITIONS="5"
export MAX_POSITION_SIZE="100000"      # INR per position
export VOLATILITY_THRESHOLD="2.0"

# Trading mode: paper (default) or live
export TRADING_MODE="paper"
export DEFAULT_EXCHANGE="NSE_FNO"

# LLM APIs (for agent intelligence)
export OPENAI_API_KEY="your_key"
export ANTHROPIC_API_KEY="your_key"
export GEMINI_API_KEY="your_key"

# News
export NEWS_API_KEY="your_key"
```

### 3. Run the system

```bash
uvicorn trading_system.main:app --host 0.0.0.0 --port 8000 --reload
```

Or directly:

```bash
python -m trading_system.main
```

---

## Risk Management

APEX enforces hard risk limits that cannot be overridden by any agent:

| Parameter | Default | Env Var |
|-----------|---------|--------|
| Max Daily Loss | INR 50,000 | `MAX_DAILY_LOSS` |
| Max Open Positions | 5 | `MAX_OPEN_POSITIONS` |
| Max Position Size | INR 1,00,000 | `MAX_POSITION_SIZE` |
| Volatility Kill Switch | 2.0x threshold | `VOLATILITY_THRESHOLD` |

The `VolatilityKillSwitch` and `RiskManager` both have veto authority over the `MasterDecisionMaker`.
No order reaches `DhanExecutor` without passing both checks.

---

## Trading Modes

| Mode | Behavior |
|------|----------|
| `paper` (default) | Simulates order fills using live prices. No real orders sent. |
| `live` | Places real orders via Dhan API v2. Use only after paper validation. |

Switch via: `export TRADING_MODE=live`

---

## Execution Engine

**Broker:** DhanHQ -- Dhan API v2 only. No Zerodha/Kite/Upstox dependencies.

**DhanExecutor** supports:
- `place_order` -- market, limit, SL, SL-M order types
- `modify_order` -- update price/quantity on open orders
- `cancel_order` -- cancel by order ID
- `get_positions` -- current intraday positions
- `get_holdings` -- delivery holdings
- `get_funds` -- available margin

**DhanDataFeed** supports:
- WebSocket streaming (Ticker / Quote / Full depth modes)
- `subscribe(security_id, exchange_segment, mode)` -- single instrument
- `subscribe_many(instruments, mode)` -- batch subscribe
- `on_tick(callback)` -- register tick handlers
- Auto-reconnect with subscription restoration

**Exchange segments:** `NSE_EQ`, `NSE_FNO`, `BSE_EQ`, `BSE_FNO`, `MCX_COMM`

---

## Configuration

All configuration is driven by environment variables via `APEXConfig` (dataclass in `core/config.py`).
No hardcoded secrets. Import pattern:

```python
from trading_system.core.config import Config
config = Config()
print(config.DHAN_CLIENT_ID)
```

---

## Nebula AI Integration

APEX is orchestrated by the Nebula AI agent network, which runs:
- **Morning pre-market briefing** (09:00 IST) -- regime scan, global macro, sentiment
- **15-minute intraday loops** -- regime refresh, signal generation, paper trade execution
- **Post-session learning** -- reviews trades, updates strategy weights, files GitHub issues for detected bugs

The Nebula agent ecosystem (India Trading Central Command + 8 specialist agents) operates independently
of this codebase but uses Dhan API credentials and Redis state shared with the trading system.

---

## Development Status

| Component | Status |
|-----------|--------|
| Dhan API v2 integration | Complete |
| 16-agent network | Complete |
| Paper trading engine | Active |
| Live trading | Ready (disabled by default) |
| Risk enforcement | Complete |
| FastAPI control plane | Complete |
| Kafka event streaming | Integrated |
| Redis state management | Integrated |

---

## License

Private repository. All rights reserved.
