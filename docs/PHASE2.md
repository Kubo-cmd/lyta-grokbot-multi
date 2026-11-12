# Phase 2 — pump.fun memecoin execution (paper-only)

**Activation word: `pumpfun`.** Until the user says `pumpfun`, this file is a
checklist only. Nothing below is wired, committed as live, or executed.

## What the user asked for (verbatim)

- "the pump fun perimeters dont work on trencher ai or circuit ai. we only got good
  feedbacks from spot trading."
- "make sure to maek this repo transparent and straigt forward. get rid of anything
  not useful"
- "pumpfun" trigger: Phase 2 activated; awaiting explicit confirmation before live trades.

## The trap to remember (from paper data)

The spot/Circuit paper session ran with `CONSENSUS_MIN = 5` and a 20-tick trend
staleness decay. Those limits were tuned for Circuit market data, NOT for the
new-launch volatility of pump.fun. Do **not** copy the pump.fun rule set into the
Circuit paper runner. The two stay separate, and the pump.fun rule set is only
active after the `pumpfun` trigger.

## Activation recipe (apply only when the user says `pumpfun`)

1. `paper_run.py`: point the signal source at `pumpfun_adapter.py` (new-launch pump.fun
   data) instead of the Circuit market simulator; keep `CONSENSUS_MIN = 5`,
   the 12-bot roster, the $100 paper pool, no wallet import, no signing.
2. `config/pumpfun_desk_config.txt` → wired in as defaults:
   - min consensus 7/12 · minimum liquidity $50,000
   - skip coins up >100% in the last hour · stop −35% · take profit +50%
   - paper-only guards: no wallet import, no signing/order execution, Telegram OFF
3. Nothing is live. The whole Phase 2 path stays paper-only (no betting, no real
   orders, no wallet, no signing) until the user explicitly gives the go.

## Expected diff on activation

| File | Change |
|---|---|
| `paper_run.py` | signal source → `pumpfun_adapter.py`; config load |
| `config/pumpfun_desk_config.txt` | used as the Phase 2 defaults |
| `README.md` | "📊 Status" line → "Phase 2 — pumpfun trigger active (paper-only)" |

## Constraints (never waive)

- $100 paper pool only (`_paper_agent.ts`), no wallet import, no signing.
- Telegram alerts OFF for paper mode.
- Exactly one execution of this recipe per `pumpfun` message.
