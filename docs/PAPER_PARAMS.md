# Paper Trading Parameters — LYTA Grok Trading Desk

Verified against the final paper session: **60 minutes, 10-second ticks, Tick 1–358, $100 pool**.

> Principle: *the pump.fun perimeters do not work on Trencher AI or Circuit AI; only spot
> trading produced good feedback.* Keep the Circuit paper params below as the live
> paper-set, and treat the pump.fun rule set as a separate Phase 2 config.

## Parameter map — where each setting lives

| File | What it holds |
|---|---|
| `paper_run.py` | Signal weights, trend staleness, consensus min, move thresholds, state writer |
| `lyta-grok-desk/trading_desk.py` | P&L metrics (win-rate, expectancy, drawdown) |
| `web_dashboard.py` | Dashboard render + `/api/state` (also serves `/trading_desk.html`) |
| `config/bot_versions_config.json` | Per-bot config overrides (local, do not commit) |
| `config/your_run_config.json` | Local tuning (local, do not commit) |

## Signal weights (base, verified)

| Parameter | Value | Role |
|---|---|---|
| `trend_factor` | +0.75 (up) / −0.75 (down) | wind direction |
| Trend staleness | 5% extra decay per tick after `trend_age > 20`, capped at 65% penalty | no stale trends |
| `score_norm` | `score/100 * 2 − 1` | agent confidence (−1…+1) |
| `rug_norm` | `1 − rug_risk` | survival (lower rug = better) |
| `liq_norm` | `liquidity` | survival (higher = better) |
| `vol_norm` | `volume` | activity |
| `mom_norm` | `change24h / 25.0` | momentum (−1…+1) |
| `change_amp` | ±0.15 cap | non-linear boost for high momentum |

## Consensus & gating

| Parameter | Value | Role |
|---|---|---|
| `CONSENSUS_MIN` | 5 | votes before any paper capital move |
| Buy | `buy_votes ≥ 5` **and** `buy > sell` | enter/exit buy |
| Sell | `sell_votes ≥ 5` **and** `sell > buy` | enter/exit sell |
| Pass / Hold | otherwise | no move; no capital touched |

## Validation — final paper session (Tick 1–358, 10s ticks, 07:04→07:49)

| Metric | Value |
|---|---|
| Start capital | $100.00 |
| End capital | $13.67 |
| Total ticks | 358 |
| Win rate | 34.2% |
| Expectancy | −0.94 per trade |
| Total trades | 202 |
| Max drawdown | 91.37% |
| Vote tally | BUY 966 / SELL 1088 / PASS 1968 / HOLD 274 / STAND_DOWN 0 |

## Phase 2 rules (written here so the repo stays transparent)

- `pumpfun_desk_config.txt` (Phase 2 config, enabled only on the `pumpfun` trigger):
  min consensus 7/12, minimum liquidity $50,000, skip coins up >100% per hour,
  stop loss −35%, take profit +50%, paper-only.
- The pump.fun perimeters do **not** transfer to Trencher AI or Circuit AI — they are
  Phase 2-specific and gated.
- Paper pool $100 (enforced in `_paper_agent.ts`); Telegram alerts OFF;
  **no wallet import**; **no signing**; no live trades until explicit user go.

## A2 tuning run — approved after the final session post-mortem
Final session (358 ticks, 10s ticks, $100 pool) output: **end capital $5.50, win rate 32.1%**
below the 35–55% band → tuning required. Root cause: current logic acted on *any* dense
bot-consensus direction, even when the composite signal was near zero and the market
trend disagreed with the vote direction. Fix applied to `paper_run.py`:

| Gate | Before | After | Effect |
|---|---|---|---|
| Consensus min | 5 | **7** (matches Phase 2 "min 7/12") | fewer, stronger entries; fewer noisy trades |
| Signal gate | none | **\|signal\| ≥ 0.30** | skips near-flat signals (noise) |
| Trend alignment | act on vote direction | **BUY only on up / SELL only on down** | removes directional-mismatch losses |

Per-trade logging enabled: `trade_history` (last 50) + `tick_history` (last 50) in
`/api/state` and `trading_desk_state.json`; stand-down reasons printed live every tick.

### What to compare (run once, 60 min, 10s ticks)
| Metric | Baseline A1 (old) | S1 baseline (this repo, 358 ticks) | A2 will produce |
|---|---|---|---|
| Start capital | $100 | $100 | $100 |
| End capital | $13.67 | $5.50 | **target: keep ≥ $100 drop < 65%** |
| Win rate | 34.2% | 32.1% | **target 35–55%** |
| Expectancy | −0.94 | −1.30 | closer to ≥ 0 |
| Max drawdown | 91.37% | 94.52% | lower |
| Total trades | 202 | 212 | expect fewer (better quality) |

Run: `python3 paper_run.py --minutes 60 --interval 10` (Terminal B) → compare
`/api/state` `pnl` block + `trade_history` win/loss distribution. If the band is still
outside after A2, tune the move-size step (+2%/−1.5% → +1.5%/−1.5%) next.

