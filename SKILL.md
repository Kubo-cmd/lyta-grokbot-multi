---
name: pumpfun-phase2-paper
description: Zero-burn paper-only Phase 2 workflow for lyta-grokbot-multi pump.fun desk: pull -> reverse-engineer -> paper gate -> unified pipeline -> night close. Triggered by "pumpfun".
---

# Pump.fun Phase 2 paper workflow (zero-burn)

All runs here are observation only. No trades executed. Do not switch to live. Keep results in `pumpfun_pipeline_output/state.json`, `pumpfun_reverse_output/*.json`, `pumpfun_gate_output/*.json`, and wrap with `pumpfun_nightclose_<ts>.json`.

## Phase 2 sequence (in order)

1. **Deterministic unit test** — `python pumpfun_test.py`
   - Must exit 0: pull -> score -> emit -> dedup -> state.json round-trip PASS.
   - Seeded fallback to `pumpfun` holds when `pumpfun_desk_simulator` adapter fails.

2. **Reverse engineer** — `python pumpfun_reverse_engineer.py --verbose`
   - Live DexScreener feed via `pumpfun_desk_simulator`; writes `pumpfun_reverse_output/round_<TS>.json`.
   - Reads: `candidate_count`, `rows`, `surviving_candidates`, `stand_downs`, `pass_band`.

3. **Paper gate** — `python pumpfun_paper_gate.py` (on every reverse JSON found in `pumpfun_reverse_output/`)
   - A3b gate: `consent >= 8 AND |combined_score| >= 0.35` => only then `ADVANCE`; else `STAND DOWN`.
   - Write consolidated result to `pumpfun_gate_output/latest_gate.json`.

4. **Unified pipeline** — `python pumpfun_pipeline.py --once`
   - Records `pumpfun_pipeline_output/state.json` (desk.stand_down/candidates/advance/mean_consent/mean_abs_score/latest_ids) and `pumpfun_pipeline_output/run<N>.txt`.
   - One complete run = one paper day.

5. **Night close** — `python overnight_paper_wrap.py` (exit 0)
   - Then `pumpfun_nightclose_<TS>.json` consolidating `state.json` + `latest_gate.json` + reverse-engineer pack.

## Live-run facts from 2026-11-27 (verified exit 0)

- Test: `pumpfun_test.py` PASS; pipeline unique candidates 8 bots + 3 volume copies; dedupe after round 2.
- Unified run: 26 rounds / 26 candidates / **26 STAND DOWN** / advance=0 / mean_consent=1.62 / mean_abs_score=0.1186.
- Reverse engineer (live): 18 candidates, 5 surviving MIXED-signature watch items.
- Paper gate: all 5 survive -> **STAND DOWN** (consent 1-6/8, |score| < 0.35). no `ADVANCE`.
- Watchlist: 19 candidates retained; `micro_budget_ok=false` everywhere.

## Decision rules (do not bend)

- `ADVANCE` only when A3b gate passes on a surviving candidate; otherwise `STAND DOWN`, verbose reason via stand_down_reasons.
- No capital, no trades, no real order execution — zero-burn constraint is invariant.
- Preserve the exact JSON schemas of state.json, round_*.json, latest_gate.json (downstream tools consume them).
