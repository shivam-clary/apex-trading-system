# NSE Option Chain Monitor

## Role
Polls the full NSE option chain via Dhan API every 3 seconds during market hours (09:15–15:30 IST) for NIFTY, BANKNIFTY, FINNIFTY, and MIDCPNIFTY. Computes OI buildup/unwinding signals, IV rank, gamma exposure, and max pain levels. Writes structured snapshots to Nebula memory for consumption by the regime engine and signal generator.

## Capabilities
- Real-time option chain polling via Dhan API v2 (NSE_FNO segment)
- OI buildup and unwinding detection at strike level
- PCR (Put-Call Ratio) computation per expiry
- IV Rank and IV Percentile calculation
- Gamma exposure (GEX) aggregation across strikes
- Max pain strike computation
- Support/resistance identification from OI concentration
- Writes to Nebula memory key: `OPTION_CHAIN_SNAPSHOT`

## Memory Keys Written
| Key | Description |
|-----|-------------|
| `OPTION_CHAIN_SNAPSHOT` | Full option chain data with OI, IV, Greeks per strike |
| `PCR_CURRENT` | Current put-call ratio per index |
| `MAX_PAIN_LEVELS` | Max pain strike prices per expiry |
| `GEX_LEVELS` | Gamma exposure by strike — key support/resistance |
| `IV_RANK` | Current IV rank (0–100) per index |

## Trigger
- Runs every 3 seconds during NSE market hours via Nebula scheduler
- Can be called on-demand by india-trading-central-command

## Integration
- Feeds data to: `india-market-regime-engine`, `options-strategy-engine`
- Reads from: Dhan API v2 option chain endpoints
- Part of: APEX Trading System
