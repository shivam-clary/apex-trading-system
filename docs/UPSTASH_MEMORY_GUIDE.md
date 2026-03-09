# APEX Trading System — Upstash Redis Memory Guide

**Single source of truth for all APEX agent memory reads and writes.**
This document replaces `docs/MEMORY_SCHEMA.md`.

---

## Architecture

All APEX agents read and write shared state exclusively via **Upstash Redis REST API**.
- No `manage_memories` calls. That tool fails in Nebula trigger execution contexts.
- No redis-py library. Pure HTTPS REST works in every agent context.
- Two databases: DB1 (live runtime state) and DB2 (intelligence/analytics).

```
Global Macro Scanner  ──▶  DB2: GLOBAL_SENTIMENT, WEEKEND_MACRO_SNAPSHOT
Regime Engine         ──▶  DB1: MARKET_REGIME
Sentiment Engine      ──▶  DB1: SENTIMENT_SNAPSHOT
Option Chain Monitor  ──▶  DB1: OPTION_CHAIN_SNAPSHOT
Validator Gate        ──▶  DB1: VALIDATION_RESULT, SIGNAL_BLOCKED
Options Strategy      ──▶  DB1: TRADE_SIGNALS
Risk Veto Authority   ──▶  DB1: VETO_RESULT, APPROVED_SIGNALS
Paper Trade Engine    ──▶  DB1: PAPER_LEDGER, EXECUTION_RECORD
Performance Monitor   ──▶  DB2: PERFORMANCE_SNAPSHOT
Evolution Engine      ──▶  DB2: STRATEGY_WEIGHTS, EVOLUTION_LOG
Health Monitor        ──▶  DB1: HEALTH_STATUS, HEALTH_CHECK_LOG
Error Monitor         ──▶  DB1: ERROR_LOG, APEX_ERROR_MONITOR_LOG
```

---

## REST API Pattern

### Read a key
```
GET https://{UPSTASH_HOST}/get/{KEY}
Authorization: Bearer {TOKEN}

Response: {"result": "your-pipe-delimited-string-value"}
```

### Write a key (with TTL)
```
POST https://{UPSTASH_HOST}/pipeline
Authorization: Bearer {TOKEN}
Content-Type: application/json

Body: [["SET", "KEY_NAME", "pipe-delimited-value", "EX", 1200]]

Response: [{"result": "OK"}]
```

### Python snippet (copy into any agent)
```python
import os, json
from urllib.request import urlopen, Request

DB1_URL   = os.environ["UPSTASH_REDIS_REST_URL"]
DB1_TOKEN = os.environ["UPSTASH_REDIS_REST_TOKEN"]
DB2_URL   = os.environ.get("UPSTASH_REDIS_REST_URL_DB2", DB1_URL)
DB2_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN_DB2", DB1_TOKEN)

def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def redis_get(base_url, token, key):
    url = f"{base_url.rstrip('/')}/get/{key}"
    req = Request(url, headers=_headers(token))
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read())["result"]

def redis_set(base_url, token, key, value, ttl=None):
    assert isinstance(value, str), "value MUST be a plain string"
    url = f"{base_url.rstrip('/')}/pipeline"
    cmd = ["SET", key, value] + (["EX", str(ttl)] if ttl else [])
    req = Request(url, data=json.dumps([cmd]).encode(), headers=_headers(token), method="POST")
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read())[0]["result"] == "OK"

# DB1 reads/writes
def read_state(key):   return redis_get(DB1_URL, DB1_TOKEN, key)
def write_state(key, value, ttl=None): return redis_set(DB1_URL, DB1_TOKEN, key, value, ttl)

# DB2 reads/writes
def read_intel(key):   return redis_get(DB2_URL, DB2_TOKEN, key)
def write_intel(key, value, ttl=None): return redis_set(DB2_URL, DB2_TOKEN, key, value, ttl)
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `UPSTASH_REDIS_REST_URL` | DB1 REST endpoint (e.g. `https://xxx.upstash.io`) |
| `UPSTASH_REDIS_REST_TOKEN` | DB1 bearer token |
| `UPSTASH_REDIS_REST_URL_DB2` | DB2 REST endpoint (optional, falls back to DB1) |
| `UPSTASH_REDIS_REST_TOKEN_DB2` | DB2 bearer token (optional, falls back to DB1) |

---

## DB1 — Live State Keys

All values are **pipe-delimited plain strings**. Short TTLs.

| Key | Writer | Readers | TTL (s) | Value Schema |
|---|---|---|---|---|
| `MARKET_REGIME` | India Market Regime Engine | All | 1200 | `regime:<val>\|confidence:<0-100>\|vix:<val>\|pcr:<val>\|timestamp:<ISO>` |
| `TRADE_SIGNALS` | Options Strategy Engine | Validator, Veto, Paper | 900 | `generated_at:<ISO>\|signal_count:<n>\|signals:<id>:<type>:<entry>:<sl>:<tp>:<strategy>:<conf>;<...>` |
| `APPROVED_SIGNALS` | Risk Veto Authority | Paper Trade Engine | 900 | Same format as TRADE_SIGNALS, only approved entries |
| `PAPER_LEDGER` | Dhan Paper Trade Engine | Evolution, Performance | 3600 | `capital:<val>\|realized_pnl:<val>\|unrealized_pnl:<val>\|open_positions:<id>:<mtm>;<...>\|closed_trades:<id>:<pnl>;<...>` |
| `OPTION_CHAIN_SNAPSHOT` | NSE Option Chain Monitor | Validator, Strategy | 360 | `timestamp:<ISO>\|nifty_pcr:<val>\|banknifty_pcr:<val>\|max_pain_nifty:<val>\|iv_rank:<val>\|gamma_exp:<val>` |
| `SENTIMENT_SNAPSHOT` | Sentiment Intelligence Engine | Validator, Regime | 360 | `timestamp:<ISO>\|score:<-1 to 1>\|label:<val>\|conviction:<HIGH/MED/LOW>\|top_themes:<a,b,c>` |
| `VALIDATION_RESULT` | Apex Validator Gate | Central Command, Veto | 1200 | `timestamp:<ISO>\|overall:<PASS/WARN/FAIL>\|regime:<PASS/FAIL>\|sentiment:<PASS/FAIL>\|option_chain:<PASS/FAIL>\|signals:<PASS/FAIL>` |
| `VALIDATION_LOG` | Apex Validator Gate | Health Monitor | 3600 | Append-only log entries, pipe-separated |
| `SIGNAL_BLOCKED` | Apex Validator Gate | All execution agents | 1200 | `true` or `false` |
| `VETO_RESULT` | Risk Veto Authority | Paper Trade Engine | 1200 | `timestamp:<ISO>\|vetoed:<n>\|approved:<n>\|entries:<id>:<verdict>:<reason>;<...>` |
| `EXECUTION_RECORD` | Dhan Paper Trade Engine | Performance, Evolution | 3600 | `timestamp:<ISO>\|trades_opened:<n>\|trades_closed:<n>\|fills:<id>:<pair>:<price>:<qty>;<...>` |
| `HEALTH_STATUS` | Apex System Health Monitor | Error Monitor | 3600 | `timestamp:<ISO>\|status:<OK/DEGRADED/CRITICAL>\|failed_agents:<list or NONE>\|late_agents:<list or NONE>` |
| `HEALTH_CHECK_LOG` | Apex System Health Monitor | Error Monitor | 86400 | Append-only log |
| `ERROR_LOG` | All agents (on error) | Error Monitor, Tony | 86400 | `timestamp:<ISO>\|error_id:<ERR_XXX>\|agent:<slug>\|type:<class>\|message:<text>\|recurrence:<n>` |
| `APEX_ERROR_MONITOR_LOG` | Apex Error Monitor | Nebula orchestrator | 86400 | Structured error monitor run log |
| `FOREX_MARKET_REGIME` | Apex Forex Macro Regime Engine | INR Signal Engine, Veto | 1200 | `regime:<val>\|confidence:<0-100>\|dxy:<val>\|dxy_change_pct:<val>\|us10y:<val>\|crude_brent:<val>\|timestamp:<ISO>` |
| `FOREX_BLACKOUT` | Apex Forex Macro Regime Engine | All Forex agents | 1200 | `blackout:<true/false>\|reason:<text or NONE>` |
| `FOREX_SIGNALS` | INR Currency Signal Engine | Forex Veto, Paper | 900 | `generated_at:<ISO>\|signals:<id>:<pair>:<dir>:<entry>:<sl>:<tp>:<strategy>:<conf>;<...>` |
| `APPROVED_FOREX_SIGNALS` | Forex Risk Veto Authority | Dhan Forex Paper Engine | 900 | Same format as FOREX_SIGNALS |
| `FOREX_PAPER_LEDGER` | Dhan Forex Paper Engine | Forex Perf, Evolution | 3600 | `capital:<val>\|realized_pnl:<val>\|open_positions:<pair>:<dir>:<entry>:<qty>:<mtm>;<...>` |
| `FOREX_VETO_REPORT` | Forex Risk Veto Authority | Forex Evolution | 3600 | `timestamp:<ISO>\|vetoed:<n>\|approved:<n>\|entries:<id>:<reason>;<...>` |
| `CRYPTO_MARKET_REGIME` | Apex Crypto Market Regime | Crypto Signal | 900 | `regime:<val>\|confidence:<0-100>\|btc_dom:<val>\|fear_greed:<val>\|timestamp:<ISO>` |
| `CRYPTO_TRADE_SIGNALS` | Apex Crypto Signal Aggregator | Crypto Veto | 900 | `generated_at:<ISO>\|signals:<id>:<symbol>:<dir>:<entry>:<sl>:<tp>:<strategy>:<conf>;<...>` |
| `APPROVED_CRYPTO_TRADE_SIGNALS` | Apex Crypto Risk Veto | Crypto Paper Engine | 900 | Same format as CRYPTO_TRADE_SIGNALS |
| `CRYPTO_PAPER_LEDGER` | Apex Crypto Paper Engine | Crypto Evolution | 3600 | `capital:<val>\|realized_pnl:<val>\|open_positions:<symbol>:<dir>:<entry>:<mtm>;<...>` |
| `CRYPTO_VETO_REPORT` | Apex Crypto Risk Veto | Crypto Evolution | 3600 | `timestamp:<ISO>\|vetoed:<n>\|approved:<n>\|entries:<id>:<reason>;<...>` |

---

## DB2 — Intelligence Keys

Longer TTLs. Written by macro/analytics agents, read by regime and strategy agents.

| Key | Writer | Readers | TTL (s) | Value Schema |
|---|---|---|---|---|
| `GLOBAL_SENTIMENT` | Global Macro Intelligence Scanner | All equity agents | 14400 | `score:<-1 to 1>\|label:<val>\|directional_bias:<LONG/SHORT/NEUTRAL>\|conviction:<HIGH/MED/LOW>\|generated_at:<ISO>\|fed_signal:<val>\|geopolitical_signal:<val>\|commodity_signal:<val>\|confidence_pct:<0-100>` |
| `GLOBAL_SENTIMENT_ASIA` | Global Macro Intelligence Scanner | Morning pipeline | 28800 | Same schema as GLOBAL_SENTIMENT |
| `GLOBAL_SENTIMENT_USOPEN` | Global Macro Intelligence Scanner | Next-day pipeline | 43200 | Same schema as GLOBAL_SENTIMENT |
| `GLOBAL_SENTIMENT_COMPOSITE` | Global Macro Intelligence Scanner | All agents | 28800 | Same schema as GLOBAL_SENTIMENT |
| `WEEKEND_MACRO_SNAPSHOT` | Weekend Sweep / Global Macro Scanner | Monday pre-market | 172800 | `timestamp:<ISO>\|sentiment_bias:<val>\|confidence:<0-100>\|fed_signal:<val>\|crude_bias:<val>\|dxy_bias:<val>\|sgx_nifty_signal:<val>\|monday_opening_bias:<val>\|key_events:<e1,e2,...>\|analyst_note:<text>` |
| `WEEKEND_SWEEP_LOG` | Weekend Sweep recipe | Health Monitor | 172800 | `timestamp:<ISO>\|run:WEEKEND_SWEEP\|status:COMPLETE\|events_found:<n>` |
| `MARKET_STATE` | India Market Regime Engine | Evolution, Performance | 86400 | `date:<YYYY-MM-DD>\|nifty_close:<val>\|banknifty_close:<val>\|india_vix:<val>\|advance_decline:<val>\|fii_net:<val>\|dii_net:<val>` |
| `PERFORMANCE_SNAPSHOT` | Live Trade Performance Monitor | Evolution Engine | 86400 | `date:<ISO>\|sharpe:<val>\|calmar:<val>\|sortino:<val>\|win_rate:<val>\|profit_factor:<val>\|max_drawdown:<val>\|daily_pnl:<val>\|total_trades:<n>\|decay_flags:<list or NONE>` |
| `STRATEGY_WEIGHTS` | APEX Self-Evolution Engine | Options Strategy Engine | 604800 | `strategy_id:<multiplier>\|strategy_id:<multiplier>...` (multipliers 0.5–1.5) |
| `EVOLUTION_LOG` | APEX Self-Evolution Engine | Tony, Health Monitor | 604800 | `timestamp:<ISO>\|strategies_updated:<n>\|paused:<list or NONE>\|weight_changes:<strategy>:<old>-><new>;<...>` |
| `WALK_FORWARD_RESULTS` | NSE Strategy Validation Engine | Evolution, Health | 604800 | `timestamp:<ISO>\|strategies_tested:<n>\|passed:<n>\|failed:<n>\|results:<strategy>:<sharpe>:<drawdown>:<grade>;<...>` |
| `FOREX_PERFORMANCE_SNAPSHOT` | Forex Performance Monitor | Forex Evolution | 86400 | Same schema as PERFORMANCE_SNAPSHOT |
| `FOREX_STRATEGY_WEIGHTS` | Forex Self-Evolution Engine | INR Signal Engine | 604800 | `strategy_id:<multiplier>\|...` |
| `FOREX_EVOLUTION_LOG` | Forex Self-Evolution Engine | Tony, Health Monitor | 604800 | Same schema as EVOLUTION_LOG |
| `CRYPTO_PERFORMANCE_SNAPSHOT` | Apex Crypto Paper Engine | Crypto Evolution | 86400 | Same schema as PERFORMANCE_SNAPSHOT |
| `CRYPTO_STRATEGY_WEIGHTS` | Apex Crypto Self-Evolution | Crypto Signal Aggregator | 604800 | `strategy_id:<multiplier>\|...` |
| `CRYPTO_EVOLUTION_LOG` | Apex Crypto Self-Evolution | Tony, Health Monitor | 604800 | Same schema as EVOLUTION_LOG |

---

## Value Format Rules

1. **Always plain strings** — never JSON objects, never dicts, never lists
2. **Pipe-delimited** — fields separated by `|`
3. **Colon-separated** — key:value within each field
4. **Timestamps in ISO 8601 IST** — e.g. `2026-03-10T09:15:00+05:30`
5. **Lists within a field** — comma-separated e.g. `key_events:event1,event2,event3`
6. **Sub-lists (e.g. signals)** — semicolon-separated entries within the list field
7. **No newlines** — entire value is one line

### Example: MARKET_REGIME
```
regime:TRENDING_UP|confidence:82|vix:14.2|pcr:1.12|fii_net_cr:450|timestamp:2026-03-10T09:30:00+05:30
```

### Example: TRADE_SIGNALS
```
generated_at:2026-03-10T09:45:00+05:30|signal_count:2|signals:SIG001:BANKNIFTY_CE:LONG:57200:56800:57800:BREAKOUT:78:2;SIG002:NIFTY_PE:SHORT:24200:24400:23900:MOMENTUM:65:1
```

### Example: WEEKEND_MACRO_SNAPSHOT
```
timestamp:2026-03-09T18:00:00+05:30|sentiment_bias:BEARISH|confidence:88|fed_signal:NEUTRAL|crude_bias:UP|dxy_bias:UP|sgx_nifty_signal:DISCOUNT|monday_opening_bias:GAP_DOWN|key_events:Iran war day 9,Brent $92,NFP miss,FPI sell Rs21000cr|analyst_note:Maximum geopolitical risk. Gap-down base case. Reduce size to 0.25x.
```

---

## Agent Instructions

Every APEX agent that reads or writes memory MUST include this snippet in its prompt/code:

```
MEMORY PROTOCOL (MANDATORY):
- Read state:  GET https://{UPSTASH_REDIS_REST_URL}/get/{KEY}  | Authorization: Bearer {UPSTASH_REDIS_REST_TOKEN}
- Write state: POST https://{UPSTASH_REDIS_REST_URL}/pipeline  | Body: [["SET","KEY","pipe-string","EX",TTL]]
- Read intel:  GET https://{UPSTASH_REDIS_REST_URL_DB2}/get/{KEY}  | Authorization: Bearer {UPSTASH_REDIS_REST_TOKEN_DB2}
- Write intel: POST https://{UPSTASH_REDIS_REST_URL_DB2}/pipeline  | Body: [["SET","KEY","pipe-string","EX",TTL]]
- NEVER call manage_memories — it fails in trigger execution contexts
- Values MUST be plain pipe-delimited strings — never JSON objects
- Always validate freshness: check timestamp field against TTL before consuming
```

---

## Migration Notes

- **Replaced:** `manage_memories(action='save', app='APEX_TRADING', ...)` — deprecated, non-functional in trigger contexts
- **Replaced:** `MEMORY_SCHEMA.md` — this document supersedes it
- **Migration date:** 2026-03-09
- **Trigger context bug:** Nebula `manage_memories` tool fails with "Input should be an object" JSON serialization error when called from scheduled trigger pipelines. Upstash REST calls are unaffected.
