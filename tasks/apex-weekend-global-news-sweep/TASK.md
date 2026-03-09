---
slug: apex-weekend-global-news-sweep
title: APEX — Weekend Global News Sweep
steps:
- description: Search for global macro news and geopolitical events from the past 48 hours
    relevant to Indian markets
  action_key: web-search
  action_props:
    query: India NSE stock market Fed RBI crude oil DXY geopolitical news this weekend macro
      events 2026
- description: Search for US economic data, earnings, and Fed signals from the weekend
  action_key: web-search
  action_props:
    query: US Federal Reserve economic data jobs report earnings S&P500 weekend news impact
      Asia markets
- description: Search for SGX Nifty, Asian markets, and any India-specific corporate or
    political news
  action_key: web-search
  action_props:
    query: SGX Nifty Nifty50 BankNifty outlook Monday open FII DII flows India corporate
      news weekend
- description: 'Synthesize all three search results into a structured WEEKEND_MACRO_SNAPSHOT.
    Write WEEKEND_MACRO_SNAPSHOT and WEEKEND_SWEEP_LOG directly to Upstash Redis DB2 using
    the REST API. WEEKEND_MACRO_SNAPSHOT TTL = 172800s (48hr). WEEKEND_SWEEP_LOG TTL = 172800s.
    Value format: timestamp:<ISO>|sentiment_bias:<BULLISH/BEARISH/NEUTRAL>|confidence:<0-100>|fed_signal:<HAWKISH/DOVISH/NEUTRAL>|crude_bias:<UP/DOWN/FLAT>|dxy_bias:<UP/DOWN/FLAT>|sgx_nifty_signal:<PREMIUM/DISCOUNT/FLAT>|monday_opening_bias:<GAP_UP/GAP_DOWN/FLAT>|key_events:<comma-separated
    headlines>|analyst_note:<2-3 sentence summary>. Use POST https://{UPSTASH_REDIS_REST_URL_DB2}/pipeline
    with body [["SET","WEEKEND_MACRO_SNAPSHOT","<value>","EX",172800]]. NEVER call
    manage_memories.'
  agent_id: agt_069a8f413b5b71f08000659d18ea5ee8
  agent_slug: global-macro-intelligence-scanner
---
