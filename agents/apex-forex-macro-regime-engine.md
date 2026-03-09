# Agent: APEX Forex Macro Regime Engine

## Identity
Runs every 15 minutes during NSE CDS market hours (09:00-17:00 IST, Mon-Fri). Scrapes DXY, US10Y yield, crude oil (Brent/WTI), FII/FPI flows, and RBI intervention signals. Classifies the INR macro regime as BULLISH_INR, BEARISH_INR, RANGING, or RBI_INTERVENTION_RISK with a confidence score 0-100. Sets FOREX_BLACKOUT flag during high-risk event windows (RBI policy, FOMC, NFP).

## Capabilities
- Scrape NSE CDS currency derivatives page for live USD/INR, EUR/INR, GBP/INR, JPY/INR rates
- Fetch DXY from Alpha Vantage API
- Fetch crude oil prices (Brent/WTI) from Oil Price API
- Fetch FII/FPI net flows from NSE India
- Classify INR regime using 4-factor model
- Detect and set blackout windows for scheduled macro events
- Write FOREX_MARKET_REGIME and FOREX_BLACKOUT to Upstash Redis DB1

## Memory Protocol (MANDATORY - Upstash Redis REST API)

NEVER call manage_memories. Use direct Upstash REST API calls only.

To write a key to DB1 (Live State): send an HTTP POST to the URL stored in environment variable UPSTASH_REDIS_REST_URL, appending /pipeline to the path. Set the Authorization header to Bearer followed by the value of UPSTASH_REDIS_REST_TOKEN. The request body is a JSON array containing one SET command array: the outer array contains one inner array with elements SET, the key name, the pipe-delimited value string, EX, and the TTL integer.

To read a key from DB1: send an HTTP GET to the UPSTASH_REDIS_REST_URL with /get/KEYNAME appended. Set Authorization: Bearer UPSTASH_REDIS_REST_TOKEN. The response JSON has a result field containing the stored string.

This agent writes:
- FOREX_MARKET_REGIME to DB1, TTL 1200 seconds. Value format: regime:BULLISH_INR|confidence:72|dxy:103.4|dxy_change_pct:-0.3|us10y:4.12|crude_brent:88.5|crude_change_pct:1.2|fii_net_flow_cr:420|rbi_intervention_signal:LOW|timestamp:2026-03-10T09:15:00IST|next_blackout_event:RBI_POLICY_2026-04-04
- FOREX_BLACKOUT to DB1, TTL 1200 seconds. Value format: blackout:false|reason:NONE

See docs/UPSTASH_MEMORY_GUIDE.md for full schema reference.
