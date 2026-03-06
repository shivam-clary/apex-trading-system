# APEX — Indian & Global AI Trading Intelligence System

Autonomous AI trading ecosystem for NSE options. 17 scheduled triggers, 13+ specialized agents, full paper trading pipeline with self-healing error monitoring.

## Architecture

### Agent Pipeline (in execution order)
| Agent | Role | Trigger |
|---|---|---|
| global-macro-intelligence-scanner | Asia/overnight scan, US open scan | 02:00 IST, 21:30 IST |
| india-trading-central-command | Morning pipeline, 15-min execution loop | 08:00 IST, every 15 min |
| india-market-regime-engine | Classifies TRENDING/RANGE/EVENT_DRIVEN/HIGH_VOL | Inside central command |
| sentiment-intelligence-engine | Scrapes ET, MoneyControl, Twitter, StockTwits | Every 5 min |
| nse-option-chain-monitor | PCR, IV rank, GEX, OI signals | Every 5 min |
| options-strategy-engine | Generates spread signals with confidence scores | Inside central command |
| apex-validator-gate | Quality gate — validates all inputs before execution | Inside central command |
| trading-risk-veto-authority | 6-gate risk veto, Kelly sizing, kill switch | Inside central command |
| dhan-paper-trade-engine | Paper trade execution, MTM, SL/target tracking | Inside central command |
| live-trade-performance-monitor | Sharpe, Calmar, Sortino, decay detection | Every 15 min |
| apex-self-evolution-engine | Post-session learning, prompt corrections | 16:00 IST |
| apex-system-health-monitor | Watchdog — monitors all agents, fires alerts | Every 30 min + EOD |
| apex-error-monitor | Detects trigger errors, routes to Tony for fixes | Every hour |
| apex-fix-verifier | Verifies Tony fixes resolved the issue | After each fix |
| tony-autonomous-senior-dev | Code review, fix branches, self-healing fixes | Every 4h + on-demand |
| nse-strategy-validation-engine | Walk-forward backtesting | Every Saturday |

### State Management
Primary state: data/APEX_STATE.json (file-based, always authoritative)
Secondary: Nebula memory (attempted after file write; failures are non-blocking)

### Self-Healing Error Loop
```
[Trigger Error] -> [APEX Error Monitor (hourly)]
                         |
               Package error report
                         |
               Tony Autonomous Senior Dev
               (fix in Nebula first, then push to GitHub)
                         |
               APEX Fix Verifier
               (check next 3 cycles)
                    /         \
               Fixed         Still broken
                 |                 |
          Log resolved      3+ attempts?
                                   |
                           Alert user via Gmail
```

## Trigger Schedule
| Trigger | Cron (UTC) | IST | Days |
|---|---|---|---|
| Asia/Pre-Europe Scan | 0 20 * * 0-4 | 02:00 | Sun-Thu |
| Pre-Market Pipeline | 0 2 * * 1-5 | 08:00 | Mon-Fri |
| Pre-Market Health Check | 0 3 * * 1-5 | 08:35 | Mon-Fri |
| Option Chain Monitor | 0 3-10 * * 1-5 | Hourly 09-16 | Mon-Fri |
| Sentiment Polling | 0 3-10 * * 1-5 | Hourly 09-16 | Mon-Fri |
| Execution Loop | */15 3-10 * * 1-5 | Every 15 min | Mon-Fri |
| Central Command | 0 3-10 * * 1-5 | Hourly 09-16 | Mon-Fri |
| Performance Monitor | 0 3-10 * * 1-5 | Hourly 09-16 | Mon-Fri |
| Position Monitor | 0 3-10 * * 1-5 | Hourly 09-16 | Mon-Fri |
| System Health Check | 0 3-10 * * 1-5 | Hourly 09-16 | Mon-Fri |
| EOD Reconciliation | 0 10 * * 1-5 | 15:35 | Mon-Fri |
| EOD Health Check | 0 10 * * 1-5 | 15:40 | Mon-Fri |
| US Market Open Scan | 0 16 * * 1-5 | 21:30 | Mon-Fri |
| EOD Evolution | 0 11 * * 1-5 | 16:00 | Mon-Fri |
| Walk-Forward Validation | 0 4 * * 6 | 09:30 | Saturday |
| Tony APEX Scan | 0 */4 * * 1-5 | Every 4h | Mon-Fri |
| RB2B Visitor Check | 0 */6 * * 1-5 | Every 6h | Mon-Fri |
| Error Monitor | 0 * * * 1-5 | Every hour | Mon-Fri |

## Risk Controls
- 2% daily loss circuit breaker (hard stop)
- 0.5% per-trade max risk
- Half-Kelly position sizing
- Max 3 concurrent positions
- EVENT_DRIVEN regime = 0x sizing (no trades)
- India VIX > 18 = additional gate
- 6-gate veto before any execution

## Email Alerts
All alerts route to sujaysn6@gmail.com via Gmail (AWS SES replaced).
- [APEX ALERT] = agent late/silent/failed
- [APEX CRITICAL] = 3+ consecutive failures or persistent errors
- EOD Digest = daily P&L + positions
- Evolution Report = weekly learning summary
