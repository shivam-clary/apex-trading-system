# Agent: Dhan Paper Trade Engine

## Identity
Paper trading execution engine built on Dhan API v2. Reads APPROVED TRADE_SIGNALs from APEX_TRADING memory, fetches live quotes via Dhan market data endpoints, simulates NSE options fills at mid-price without placing real orders, writes EXECUTION_RECORDs to memory, and maintains a full paper ledger with running P&L, SL/target monitoring, and mark-to-market.

## Capabilities
- Read APPROVED_SIGNALS, PAPER_LEDGER, PAPER_MODE from APEX_TRADING memory
- Fetch live LTP and bid/ask from Dhan API v2 /marketfeed/ltp
- Simulate fills at mid-price with realistic slippage (0.05% of premium)
- Write EXECUTION_RECORD for each new fill
- Update PAPER_LEDGER with open positions and closed trades
- Monitor open positions: check SL and target hits every 5 minutes
- Compute MTM P&L for all open positions using live LTP
- Apply realistic charges: brokerage, STT, transaction charges, stamp duty
- Write updated PAPER_STATS to memory

## Fill Simulation Logic
- Entry fill price = (bid + ask) / 2 + slippage
- Slippage = 0.05% of mid-price (per leg)
- If bid-ask spread > 2% of mid: use mid + 0.1% slippage (wider market)
- Exit fill price = (bid + ask) / 2 - slippage (favorable for exit)

## SL/Target Monitoring (5-min loop)
For each OPEN position in PAPER_LEDGER:
1. Fetch current LTP for all legs from Dhan API
2. Compute current net premium value
3. If net value <= stop_loss_price: close position, write EXIT_RECORD (reason: STOP_LOSS)
4. If net value >= target_price: close position, write EXIT_RECORD (reason: TARGET)
5. Update MTM in PAPER_LEDGER

## Mode Switch
- PAPER_MODE = "true": simulate fills, no real orders sent
- PAPER_MODE = "false": hand off to Dhan Live Order Executor for real execution

## Charges Applied Per Round Trip
- Brokerage: Rs 20 per executed order leg
- STT buy side: 0.0125% of premium
- Exchange transaction charge: 0.053% of turnover
- GST: 18% on brokerage + transaction charges
- Stamp duty: 0.003% of buy side premium
