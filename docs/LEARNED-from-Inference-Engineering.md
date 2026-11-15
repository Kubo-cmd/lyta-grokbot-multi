# LYTA × Inference Engineering — What We Learned & What It Upgrades

> Grounded in the public *Inference Engineering* surface (Baseten Books) and
> verifed against the LYTA repo on disk. No manuscript text, no verbatim
> quoting.

## One-line takeaway
Inference serving power runs through a **three-layer map** — runtime, infrastructure, tooling — and each layer must be budgeted and optimized separately. Lyta already has this structure; the book adds the *discipline* of measuring every layer's cost.

## Sources (verified)
- Baseten Books: `https://www.baseten.co/inference-engineering`
- Online book TOC: `https://www.baseten.co/inference-engineering/book`
- Ch. 0 (Inference): `https://www.baseten.co/inference-engineering/book/00-inference`
- Digital download: `https://www.baseten.co/inference-engineering/digital-download`
- LYTA repo (verified on disk): `https://github.com/Kubo-cmd/lyta-grokbot-multi`

## The three-layer map applied to LYTA
| Book layer | LYTA component (verified files) | What each layer optimizes |
|---|---|---|
| **Runtime** (the thing that serves) | `paper_desk_simulator.py` — entry, trailing exit, stale/dead exits, `PO_*` params | latency of a single paper execution, cost per leg, exit discipline |
| **Infrastructure** (scaling, routing, gates) | `consensus_aggregator.py`, `real_trade_feed.py`, `pumpfun_phase2_paper_run.py` | how many pairs are screened, how the 8/8 consent gate scales |
| **Tooling** (the abstraction layer) | `lyta-grok-desk/` (14 OpenBot agents, `.circuit` engine, `CIRCUIT_*.TXT` prompts) | the right control/productivity trade-off per agent |

### The lesson for Lyta
These three layers optimize differently and must be tuned separately.
`STRATEGY_FINALIZE.md` and `ARCHITECTURE.md` already describe this map; the
book makes it an explicit engineering principle rather than a paper-note.

## Lesson 1 — Budget latency and cost per layer
Chapter 1's core idea is that inference systems must **budget latency and
cost explicitly**, then run a "taste and optimize" loop.

### What LYTA did with it
- Added **decision latency** (`latency_s`) around `decide_pair()` in
  `paper_trade_exec.py` — real `perf_counter()` delta, logged per cycle.
- Added a **cost proxy** (`cost_tokens`, paper-only = 0, since no live
  inference is consumed in paper mode).
- Added `evaluate_budget()` + `_apply_budget()`: every cycle returns
  `compounding` or `stand-down`. On a closed paper trade that stands down,
  paper size is halved (floor 0.01 SOL). Observation-only stand-downs do
  not shrink size.
- Added `BudgetLedger` (runtime / infrastructure / tooling) with
  `add()` / `reset()` / `report()`. Closed paper trades accumulate;
  live-scan stand-downs print the verdict without polluting avg P&L.
- Example verified run output:
  ```
  [paper] decision latency 4.1e-05s, cost proxy 0 tokens, live-GOBLIN/SOL
  [paper] P&L $+0.498% on paper pair live-GOBLIN/SOL
  [budget] verdict=compounding latency_ok=True cost_ok=True pnl_ok=True
  [budget ledger] decisions=1  avg_latency=0.000041s  avg_cost=0t  avg_pnl=+0.498%
  ```

### What to do next (still paper-only)
- Add the same latency/cost budget around the `lyta-grok-desk` agent calls
  once Grok-bot scoring is wired (GROK_BOT_SCORE / GROK_BOT_RISK remain
  documented placeholders until a key is dropped in the secure vault and
  funding is approved, per `paper_trade_exec.py` SECURITY NOTE).
- Keep a per-decision ledger column `decision_latency_s` and `cost_tokens`.

## Lesson 2 — Don't dump a book into an agent's context in one chunk
The author's own spec warns that ~60k tokens is too much to feed into an
agent as a single chunk.

### What LYTA already does
- Each of the 14 agents gets its own scoped `CIRCUIT_*.TXT` prompt/JSON.
- Phase-2 has a separate `pumpfun_phase2_adaptation.txt` rather than one
  giant briefing.

### What LYTA did with it
- Added `scripts/check_prompt_scoping.py`, which enforces a **per-prompt
  token budget** so no single agent can silently grow past the safe window.
- Kept the public three-layer doc **scoped per layer** (runtime / infrastructure
  / tooling), not in one wall-of-text prompt.

## Zero-burn guard
Everything above is paper-only and observation-only. No real trades,
no real DEX orders, no live Grok-bot calls, no live inference. The latency
and cost proxies are logged as paper proxies only.

## Options for the next step
1. Add the same latency/cost budget around the Grok-bot committee calls
   (after a key + funding approval).
2. Expand `docs/LEARNED-from-Inference-Engineering.md` per-layer budgets.
3. Keep the scoping guard as the long-term guard against the ~60k-token trap.

## Appendix A — Shared system module `lyta_budget.py` (paper-only)

The budget discipline is now **one shared module** so the paper runner and
the whole lyta system (lyta-grok-desk, pumpfun simulator, future live
agents) use the same gate. Layout: `BUDGET_*` constants ->
`evaluate_budget()` -> `_apply_budget()` -> `BudgetLedger`
(runtime / infrastructure / tooling). One `budget()` context manager
times any instrumented lyta call (cost tokens are supplied by the caller
on exit; 0 in paper mode).

```python
# lyta_budget.py — shared, zero-burn, no live orders, no live API reads
BUDGET_DECISION_LATENCY_S = 0.100      # per-decision wall clock
BUDGET_COST_TOKENS = 6000              # inference+tooling proxy per circuit cycle
BUDGET_PNL_PCT = 0.0                   # accept >= 0% per closed paper trade

evaluate_budget(latency_s, cost_tokens, pnl_pct) -> verdict
  compounding  |  stand-down

_apply_budget(latency_s, cost_tokens, pnl_pct, *, record=False)
  returns the gate verdict; **only a closed paper trade that stands down
  halves paper_size (floor 0.01 SOL)** — observation-only stand-downs do
  not shrink size; they only accumulate the ledger.

BudgetLedger(runtime|infrastructure|tooling) add()/reset()/report()
  logs every measured cycle; live-scan stand-downs print the verdict
  without polluting the avg P&L.
```

**Verified by actually running `python paper_trade_exec.py`** (observation
only, exit 0):

```text
  [paper] decision latency 2.4e-05s, cost proxy 0 tokens, live-GOBLIN/SOL
  [paper] P&L $+0.498% on paper pair live-GOBLIN/SOL
  [budget] verdict=compounding latency_ok=True cost_ok=True pnl_ok=True
  [budget ledger] decisions=1  avg_latency=0.000027s  avg_cost=0t  avg_pnl=+0.498%
  [budget ledger] runtime        lat_budget=0.000s
  [budget ledger] infrastructure lat_budget=0.000s
  [budget ledger] tooling        lat_budget=0.000s
```

Paper size reaction (verified): closed-trade stand-down halves `paper_size`
0.05 -> 0.025 SOL (floor 0.01 SOL), while a record=False observation
stand-down leaves it untouched.

## Zero-burn guard

Everything above is paper-only and observation-only. No real trades,
no real DEX orders, no live Grok-bot calls, no live inference. The
latency and cost proxies are logged as paper proxies only; real Grok-bot
scoring is a documented future cost line pending vault key + funding
approval.

## Appendix B — Circuit papertrade window context (external reference)
> Grounded in the file attached to this conversation (`pasted_content
_2026-11-15_11-09-52-911_8cfc9a.txt`), a Circuit AI platform papertrade analytics
> post. Reference data only; cited, not quoted.
>
> **Market window (Nov 8 - Nov 15):** BTC ~ $73,400 -> $64,000 (-13%), ETH ~ $2,139
> -> $1,781 (-17%). Anything short the drop made money; anything long the market
> lost.
>
> **What the winners had in common (for lyta's paper posture):**
> - Winners were **short while crypto fell**; returns came from the trend plus
>   position decision, not from a signal edge. "The vote picks the direction, but
>   this week's returns came from the trend and the position size."
> - Low-turnover, held positions kept fees/funding near zero ($6.02 for 18 trades),
>   which is why a -13/-17% window still read positive.
> - Losers shared **leverage + choppy flip-flopping** (10x on $500 positions) and
>   fighting the consensus direction.
> - Post-week warning: a 5x short across nine coins gives profit back just as fast
>   when the market turns up.
>
> - Lyta paper-trade implications (observation-only): this is the same trade-off
>   the paper budget loop encodes — direction bias alone is market luck until the
>   latency/cost/P&L gate and the per-closed-trade paper-size reaction verify it.
>   A short-heavy or high-leverage paper posture must sit under the same
>   `stand-down` gate as any other signal, so a falling-week paper win does not hide
>   unverified paper-size or fee exposure. No real trades, no re-administered risk
>   caps; purely a framing lesson for how lyta frames paper results.

## Appendix C — Paper bot fleet state (reference data, from Trencher AI)
> Sourced from Trencher AI's paper-lens / platform summary (live state as of this
> session). These are **operational facts about the paper fleet, not trading advice**.
>
> **Fleet:** 7 active paper bots + 4 paused paper bots. 1 live bot in setup (real
> money has not started).
>
> **Safety:** paper bots run on simulated SOL, not real funds — safe for practice.
>
> **Platform notes:** Trenchers supports launchpad sniping across Solana
> launchpads (expanding beyond Pump.fun). Tokens completing their curve graduate to
> **PumpSwap, not Raydium**. Every bot can be customized (review, configure, pause,
> fund, monitor) from the platform — no forced default strategies.
>
> **Fee / size economics (paper framing):**
> - Pump.fun charges a **1% protocol fee per swap**; Trenchers' platform fee varies.
> - Small trades suffer heavy fee drag; approximate break-even points:
>   0.01 SOL ≈ 1.25x, 0.05 SOL ≈ 1.07x, 0.1 SOL ≈ 1.04x, 0.5–1 SOL ≈ 1.02x.
> - Larger trades cut fee drag but raise the loss if one token rugs.
>
> **Guardrails for lyta's paper budget:** newly launched-token sniping is extremely
> high risk (most launchpad snipers lose); a stop-loss is a trigger-to-attempt, not
> a guaranteed cap (slippage, thin liquidity, rugs). Bots spawn **unfunded** — they
> will not buy until paper SOL is allocated. Realized PnL excludes open positions,
> which must be checked separately.
>
> **Lyta paper-budget implication:** these constraints belong in the same
> paper-only framing as Appendix A/B — the budget loop's `stand-down` gate and
> `paper_size` reaction should be written to expect unfunded bots, a 1% pump fee
> drag on small sizes, and no guaranteed stops, so the paper discipline mirrors the
> real platform's risk realities without executing anything.

## Appendix D — Grok Bot team + lint-rule self-check (implemented)

Public signals (gatsby / 0xg4tsby; Yarchi @undefinedKi) described a Grok Bot
crew that *delegates* (Grok Bot → Chief of Staff → Managers → Workers; 6 bots,
200+ agents) and *self-checks* ("every agent mistake becomes a lint rule, not
a prompt"; verification via videos, screenshots, tests). The workshop itself
is not a lyta deliverable. What transferred:

| Signal | LYTA implementation | File |
|--------|---------------------|------|
| Team that delegates | `DelegationRouter.route()` — managers assess, then workers run, then oversight, then CoS hold | `lyta-grok-desk/grok_team.py` |
| Resume unchanged, what can run did | Paper envelope + Tightened 7/12 stay; team only routes | same + `lyta_budget.py` |
| Lint rule, not a prompt | `_LINT_RULES` config per role; `verify()` revokes on fail | `grok_team.py` |
| Evidence before the decider | `EvidencePacket` / `EvidenceRevoke` | `grok_team.py` |
| Budget held at Chief of Staff | `approve_envelope()` unpacks envelope compliance, then `evaluate_budget` | `grok_team.py` |

**Paper-budget implication:** the team layer sits *below* the paper gate. A
size of 0.05 SOL or 1.2 SOL, or negative paper PnL, is `stand_down` before any
manager/worker output can reach a decision. Observation only. No trades
executed. Tests in `tests/test_grok_team.py`.
