"""
apex_redis.py — Universal Upstash REST Client for APEX Trading System

All APEX agents read/write shared state exclusively through this module.
Uses pure HTTPS REST API — no redis-py dependency, works in any agent context
including Nebula trigger execution contexts where tool serialization fails.

Two databases:
  DB1 (Live State)      — UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN
                          Short-TTL runtime keys: MARKET_REGIME, SIGNALS, LEDGER, etc.
  DB2 (Intelligence)    — UPSTASH_REDIS_REST_URL_DB2 / UPSTASH_REDIS_REST_TOKEN_DB2
                          Longer-TTL keys: GLOBAL_SENTIMENT, MACRO_SNAPSHOT, etc.

Environment variables required (set in .env / Dhan agent secrets):
  UPSTASH_REDIS_REST_URL         — DB1 REST endpoint
  UPSTASH_REDIS_REST_TOKEN       — DB1 bearer token
  UPSTASH_REDIS_REST_URL_DB2     — DB2 REST endpoint (falls back to DB1 if unset)
  UPSTASH_REDIS_REST_TOKEN_DB2   — DB2 bearer token (falls back to DB1 if unset)

Quick usage:
  from trading_system.core.apex_redis import read_state, write_state
  from trading_system.core.apex_redis import read_intelligence, write_intelligence

  regime = read_state("MARKET_REGIME")
  write_state("MARKET_REGIME", "regime:TRENDING_UP|confidence:82|...", ttl=1200)

  sentiment = read_intelligence("GLOBAL_SENTIMENT")
  write_intelligence("WEEKEND_MACRO_SNAPSHOT", "sentiment_bias:BEARISH|...", ttl=86400)
"""

import os
import time
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DB1_URL   = os.environ.get("UPSTASH_REDIS_REST_URL", "")
_DB1_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
_DB2_URL   = os.environ.get("UPSTASH_REDIS_REST_URL_DB2", _DB1_URL)
_DB2_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN_DB2", _DB1_TOKEN)

_MAX_RETRIES   = 3
_RETRY_DELAY_S = 1.5
_TIMEOUT_S     = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

def _safe_key(key):
    return quote(key, safe="")

def _http_get(url, token):
    req = Request(url, headers=_headers(token), method="GET")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=_TIMEOUT_S) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("result")
        except HTTPError as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] GET failed after {_MAX_RETRIES} attempts: HTTP {e.code} — {url}")
                return None
        except (URLError, OSError) as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] GET failed after {_MAX_RETRIES} attempts: {e} — {url}")
                return None
        time.sleep(_RETRY_DELAY_S)
    return None

def _http_set(base_url, token, key, value, ttl=None):
    if not isinstance(value, str):
        print(f"[apex_redis] WRITE REJECTED — value must be plain string, got {type(value).__name__} for key={key}")
        return False
    # Use Upstash pipeline endpoint: POST /pipeline with [["SET", key, value, "EX", ttl]]
    url = f"{base_url.rstrip('/')}/pipeline"
    cmd = ["SET", key, value]
    if ttl is not None:
        cmd += ["EX", str(int(ttl))]
    payload = json.dumps([cmd]).encode("utf-8")
    req = Request(url, data=payload, headers=_headers(token), method="POST")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with urlopen(req, timeout=_TIMEOUT_S) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                # Pipeline returns a list; first element should be {"result": "OK"}
                if isinstance(body, list) and body:
                    return body[0].get("result") == "OK"
                return False
        except HTTPError as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] SET failed after {_MAX_RETRIES} attempts: HTTP {e.code} key={key}")
                return False
        except (URLError, OSError) as e:
            if attempt == _MAX_RETRIES:
                print(f"[apex_redis] SET failed after {_MAX_RETRIES} attempts: {e} key={key}")
                return False
        time.sleep(_RETRY_DELAY_S)
    return False


# ---------------------------------------------------------------------------
# DB1 — Live State (short TTL runtime keys)
# ---------------------------------------------------------------------------

def read_state(key):
    """Read a live state key from DB1. Returns string or None."""
    if not _DB1_URL or not _DB1_TOKEN:
        print("[apex_redis] DB1 not configured")
        return None
    url = f"{_DB1_URL.rstrip('/')}/get/{_safe_key(key)}"
    return _http_get(url, _DB1_TOKEN)

def write_state(key, value, ttl=None):
    """
    Write a live state key to DB1.
    value MUST be a plain pipe-delimited string.
    Recommended TTLs (seconds):
      MARKET_REGIME=1200, TRADE_SIGNALS=900, PAPER_LEDGER=3600,
      OPTION_CHAIN_SNAPSHOT=360, SENTIMENT_SNAPSHOT=360,
      VALIDATION_RESULT=1200, VETO_RESULT=1200, EXECUTION_RECORD=3600,
      APPROVED_SIGNALS=900, SIGNAL_BLOCKED=1200,
      HEALTH_STATUS=3600, ERROR_LOG=86400
    Returns True on success.
    """
    if not _DB1_URL or not _DB1_TOKEN:
        print("[apex_redis] DB1 not configured")
        return False
    return _http_set(_DB1_URL, _DB1_TOKEN, key, value, ttl)

def delete_state(key):
    """Delete a key from DB1."""
    if not _DB1_URL or not _DB1_TOKEN:
        return False
    url = f"{_DB1_URL.rstrip('/')}/del/{_safe_key(key)}"
    req = Request(url, headers=_headers(_DB1_TOKEN), method="GET")
    try:
        with urlopen(req, timeout=_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return int(body.get("result", 0)) > 0
    except Exception as e:
        print(f"[apex_redis] delete_state failed: {e}")
        return False

def get_all_state_keys():
    """List all DB1 keys. For debugging only — never call in hot paths."""
    if not _DB1_URL or not _DB1_TOKEN:
        return []
    url = f"{_DB1_URL.rstrip('/')}/keys/*"
    result = _http_get(url, _DB1_TOKEN)
    return result if isinstance(result, list) else []


# ---------------------------------------------------------------------------
# DB2 — Intelligence (longer TTL macro/sentiment keys)
# ---------------------------------------------------------------------------

def read_intelligence(key):
    """Read an intelligence key from DB2. Returns string or None."""
    if not _DB2_URL or not _DB2_TOKEN:
        print("[apex_redis] DB2 not configured")
        return None
    url = f"{_DB2_URL.rstrip('/')}/get/{_safe_key(key)}"
    return _http_get(url, _DB2_TOKEN)

def write_intelligence(key, value, ttl=None):
    """
    Write an intelligence key to DB2.
    value MUST be a plain pipe-delimited string.
    Recommended TTLs (seconds):
      GLOBAL_SENTIMENT=14400, GLOBAL_SENTIMENT_ASIA=28800,
      GLOBAL_SENTIMENT_USOPEN=43200, WEEKEND_MACRO_SNAPSHOT=172800,
      PERFORMANCE_SNAPSHOT=86400, STRATEGY_WEIGHTS=604800,
      EVOLUTION_LOG=604800, WALK_FORWARD_RESULTS=604800
    Returns True on success.
    """
    if not _DB2_URL or not _DB2_TOKEN:
        print("[apex_redis] DB2 not configured")
        return False
    return _http_set(_DB2_URL, _DB2_TOKEN, key, value, ttl)

def get_all_intelligence_keys():
    """List all DB2 keys. For debugging only."""
    if not _DB2_URL or not _DB2_TOKEN:
        return []
    url = f"{_DB2_URL.rstrip('/')}/keys/*"
    result = _http_get(url, _DB2_TOKEN)
    return result if isinstance(result, list) else []


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def parse_pipe_string(value):
    """
    Parse pipe-delimited 'key:value|key:value' string into a dict.
    Example: parse_pipe_string("regime:TRENDING_UP|confidence:82") -> {"regime":"TRENDING_UP","confidence":"82"}
    """
    if not value:
        return {}
    result = {}
    for part in str(value).split("|"):
        if ":" in part:
            k, _, v = part.partition(":")
            result[k.strip()] = v.strip()
    return result

def build_pipe_string(**kwargs):
    """
    Build pipe-delimited string from kwargs.
    Example: build_pipe_string(regime="TRENDING_UP", confidence=82) -> "regime:TRENDING_UP|confidence:82"
    """
    return "|".join(f"{k}:{v}" for k, v in kwargs.items())

def check_freshness(value, max_age_seconds, ts_field="timestamp"):
    """
    Check if a pipe-delimited value's timestamp is within max_age_seconds.
    Returns True if fresh, False if stale or unparseable.
    """
    from datetime import datetime, timezone
    parsed = parse_pipe_string(value)
    ts_raw = parsed.get(ts_field)
    if not ts_raw:
        return False
    try:
        ts_raw_clean = ts_raw.replace("+05:30", "+0530")
        try:
            ts = datetime.fromisoformat(ts_raw_clean)
        except ValueError:
            ts = datetime.strptime(ts_raw_clean[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age <= max_age_seconds
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Key Registries
# ---------------------------------------------------------------------------

DB1_KEYS = [
    # NSE Equity
    "MARKET_REGIME", "TRADE_SIGNALS", "APPROVED_SIGNALS", "PAPER_LEDGER",
    "OPTION_CHAIN_SNAPSHOT", "SENTIMENT_SNAPSHOT", "VALIDATION_RESULT",
    "VALIDATION_LOG", "VETO_RESULT", "EXECUTION_RECORD", "SIGNAL_BLOCKED",
    "HEALTH_STATUS", "HEALTH_CHECK_LOG", "ERROR_LOG", "APEX_ERROR_MONITOR_LOG",
    # Forex
    "FOREX_MARKET_REGIME", "FOREX_BLACKOUT", "FOREX_SIGNALS",
    "APPROVED_FOREX_SIGNALS", "FOREX_PAPER_LEDGER", "FOREX_VETO_REPORT",
    # Crypto
    "CRYPTO_MARKET_REGIME", "CRYPTO_SENTIMENT_SNAPSHOT", "CRYPTO_TRADE_SIGNALS",
    "APPROVED_CRYPTO_TRADE_SIGNALS", "CRYPTO_PAPER_LEDGER", "CRYPTO_VETO_REPORT",
]

DB2_KEYS = [
    # Global Macro Intelligence
    "GLOBAL_SENTIMENT", "GLOBAL_SENTIMENT_ASIA", "GLOBAL_SENTIMENT_USOPEN",
    "GLOBAL_SENTIMENT_COMPOSITE", "WEEKEND_MACRO_SNAPSHOT", "WEEKEND_SWEEP_LOG",
    "MARKET_STATE",
    # NSE Performance
    "PERFORMANCE_SNAPSHOT", "STRATEGY_WEIGHTS", "EVOLUTION_LOG", "WALK_FORWARD_RESULTS",
    # Forex Intelligence
    "FOREX_PERFORMANCE_SNAPSHOT", "FOREX_STRATEGY_WEIGHTS", "FOREX_EVOLUTION_LOG",
    # Crypto Intelligence
    "CRYPTO_PERFORMANCE_SNAPSHOT", "CRYPTO_STRATEGY_WEIGHTS", "CRYPTO_EVOLUTION_LOG",
]


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("APEX Redis — self-test")
    print(f"DB1 configured: {'YES' if _DB1_URL else 'NO'}")
    print(f"DB2 configured: {'YES' if _DB2_URL else 'NO'}")

    test_key = "APEX_REDIS_SELFTEST"
    test_val = build_pipe_string(test="OK", ts="2026-01-01T00:00:00Z")

    print(f"Writing to DB1: {test_val}")
    ok = write_state(test_key, test_val, ttl=60)
    print(f"Write: {'OK' if ok else 'FAILED'}")

    read_back = read_state(test_key)
    print(f"Read back: {read_back}")
    print(f"Round-trip: {'PASS' if read_back == test_val else 'FAIL'}")
    delete_state(test_key)
    print("Done.")
