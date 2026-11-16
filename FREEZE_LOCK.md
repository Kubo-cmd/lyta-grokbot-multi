# FREEZE LOCK — pump.fun Phase 2 paper desk (observation only)

**This run is observation only. No trades executed.**

**Status: FREEZE RE-OPENED (local paper freeze — observation only).**
Filter-sensitivity probe executed on the frozen 24-candidate pool
(V0 baseline / V1 loose / V2 looser / V3 tight). Remote stays PRIVATE, no push
until user approval.

## 1. Freeze state (as of commit 636c8d7)

- **Remote:** `origin/main` is **PRIVATE** (`Kubo-cmd/lyta-grokbot-multi`).
  Local == remote == `636c8d7`, verified in sync. No further push until user approval.
- **Last committed freeze set:**
  - `b7d3cbd` — Route B: pump.fun Phase 2 zero-burn calibrated paper run
  - `636c8d7` — adapter extension (`pumpfun_phase2_adapter_ext_run.py`) + comparison report (`PAPER_COMPARE_ROUTE_B_ADAPTER.md`)
- **New evidence appended (round 9, observation only):** `p2adapter_ext_20261115_181248.log` — 24 candidates screened, 0 gate-qualified, 0 paper fills, $0.00 P&L, 100% stand-down, exit 0.

## 2. Freeze-safe lanes (all complete)

|| # | Lane | Deliverable | Verified |
|---|---|---|---|---|
| 1 | Freeze wrap | local freeze record | ✅ |
| 2 | Extend adapter path to real pump.fun candidates | `pumpfun_phase2_adapter_ext_run.py` (compile OK, run exit 0, **24 candidates**, 0 qualified, 0 fills, observation-only/zero-burn) | ✅ |
| 3 | Comparison report | `PAPER_COMPARE_ROUTE_B_ADAPTER.md` | ✅ |
| 4 | README/lock-in | this document | ✅ |

## 3. Observation-only / zero-burn declaration

- **This run is observation only. No trades executed.**
- Paper-only framing: no live capital, no live Grok Bot workshop execution, no live exchange writes.
- `PAPER_ROUTE_B_FINAL.md` — 6 candidates screened, 0 gate-qualified, 0 paper fills, $0.00 P&L, 0 stand-down reasons (beyond gate), zero-burn.
- Test gate: `python3 -m pytest tests/ -v --cache-clear` → exit 1 (28 passed, 3 failed — pre-existing Tightened-lock asserts on `lyta-grok-desk/circuit.toml` / `circuit-settings.d.ts`; **freeze: leave that lock, do not strip settings to go green**).

## 4. Variant filter decision (V0/V1/V2/V3), evidence from the verified engine
Probe: 24 frozen-candidate pool, gates V0=8/0.35 (frozen baseline), V1=7/0.25,
V2=6/0.20 (loosened), V3=8/0.50.
- V0, V3 → 0 qualified (baseline holds: 100% stand-down).
- V1 (7/0.25) → ApeCoin/Etherion/Ovation reach 7/8 buy votes with |score| 0.24–0.28;
  loosening the vote floor from 8 to 7 lets 3 green candidates into the qualified
  set — every one still tagged `hidden_liquidity` (liq < vol×2).
- V2 (6/0.20) → same 3 candidates remain the only qualified rows; all carry the
  `hidden_liquidity` stand-down tag.
- Structural ceiling: no candidate in this pump.dev-format pool can ever reach
  8 buy votes (max observed = 7), so under the frozen **consensus_min=8 floor
  the pool is structurally stand-down**, independent of the score floor.
Conclusion: the "different filter" that can at all qualify rows on this pool is a
loosened vote floor (V2: CONSENSUS_MIN=6, SIGNAL_GATE=0.20), and even then it is
3 green candidates carrying an unresolved hidden-liquidity tag.

## 5. Decision gate (for the user)
- **No further commits/pushes** until the user approves.
- Next trigger (if approved): reopen the freeze and run additional paper rounds
  (20+ positions) before any fine-tuning; MIN_LIQ revisit ($50k→$20k) only if
  more trades are desired.
- Pattern status: **NOT yet established** — 100% stand-down across all scored
  candidates (consensus_min + signal_gate + hidden_liquidity); no tradable
  pattern emerged during the paper window.

## 7. Extended rounds — cumulative evidence (zero-burn, no trade executed)

| Round | Pool size | Gate | Qualified | Stand-down | Fills | P&L |
|---|---|---|---|---|---|---|
| 9 | 45 | V0 frozen (8/0.35) | 0 | 45 | 0 | $0.00 |
| 10 | 24 | V2 looser (6/0.20) | 3 | 21 | 0 | $0.00 |
| 11 | 45 | V2 looser (6/0.20) | 14 | 31 | 0 | $0.00 |
| 12 | 60 | V2 looser (6/0.20) | 15 | 45 | 0 | $0.00 |
| 12 | 60 | V0 frozen (8/0.35) | 0 | 60 | 0 | $0.00 |

Logs: `round10_v2_20261115.log`, `round11_v2_20261115.log`,
`round11_baseline_20261115.log`, `round12_v2_20261115.log`,
`round12_baseline_20261115.log`.

Structured finding (final, paper window closed): under the frozen V0 baseline
the pool is structurally stand-down (max consent 7/8 vs required 8). Under
the loosened V2 floor the qualified set GROWS with sample size (3/24 →
14/45 → 15/60), but every qualified row sits at the consent ceiling (7 vs
floor 6) AND carries `hidden_liquidity` (liquidity < 2× vol24h). The loose
floor does not find healthy liquidity — it finds green-ish candidates with
thin depth. No tradable pattern established from paper evidence; zero trades
executed across 200+ candidate screenings.

## 8. Decision gate — final (for the user)

- **No further commits/pushes** until user approval. Repo remains PRIVATE.
- **Recommended: Option C — STOP.** Close the paper freeze with the
  documented conclusion (no tradable pattern; flexible floor confirms the
  vote-ceiling + hidden-liquidity finding). This matches "private until
  flawless": keep the artifacts local and clean; do not commit/push anything.
- MIN_LIQ revisit ($50k→$20k) is not recommended: liquidity tags are hidden
  at every size; a lower floor does not change the pattern.
- If the user still wants more work: a *third* independent pool (new
  generator, not the same fixture) is the only remaining evidence path;
  propose and wait for approval.

*End of freeze lock. Observation only — no trade executed.*
