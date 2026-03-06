---
slug: apex-overnight-us-market-open-scan-2130-ist
title: APEX — Overnight US Market Open Scan (21:30 IST)
steps:
- description: Scan global markets at US open — Fed signals, crude, DXY, geopolitical,
    US banking sector, Iran/Hormuz updates
  action_key: web-search
  action_props:
    query: US market open today Fed signals crude oil DXY geopolitical India Nifty
      impact 2026-03-06
    citations: true
- description: Synthesize US open macro scan into structured GLOBAL_SENTIMENT payload
    and write to APEX_TRADING memory
  agent_slug: global-macro-intelligence-scanner
  format_guide: 'Read  web search results. Produce a structured GLOBAL_SENTIMENT_USOPEN
    payload with: sentiment_score (-1.0 to +1.0), directional_bias for NIFTY and BANKNIFTY
    (BULLISH/BEARISH/NEUTRAL), key_drivers (list of top 3 factors), crude_wti_signal,
    dxy_signal, fed_signal, geopolitical_risk (LOW/MEDIUM/HIGH/CRITICAL), iran_hormuz_status,
    overnight_risk_assessment, and recommended_regime_bias for next session. Save
    to APEX_TRADING memory as GLOBAL_SENTIMENT_USOPEN with timestamp.'
---

Runs at 21:30 IST (16:00 UTC) when NYSE opens. Global macro scanner sweeps US market open conditions, Fed signals, crude oil, DXY, geopolitical events and writes a fresh GLOBAL_SENTIMENT score to memory. All APEX agents read this before the 08:00 IST morning pipeline.
