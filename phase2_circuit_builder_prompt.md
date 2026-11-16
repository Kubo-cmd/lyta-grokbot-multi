# phase2_circuit_builder_prompt.md
## Phase 2 paper-window prompt — paste into Circuit Builder / AI agent session
> Ready-to-paste prompt for the Phase 2 paper window.
> **Observation only. No trades executed. Paper-only framing: no live capital,
> no live Grok Bot workshop execution, no live exchange writes.**

------------------------------------------------------------------------
# PHASE 2 PAPER WINDOW — ADAPTER + FILTERS PROBE PROMPT
## (paste into circuit builder / AI agent)

## 0. GUARDRAIL (do not skip)
- **This run is observation only. No trades executed.**
- Paper-only framing: no live trades, no real capital, no live Grok Bot workshop,
  no live exchange writes. Zero-burn hard stop.
- Run against the FROZEN 60-candidate pump.dev-format pool (commit 084334d freeze-locked).
  Pool read-only on disk: `pumpfun_phase2_adapter_ext_run.py` → `pumpfun_candidate_pool()`.
- Do not call any live API. All data is from the local frozen pool only.
- Engine (verified fixed gate):
    qualified <=> (buy votes >= CONSENSUS_MIN) AND (|combined_score| >= SIGNAL_GATE)
  with engine module-level params CONSENSUS_MIN / SIGNAL_GATE (set BEFORE each variant); a
  green narrative clears the liquidity tag, and a non-green narrative with
  liq < vol*2 is tagged `hidden_liquidity`.
- Voters: 5 heuristic bots + 3 volume-momentum clones (frozen `build_voters()`).

## 1. WIRING (verified path — do not change)
- Load adapter module from disk:
    adapter = load `pumpfun_phase2_adapter_ext_run.py` via importlib
- Engine call path (exact, from frozen round-12 probe):
    `engine_consensus(adapter.to_engine_pair(p), narrative="")` per candidate
  (engine-level CONSENSUS_MIN / SIGNAL_GATE), NOT a direct `vote()` on raw pump.dev dicts.
- Per candidate output (verbatim template — one block per candidate):
    stand-down  {name:14} consent={agree}/{floor} score={combined_score:+.3f} tag={tag}
  or, if qualified:
    >>> qualified {name:14} consent={agree}/{floor} score={combined_score:+.3f} tag={tag}

## 2. FILTER FLOORS (variants, run in this order)
| Variant | Label | CONSENSUS_MIN | SIGNAL_GATE |
|---|---|---|---|
| V0 | baseline engine (frozen evidence) | 8 | 0.35 |
| V1 | loose floor | 7 | 0.25 |
| V2 | looser floor (derived floor) | 6 | 0.20 |
| V3 | tight gate | 8 | 0.50 |

## 3. EXECUTION STEPS
1. Load frozen 60-candidate pool; verify 60 entries (no live API, no audience markers).
2. For each variant (V0→V3, in order):
   a. set engine module params CONSENSUS_MIN/SIGNAL_GATE;
   b. build 5+3 voters; run `engine_consensus(to_engine_pair(p), narrative="")` on all 60;
   c. emit per-candidate blocks + summary line:
      `   candidates screened : {n}   gate_qualified : {q}   stand-down: {s}`;
   d. record all stand-down reasons and qualified names into the output file.
3. Do NOT interpret, do NOT trade, do NOT push — emit only the artifacts.

## 4. OUTPUT ARTIFACTS (all local, paper, read-only)
- `round12_v2_20261115.log` style probe log — byte-identical template shown in Sec 5.
- `phase2_local_simulator.py` runs: `--probe` (full 4-section log) / `--v0..v3` / `--json`.
- Final verdict table: one row per candidate, with `qualified` bool under V2 floor 6/0.20.

## 5. VERBATIM TEMPLATE OF THE FROZEN ROUND-12 LOG (use as output schema)
```
FILTER-SENSITIVITY PROBE (observation only, zero-burn): 60 deterministic pump.dev-format candidates (offline)

== V0  baseline engine (frozen evidence) ==  CONSENSUS_MIN=8, SIGNAL_GATE=0.35
   candidates screened : 60   gate_qualified : 0   stand-down: 60
     stand-down  ApeCoin        consent=7/8 score=+0.258 tag=hidden_liquidity
     ... (one block per candidate) ...

== V1  loose floor ==  CONSENSUS_MIN=7, SIGNAL_GATE=0.25
   candidates screened : 60   gate_qualified : 15   stand-down: 45
     stand-down  Aurora         consent=3/7 score=+0.138 tag=hidden_liquidity
     >>> qualified ApeCoin      consent=7/7 score=+0.258 tag=hidden_liquidity
     ... (one block per candidate) ...

== V2  looser floor ==  CONSENSUS_MIN=6, SIGNAL_GATE=0.20
   candidates screened : 60   gate_qualified : 20   stand-down: 40
     stand-down  Aurora         consent=3/6 score=+0.138 tag=hidden_liquidity
     >>> qualified Envy         consent=7/6 score=+0.258 tag=hidden_liquidity
     ... (one block per candidate) ...

== V3  tight gate ==  CONSENSUS_MIN=8, SIGNAL_GATE=0.50
   candidates screened : 60   gate_qualified : 0   stand-down: 60
     stand-down  ApeCoin        consent=7/8 score=+0.258 tag=hidden_liquidity
     ... (one block per candidate) ...
```

## 6. STAND-DOWN POLICY (hard rules)
- Stand down any candidate with consent < CONSENSUS_MIN or |score| < SIGNAL_GATE.
- Keep `hidden_liquidity` candidates on the stand-down list — do not treat as trades.
- Roll back to the V0 baseline report if any variant runs more than 2× the frozen
  candidate count or injects live data.

## 7. DECISION MATRIX (post-run)
| Gate | Qualified (of 60) | All qualified tagged hidden_liquidity? |
|---|---|---|
| V0 8/0.35 | 0 | n/a |
| V1 7/0.25 | 15 | yes |
| V2 6/0.20 | 20 | yes |
| V3 8/0.50 | 0 | n/a |

## 8. POST-RUN
- Freeze remains closed to commits/pushes until user approval.
- Paper window: no trades, no fills, no capital at risk.
- Next step after user approval: freeze-safe lane 1 wrap + record into
  FREEZE_LOCK.md; continue ice-free lanes 2–4 on `origin/main` (clean tree).
