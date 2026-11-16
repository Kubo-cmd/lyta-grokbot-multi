# PAPER COMPARE — Adapter Extension vs Route B (pump.fun Phase 2)

**Status: observation only · zero trades · zero burn** (paper freeze applies)
**Date:** 2026-11-15 · **Workspace:** `/Users/test/projects/lyta-grokbot-multi` (private remote `origin`)

---

## 1. Runs compared

| | **Adapter extension run** | **Route B evidence rounds** |
|---|---|---|
| Script | `pumpfun_phase2_adapter_ext_run.py` | `pumpfun_phase2_pumpfun_run.py` (route2 log, route B) |
| Date | 2026-11-15 16:24 | 2026-11-15 15:07 (selected run) |
| How candidates came in | 6 deterministic **pump.dev-format** payloads (offline, synthetic) via `PumpFunDataAdapter.adapt()` | 89 live pairs from Route B evidence rounds R4–R6 |
| Read-only cross-check | DexScreener pump pull attempted; result had no `name`, pool-only used (honest offline warning, no charge) | live pump.fun feed |
| Gate | 8-vote A3b (5 heuristic + 3 volume clones), consensus_min=8, \|score\|>=0.35 | 8-vote A3b (5+ bot consensus), same thresholds |
| Observation banner | ✅ present ("This run is observation only. No trades executed.") | ✅ present |
| Zero-burn note | ✅ present | ✅ present |

## 2. Totals

| metric | adapter extension run | route B evidence |
|---|---|---|
| candidates screened | **6** | **89** |
| gate qualified | **0** | **0** |
| paper executed | **0** | **0** |
| paper trades | **0** | **0** |
| paper P&L | **$0.00** | **$0.00** |
| paper capital held | $6.00 | $100.00 |
| stand-down reasons | 5 × `consensus_min; signal_gate; tag=hidden_liquidity`<br>1 × `consensus_min; signal_gate` | 50 × no-vote (`-`)<br>39 × `hidden_liquidity` |
| votes printed to console | 48 (8 per candidate × 6) | — |

## 3. Rejection-gate analysis

- **Both runs:** the 8-vote A3b gate rejected 100% of candidates.
- **Adapter-extension run:** scores 0.01–0.26 against the 0.35 signal gate; all 6 tagged `hidden_liquidity`; consent 1/8–7/8. No `base/quote` naming hazard on the 7th live cross-check candidate (pool-only guard applied).
- **Route B evidence:** 50 rows with zero votes, 39 rows blocked with `hidden_liquidity`; every decision was `standby`.
- **Consensus pattern:** no candidate reached 8/8 consent with \|score\|\>=0.35 in either run — the common rejection mechanism is consensus_min + signal_gate + hidden_liquidity.

## 4. Realized results

| | adapter extension run | route B evidence |
|---|---|---|
| closed positions | 0 | 0 |
| exit reasons | none (no fills) | none (no fills) |
| realized P&L | $0.00 | $0.00 |
| burn | $0.00 (0 live trades, no wallet, no signing, no exchange writes) | $0.00 |

## 5. Verdict

- **Lane 2 (adapter path extension) — VERIFIED CLEAN.** `python3 -m py_compile` → OK; full run exit code **0**; per-position CLOSE logs printed as `(none — zero paper fills; all 6 candidates stood down)`; observation banner + zero-burn banner + summary + `*.log` trace all present.
- **Lane 3 (comparison) — READY.** Gate behaviour is now compared side-by-side (adapter extension vs route B), and the paper-only guardrail (no live capital, no trades) held in both runs.
- **Decision:** the adapter path is exercised end-to-end; the paper evidence so far shows 100% stand-down on live + format candidates, so the next step is gathering **20+ paper positions** before any fine-tuning (PAPER_COMPLETE.md "Next"): freeze MIN_LIQ $50k→$20k **only if** more trades are needed.

---

*End of comparison report. Observation only — no trade executed.*
