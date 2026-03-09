---
slug: apex-forex-intraday-signal-pipeline
title: APEX Forex — Intraday Signal Pipeline
steps:
- description: 'Run Forex Macro Regime Engine: scrape DXY, US10Y, crude oil, FII/FPI flows,
    classify INR regime as BULLISH_INR/BEARISH_INR/RANGING/RBI_INTERVENTION_RISK. Write
    FOREX_MARKET_REGIME and FOREX_BLACKOUT directly to Upstash Redis DB1.'
  agent_id: agt_069ad4f19cdc74b78000997db63737fe
  agent_slug: apex-forex-macro-regime-engine
  action_key: scrape-page
  action_props:
    url: https://www.nseindia.com/market-data/currency-derivatives
- description: 'Run INR Currency Signal Engine: read FOREX_MARKET_REGIME and FOREX_BLACKOUT
    from Upstash Redis DB1. Skip if blackout active. Fetch live NSE CDS futures prices.
    Run 4 strategy modules for USD/INR, EUR/INR, GBP/INR, JPY/INR. Write FOREX_SIGNALS
    directly to Upstash Redis DB1 (TTL 900s).'
  agent_id: agt_069ad501de0e71f180004e91a2e07313
  agent_slug: inr-currency-signal-engine
- description: 'Run Forex Risk Veto Authority: read FOREX_SIGNALS, FOREX_PAPER_LEDGER,
    FOREX_BLACKOUT from Upstash Redis DB1. Apply all 7 hard rules. Write APPROVED_FOREX_SIGNALS
    and FOREX_VETO_REPORT directly to Upstash Redis DB1.'
  agent_id: agt_069ad50e9d64797b80008d05eb78c78f
  agent_slug: forex-risk-veto-authority
- description: 'Run Dhan Forex Paper Engine: read APPROVED_FOREX_SIGNALS from Upstash
    Redis DB1. Fetch live NSE CDS prices. Simulate fills with realistic slippage. Mark-to-market
    open positions. Auto-close on SL/TP. Auto-square-off at 16:55 IST. Write FOREX_PAPER_LEDGER
    directly to Upstash Redis DB1 (TTL 3600s).'
  agent_id: agt_069ad50e94517ff48000d30ecbaa736e
  agent_slug: dhan-forex-paper-engine
---
