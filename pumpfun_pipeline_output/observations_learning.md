# pumpfun_pipeline — Run Log & Learnings (2026-11-27)

Zero-burn observation-only runs. No trades, no capital, no signing. All verdicts of
`standby` on every candidate that was scored this session.

## 1. Live pipeline — run7 (persistent state, repo artifact)

Command:
`python3 pumpfun_pipeline.py --rounds 6 --interval 1.5 --limit 33 --state pumpfun_pipeline_output/state.json`
(prerequisite: py_compile passed)

Observations (23 real live candidates re-scored, all `standby`):

```
[PIPELINE] live poll loop: rounds=6, interval=1.5s, limit=33
[STAND]  pumpfun|DEVFEES   standby << fee-resilience thin (setting-change run) ; high_fee_new ; thin ; thin_volume
[STAND]  pumpfun|Zhaki     standby << green_spot ; thin ; thin_volume
[STAND]  pumpswap|CM       standby << green_spot ; high_fee_new ; thin ; thin_volume
[STAND]  pumpfun|CM        standby << fee-resilience thin (setting-change run) ; thin ; thin_volume
[STAND]  pumpswap|MAYA     standby << hidden_liquidity ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  pumpfun|MAYA      standby << fee-resilience thin (setting-change run) ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  pumpfun|cashcat   standby << fee-resilience thin (setting-change run) ; high_fee_new ; thin ; thin_volume
[STAND]  pumpfun|Lemon     standby << fee-resilience thin (setting-change run) ; high_fee_new ; thin ; thin_volume
[STAND]  pumpswap|CI       standby << fee-resilience thin (setting-change run) ; hidden_liquidity ; thin ; thin_volume
[STAND]  pumpfun|CI        standby << fee-resilience thin (setting-change run) ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  pumpswap|MoonBoy  standby << active_volume ; fee-resilience thin (setting-change run) ; hidden_liquidity ; hype_proxy ; thin
[STAND]  meteora|MoonBoy   standby << fee-resilience thin (setting-change run) ; hidden_liquidity ; high_fee_new ; thin ; thin_volume
[STAND]  raydium|MoonBoy   standby << fee-resilience thin (setting-change run) ; high_fee_new ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  meteora|          standby << fee-resilience thin (setting-change run) ; hidden_liquidity ; high_fee_new ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  pumpfun|MoonBoy   standby << fee-resilience thin (setting-change run) ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  uniswap|MOIRA     standby << fee-resilience thin (setting-change run) ; thin ; thin_volume
[STAND]  ramses|MOIRA      standby << fee-resilience thin (setting-change run) ; high_fee_new ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  uniswap|Prodigy   standby << fee-resilience thin (setting-change run) ; high_fee_new ; rug ; thin ; thin_volume
[STAND]  pumpfun|TILLY     standby << fee-resilience thin (setting-change run) ; high_fee_new ; thin ; thin_volume
[STAND]  pumpswap|FoMo     standby << fee-resilience thin (setting-change run) ; high_fee_new ; thin ; thin_volume
[STAND]  pumpfun|FoMo      standby << fee-resilience thin (setting-change run) ; thin ; thin_volume
[STAND]  pumpswap|ZERO     standby << hidden_liquidity ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  pumpfun|ZERO      standby << fee-resilience thin (setting-change run) ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  pumpfun|SNIBBU    standby << fee-resilience thin (setting-change run) ; thin ; thin_volume
[STAND]  pumpfun|DEGENMAS  standby << fee-resilience thin (setting-change run) ; high_fee_new ; thin ; thin_volume
[STAND]  pumpswap|WINTER   standby << fee-resilience thin (setting-change run) ; thin ; thin_volume
[STAND]  pumpfun|WINTER    standby << fee-resilience thin (setting-change run) ; pump_and_dump / wash_grind signature ; rug ; thin ; thin_volume
[STAND]  uniswap|DAILY     standby << green_spot ; thin_volume
```

- The live adapter returns a nearly static 33-pair snapshot; the pipeline's dedup
  (`_seen`, key dexId|asset) finds **no new candidates for rounds 2–6** (5 rounds
  in a row, "no new candidates"). This is a property of the live snapshot rotation,
  not of the scoring engine. Practical consequence: a live desk cannot re-score
  *new* pairs until the adapter rotates/variants its fields; it can only re-score
  the same pool.
- Dominant stand-down signal family across the 23 live candidates:
  `fee-resilience thin (setting-change run)` — the wallet-as-settings signal
  dominates the pool; second family: `pump_and_dump / wash_grind signature` +
  `rug`, with `high_fee_new` and `hidden_liquidity` in support. Only 2 candidates
  lacked any fee-resilience complaint.

## 2. Filter-sensitivity probe — runB (observation only, zero-burn)

Command: `python3 pumpfun_phase2b_filterprobe.py > pumpfun_pipeline_output/runB.txt`
(deterministic frozen pump.dev-format pool, 60 candidates)

Gate knobs only, evidence frozen:

| Variant | CONSENSUS_MIN | SIGNAL_GATE | qualified | stand_down |
|---|---|---|---|---|
| V0 baseline (frozen evidence) | 8 | 0.35 | **0** | 60 |
| V1 loose floor | 7 | 0.25 | **15** | 45 |
| V2 loose floor | 6 | 0.20 | **20** | 40 |
| V3 tight gate | 8 | 0.50 | **0** | 60 |

**Learning:** the gate floor is not the cause of the flat 100% stand-down on the
frozen pool. Even with the tightest gate (V3) every candidate carries tag
`hidden_liquidity` — this pool has **no** candidate with a liquidity-resilience tag.
The structural property of the frozen pool is the tag distribution, not the floor.
Also note: several candidates passed 7/8 and even 7/7 (Nova, Vega, Syscoin, Kinetix,
Alchem, Elara, Cascade, Dune, Helios, Argent, Cols, Envy, Glint, Koda, Nyle all held
consent 7/7 or 7/8) and were STILL stand_down — the `hidden_liquidity` tag blocks
advance even at 7 of 8 votes.

## 3. Local paper-window simulator — runL

Command: `python3 phase2_local_simulator.py --probe --out pumpfun_pipeline_output/runL_probe.txt`
(before this, bare invocation printed usage: flags are --v0/--v1/--v2/--v3/--probe/--json/--pool/--out)

`--probe` executes V0+V1+V2+V3 sections over the frozen pool: 35 qualified markers in
total (0+15+20+0). The same frozen-pool finding repeats under the local simulator:
all qualified candidates are `hidden_liquidity`-tagged; no liquidity-resilient pass
exists in the pool.

## 4. Calibrated Route-C run — runC

Command: `python3 pumpfun_phase3_calibrated_run.py > pumpfun_pipeline_output/runC.txt`
Notes: exit 0; verbose paper log written to `ROUTE_C_20261127_141138.log` (129 lines).

Results:
- live   : 30 scanned, **0 qualified**, 0 trades, 0 won  (exactly replicating the
  100% stand-down pattern of the live pool — same as Phase-2 findings)
- sim    : 7 scanned, 5 qualified, 5 simulated trades (2 won), win rate 40%
- realized P&L : $-0.0676 | avg/trade $-0.0135
- exit reasons : {'STALL': 3, 'TARGET_GAIN': 2}
- zero-burn confirmed: no real trades, no capital moved.

**Learning:** with the calibrated entry gate the simulated pool finally produces
qualified candidates (5/7) and trades can execute inside the paper loop; the live
pool is the binding constraint (0/30), not the gate or the exit rules. The simulation
already exercises the full paper loop (entry → 3% risk micro-sizing → trailing → exit
rules STALL/TARGET_GAIN), so Route-C output is the highest-fidelity "learning so far"
on where the desk stands: live pool has no pass, paper pool can (2 wins on 5 trades).

## Cross-cutting summary (this session's learnings)

1. Ledger of live observation: 71 rounds across multiple runs, all candidates
   `standby`, 100% reject. The live pool has no candidate passing fee-resilience,
   thin-volume, hidden-liquidity, or pump-and-dump/wash filters.
2. Consistencies: live pipeline (run7) and frozen-pool simulator (run B/V2; run L)
   agree — the binding filter is the liquidity/fee-resilience story, not the
   5+ bot consensus count. Even high-consent (7/7–7/8) candidates stand down on
   `hidden_liquidity`.
3. Gate sensitivity: loosening CONSENSUS_MIN 8→6 at SIGNAL_GATE 0.20 triples
   pass rate on the frozen pool (0→20), but the frozen pool has no deep-liquidity
   candidates to begin with, so loosening alone cannot produce a real pass.
4. Live adapter: static 33-pair snapshot → dedup → no new candidates for 5+ rounds
   in a row. Needed: time-variant fields (a rotating field or a `since` cursor) so
   the desk can observe new live pairs instead of re-scoring the same 23.
5. Route-C is the best end-to-end evidence yet: paper pool passes (5/7, 40% win,
   −$0.0676 P&L on 5 trades), live pool does not (0/30). Next trial candidates:
   (a) fix/harden live adapter rotation, (b) re-probe live pool once the adapter
   rotates, (c) keep calibrating ONLY the live-side candidate filters.

## Artifacts produced this session (all zero-burn)

- pumpfun_pipeline_output/run7.txt — live pipeline run (23 verdicts)
- pumpfun_pipeline_output/runB.txt — filter probe (V0–V3)
- pumpfun_pipeline_output/runL.txt, runL_probe.txt — local simulator
- pumpfun_pipeline_output/runC.txt — calibrated Route-C run
- pumpfun_pipeline_output/state.json — persistent pipeline state (71 rounds)
- ROUTE_C_20261127_141138.log — Route-C verbose paper log


## 5. Grok Bot "Dark Factory" reference — X thread 2026-11-27 (newly observed)
Sources: x.com/0xg4tsby/status/2126323191446425953 (user-shared thread, with linked
full-setup article x.com/m4lkxx/status/2115775972536434946) + related @0xdav1d_k
threads (2119849153379414503, 2121294856085496092).

Grounded extract: SpaceXAI engineer Lauren Tan "fired herself" — 30+ agents run 24/7,
her job is only morning-coffee review. Grok Bot 1.0 (early Nov 2026) enables agent teams
for meetings, trading, PM, ops. 6-seat structure: CHIEF → OPS → CHECKER → 2×SPECIALIST
→ MISC, with routines, description-as-job, board DB, clock (standup), and a 10-min
background-approval expiry trap. Usage exports: 75–88% of tokens go to bots re-reading
old chat; ~1% to real work; 3 bill cuts before building anything.

Desk relevance (verified by this desk's own runs):
1. 24/7 scheduler mirrors the desk loop — runs with the tab closed (verified runs exit 0).
2. CHIEF→OPS→CHECKER→SPECIALIST hierarchy mirrors the 5+ bot consensus + stand-down
   tags + exit gate of pumpfun_pipeline.py.
3. 75% re-read = desk cost ceiling: the simulator must stay deterministic; no rebuilding
   of scored candidates per chat.
4. Gate pattern mirrors paper-only posture: "verify before trust / irreversible first."

Paper window only: no live trades, no external publication, no approval. ## Artifacts
produced this session (all zero-burn) + reference
- pumpfun_pipeline_output/X_REF_GROK_DARK_FACTORY.md (this record)
- pumpfun_pipeline_output/observations_learning.md (section 5 appended)
- pumpfun_pipeline_output/run7.txt, runB.txt, runL.txt, runL_probe.txt, runC.txt
- state.json (71 rounds), ROUTE_C_20261127_141138.log
