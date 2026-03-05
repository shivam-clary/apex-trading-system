-- APEX Trading Intelligence System - TimescaleDB Schema
-- Complete database schema with hypertables and continuous aggregates

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ===== TICK DATA =====
CREATE TABLE IF NOT EXISTS tick_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    oi BIGINT DEFAULT 0,
    source TEXT,
    CONSTRAINT tick_data_pkey PRIMARY KEY (time, symbol)
);

-- Convert to hypertable
SELECT create_hypertable('tick_data', 'time', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tick_symbol_time ON tick_data (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_tick_time ON tick_data (time DESC);

-- ===== CONTINUOUS AGGREGATES =====
-- 1 minute OHLCV
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    first(open, time) as open,
    max(high) as high,
    min(low) as low,
    last(close, time) as close,
    sum(volume) as volume,
    last(oi, time) as oi
FROM tick_data
GROUP BY bucket, symbol;

-- 5 minute OHLCV
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    symbol,
    first(open, time) as open,
    max(high) as high,
    min(low) as low,
    last(close, time) as close,
    sum(volume) as volume,
    last(oi, time) as oi
FROM tick_data
GROUP BY bucket, symbol;

-- 15 minute OHLCV
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', time) AS bucket,
    symbol,
    first(open, time) as open,
    max(high) as high,
    min(low) as low,
    last(close, time) as close,
    sum(volume) as volume,
    last(oi, time) as oi
FROM tick_data
GROUP BY bucket, symbol;

-- 1 hour OHLCV
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    first(open, time) as open,
    max(high) as high,
    min(low) as low,
    last(close, time) as close,
    sum(volume) as volume,
    last(oi, time) as oi
FROM tick_data
GROUP BY bucket, symbol;

-- Daily OHLCV
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol,
    first(open, time) as open,
    max(high) as high,
    min(low) as low,
    last(close, time) as close,
    sum(volume) as volume,
    last(oi, time) as oi
FROM tick_data
GROUP BY bucket, symbol;

-- ===== FII/DII FLOWS =====
CREATE TABLE IF NOT EXISTS fii_dii_flows (
    date DATE NOT NULL,
    category TEXT NOT NULL, -- FII, DII
    segment TEXT NOT NULL, -- cash, futures, options
    buy_value DOUBLE PRECISION,
    sell_value DOUBLE PRECISION,
    net_value DOUBLE PRECISION,
    CONSTRAINT fii_dii_pkey PRIMARY KEY (date, category, segment)
);

CREATE INDEX IF NOT EXISTS idx_fii_date ON fii_dii_flows (date DESC);

-- ===== OPTIONS OI DATA =====
CREATE TABLE IF NOT EXISTS options_oi (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    expiry DATE NOT NULL,
    strike DOUBLE PRECISION NOT NULL,
    option_type TEXT NOT NULL, -- CE, PE
    oi BIGINT,
    oi_change BIGINT,
    volume BIGINT,
    ltp DOUBLE PRECISION,
    iv DOUBLE PRECISION,
    CONSTRAINT options_oi_pkey PRIMARY KEY (time, symbol, expiry, strike, option_type)
);

SELECT create_hypertable('options_oi', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_options_symbol_expiry ON options_oi (symbol, expiry, time DESC);

-- ===== MACRO EVENTS =====
CREATE TABLE IF NOT EXISTS macro_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    impact_level TEXT, -- HIGH, MEDIUM, LOW
    asset_affected TEXT,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_macro_time ON macro_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_macro_impact ON macro_events (impact_level, timestamp DESC);

-- ===== AGENT SIGNALS =====
CREATE TABLE IF NOT EXISTS agent_signals (
    id UUID PRIMARY KEY,
    agent_name TEXT NOT NULL,
    agent_layer INTEGER NOT NULL,
    asset_symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    timeframe TEXT NOT NULL,
    reasoning TEXT,
    key_factors JSONB,
    entry_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    target_price DOUBLE PRECISION,
    position_size_pct DOUBLE PRECISION,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON agent_signals (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_asset ON agent_signals (asset_symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_agent ON agent_signals (agent_name, timestamp DESC);

-- ===== CONSENSUS DECISIONS =====
CREATE TABLE IF NOT EXISTS consensus_decisions (
    decision_id UUID PRIMARY KEY,
    asset_symbol TEXT NOT NULL,
    final_direction TEXT NOT NULL,
    weighted_confidence DOUBLE PRECISION NOT NULL,
    regime TEXT NOT NULL,
    master_reasoning TEXT,
    entry_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    target_1 DOUBLE PRECISION,
    target_2 DOUBLE PRECISION,
    risk_reward_ratio DOUBLE PRECISION,
    position_size_pct DOUBLE PRECISION,
    approved_by_risk BOOLEAN DEFAULT FALSE,
    execution_ready BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON consensus_decisions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_asset ON consensus_decisions (asset_symbol, timestamp DESC);

-- ===== TRADE OUTCOMES =====
CREATE TABLE IF NOT EXISTS trade_outcomes (
    trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID REFERENCES agent_signals(id),
    decision_id UUID REFERENCES consensus_decisions(decision_id),
    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION,
    pnl DOUBLE PRECISION,
    pnl_pct DOUBLE PRECISION,
    holding_period_minutes INTEGER,
    exit_reason TEXT,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trade_outcomes (entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_signal ON trade_outcomes (signal_id);

-- ===== AGENT PERFORMANCE =====
CREATE TABLE IF NOT EXISTS agent_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    signal_direction TEXT NOT NULL,
    was_correct BOOLEAN NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    asset_symbol TEXT NOT NULL,
    date DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_performance_agent_date ON agent_performance (agent_name, date DESC);
CREATE INDEX IF NOT EXISTS idx_performance_date ON agent_performance (date DESC);

-- ===== COMPRESSION POLICIES =====
-- Compress tick data older than 7 days
SELECT add_compression_policy('tick_data', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('options_oi', INTERVAL '7 days', if_not_exists => TRUE);

-- ===== RETENTION POLICIES =====
-- Keep raw tick data for 90 days
SELECT add_retention_policy('tick_data', INTERVAL '90 days', if_not_exists => TRUE);

-- ===== REFRESH POLICIES FOR CONTINUOUS AGGREGATES =====
SELECT add_continuous_aggregate_policy('ohlcv_1m',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_5m',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_15m',
    start_offset => INTERVAL '6 hours',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_1h',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('ohlcv_daily',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE);
