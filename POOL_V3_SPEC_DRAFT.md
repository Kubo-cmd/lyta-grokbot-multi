# POOL V3 — THIRD INDEPENDENT POOL (ROUTE A, DRAFT FOR SIGN-OFF)

**Status: DRAFT only. No commit, no push, no trades. Observation-only, zero capital.**

Route A is the last remaining evidence path named in `FREEZE_LOCK.md`: a
*structurally different* pool (new generator — not the same fixture as the
frozen Round-12 pool) to test whether the loose floor (V2 6/0.20) ever catches a
healthy-liquidity, tradable row.

## 1. Why "structurally different"
Frozen Round-12 pool was single-pool, single-floor, same adapter spec
(`pumpfun_phase2_adapter_ext_run.py`, commit `084334d`). This run must differ in
*generator*, not in analysis code:
- Same analysis engine (alias `agg.consensus(adapter.to_engine_pair(p), narrative="")`).
- Same floor variants: V0 8/0.35 · V1 7/0.25 · V2 6/0.20 · V3 8/0.50.
- Different data source: new synthetic generator built from a different
  microstructure seed (see §2).

## 2. Generator design (draft — new microstructure)
- Generate 60 candidates. Each candidate: score vector (consent 0–8), signal gate
  (vol24h proxy), liquidity depth (base + book), hidden-liquidity tag rule.
- Key change vs. Round-12 fixture: **liquidity reports from an order-book
  simulator with gas/burn fees** rather than the previous flat cash-E metric, and
  **2-phase confidence**: Phase-1 score gate independent of Phase-2 liquidity
  confirmation (stall-stop 30s applied between phases).
- Keep frozen-log schema byte-compatible: `roundN_v{M}_YYYYMMDD.log` with the same
  `candidates screened`, `>>> qualified`, `stand-down` block structure so the
  existing parser and `--probe` harness validate it out of the box.

## 3. Probe kit configuration (same as Route 1–2)
- `phase2_local_simulator.py --probe --v0..v3` output validated against frozen log.
- Paper-only frame: observation only. No live pump.dev writes, no live exchange
  writes, no live API calls in the final run; read-only endpoints are
  offline-verifiable probe data only.

## 4. Decision gates for this run
| Gate | Pass condition | Fail condition |
|---|---|---|
| G1 | V0/V3 stand-down, V1/V2 qualify rows on score (same as frozen log) | Engine mis-match vs. frozen reference |
| G2 | Leg 1 (score gate) per variant | No info |
| G3 | 30s stall confirmation: liquidity tag must clear (hidden_liquidity FAIL) | More rows qualify with healthy depth than frozen benchmark (20/60) |
| G4 | Trading verdict | No tradable pattern under stop 35% / trailing 30% / stall 30s |
| G5 | Report + freeze-record update | Unverified numbers in record |

## 5. What we are trying to learn
- Does the loose floor ever admit a row with *healthy liquidity depth* and a
  *trailing-eligible* signal on a structurally different pool?
- If yes: the loose floor is a viable evidence path (paper P&L under exit rules
  computed from this run). If no: the floor-and-tag finding is robust and the
  desk returns to "stop" with a record of two independent pools.

## 6. Execution order (after sign-off)
1. Generate pool → freeze-log schema validation.
2. Run `--probe` / `--v0..v3` (engine-identical harness, pre-read-only check).
3. Paper exit-rule bench on new qualified rows (35-row bench template from
   `PAPER_EXIT_RULE_BENCH.md`).
4. Freeze record + comparison report; commit + push (user sign-off required).

## 7. Risks / controls
- Wrong generator ≠ Route A: documented, abort and reorder sign-off.
- No live data in this draft: all parser/verification points are offline.
- Keep the repo private; only the user approval gate can release commits/pushes.

*End of draft. Route A (new pool) awaits user sign-off before any generation or
report is committed.*
