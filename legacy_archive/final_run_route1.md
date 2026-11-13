# Route 1 | Paper Run Final Report
======================================================================
Generated (UTC): 2026-11-13 18:38:19 UTC
Generated (PST): 2026-11-13 10:38:19 PST
Source: trading_desk_state.json + .route1_run.log (no invented figures)

## Run Configuration
- paper capital: $100.00 (paper-only, no real trades)
- config: v3
- asset: GOBLIN
- CONSENSUS_MIN = 8
- SIGNAL_GATE = 0.35 (|signal| >= 0.35 qualifies)
- BASE_CHANGE_BUY = +0.010 (+1.0%)
- BASE_CHANGE_SELL = -0.010 (-1.0%)
- session status: PAPER-ONLY
- phase: 2

## Final Outcome (42/42 trades won)
- Start capital: $100.00
- Final capital: $512.05
- Total profit: +$412.05 (412.05%)
- Total trades: 42
- Wins: 42  |  Losses: 0  |  Draws: 0
- Win rate: 100.00%
- All trades: BUY style entries
- Ticks processed: 358
- Open positions at close: 42
- Total votes cast: 4296
- Max drawdown: 0.0%
- Distinct symbols traded: 33
- Run start: 8:10:55 (PST)  |  Session complete: 09:10:48 (PST)

## Verification
- Commit referenced: 23dcf07 (paper_run.py — dead TRADE_DESK removed,
  gate/base knobs named as transparent constants; values unchanged)
- Run log confirms: SESSION COMPLETE at 09:10:48, Final capital $512.05,
  358 ticks, 42 trades.
- /api/state and trading_desk_state.json confirm capital $512.05, ticks 358.

## Known State-Flag Note (transparency)
- trading_desk_state.json and /api/state carried `session_running: True`
  after the session completed (process finished 09:10:48).
  This was a stale dashboard flag; the run had already closed by the time
  the final-report watcher fired at 09:12:00. The watcher reported
  "STILL RUNNING" solely because of this stale flag — not because the run
  was still live. For that reason the watcher cron was removed after this
  completed run and the stray mid-run marker deleted.
- The `peak` field in the dashboard state remains at the starting value;
  it is a stale dashboard field and not part of the final recap.
