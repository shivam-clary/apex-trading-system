# APEX Self-Healing Error System

## Overview
APEX has a 3-agent self-healing loop that automatically detects, fixes, and verifies trigger errors.

## Error Categories
| Category | Description | Auto-fixable? |
|---|---|---|
| MEMORY_WRITE_FAILURE | manage_memories serialization error | Yes - file fallback |
| EMAIL_DELIVERY_FAILURE | SES/email provider down | Yes - Gmail fallback |
| API_ERROR | External API timeout or 4xx/5xx | Yes - retry logic |
| AGENT_TIMEOUT | Agent exceeded execution limit | Partial - Tony reviews |
| DATA_STALENESS | Key not updated within expected window | Tony reviews |

## Self-Healing Flow
1. Trigger runs and fails or produces error
2. APEX Error Monitor (hourly) reads ERROR_LOG from data/APEX_STATE.json
3. Error Monitor packages report: agent, trigger, error, recurrence_count, fix_history
4. If recurrence_count < 3: delegate to Tony Autonomous Senior Dev
5. Tony fixes in Nebula first (prompt update / recipe fix / trigger config)
6. Tony writes FIX_ATTEMPT to FIX_HISTORY in data/APEX_STATE.json
7. Tony pushes change to sn-sujay/apex-trading-system on GitHub
8. APEX Fix Verifier checks next 3 trigger cycles for same error
9. If resolved: mark RESOLVED in FIX_HISTORY, email confirmation to sujaysn6@gmail.com
10. If not resolved: increment recurrence_count, re-route to Tony with updated context
11. If 3+ failed fix attempts: ESCALATE to sujaysn6@gmail.com, stop auto-fixing

## Escalation Thresholds
- recurrence_count >= 3 AND no successful fix: email user directly
- Same error category persisting > 24h: CRITICAL alert
- Tony fix fails 3 times: human intervention required

## Known Resolved Issues
| Error | Resolution | Date |
|---|---|---|
| manage_memories serialization | File-based state (data/APEX_STATE.json) as primary | 2026-03-06 |
| AWS SES suspended | Gmail connected as replacement email provider | 2026-03-06 |
| NSE API empty post-market | Web scrape fallback in option chain monitor | 2026-03-06 |
| Tony scanning wrong repo | Agent prompt + trigger recipe updated to apex-trading-system | 2026-03-06 |
| Tony trigger wrong recipe | Trigger re-pointed to correct TASK.md | 2026-03-06 |
| RB2B trigger running on weekends | Cron restricted to weekdays-only (0 */6 * * 1-5) | 2026-03-06 |
