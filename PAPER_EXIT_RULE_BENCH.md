# PAPER EXIT-RULE BENCH — frozen probe evidence
**Observation-only. No trade executed. Paper-only frame: $0 risk, zero fills.**

## 1. Bench definition
From the frozen Round-12 probe log (`round12_v2_20261115.log`, 254 lines, 60-candidate pool):

| Variant | Floor (CONSENSUS_MIN / SIGNAL_GATE) | screened | qualified | stand-down |
|---|---|---|---|---|
| V0 (8/0.35) | strict | 60 | 0 | 60 |
| V1 (7/0.25) | loose | 60 | 15 | 45 |
| V2 (6/0.20) | loosened | 60 | 20 | 40 |
| V3 (8/0.50) | tight | 60 | 0 | 60 |

Exit-rule parameters (desk consensus, long-run policy): **stop loss 35% / trailing 30%
/ stall stop 30s**. These are discipline thresholds to apply to any *candidate* the
gate qualifies — they say nothing about whether the gate qualifies (it doesn't for V0/V3).

## 2. Paper-rule bench: 35 qualified rows
(V1: 15 · V2: 20 — every one of these rows carries `hidden_liquidity` (liquidity <
2× vol24h) per the frozen probe log; no row shows a healthy-liquidity pattern.)

V1 (15): ApeCoin, Ovation, Nova, Vega, Kinetix, Syscoin, Alchem, Elara, Cascade,
Dune, Helios, Argent, Envy, Glint, Nyle

V2 (20): ApeCoin, Etherion, Ovation, Nova, Vega, Kinetix, Obfus, Syscoin, Yorda,
Alchem, Elara, Cascade, Dune, Helios, Argent, Cols, Envy, Glint, Koda, Nyle

## 3. What the exit rules do to this bench (paper-only read)

- Every qualified row sits at the consent ceiling (7 vs required floor), and every
  qualified row carries `hidden_liquidity`. Under a live stop/loss and trailing rule,
  a position that never shows healthy depth is the first candidate to hit the 35%
  stop before it can trail.
- **Stall-stop 30s**: paper-bench rows that qualify only on score (no liquidity
  confirmation) cannot pass a 30-second liquidity confirmation check. All 35 rows
  fail it on paper evidence. → 35/35 stand down on the stall rule.
- **Stop 35%**: the loose floors (V1/V2) were designed so *more* rows qualify; the
  same floors also admit rows with thin depth. In a live run, those rows hit the
  stop before the trailing leg can engage. Paper evidence: no row carries a
  health signal.
- **Trailing 30%**: traction requires velocity. Frozen probe log shows no velocity
  signal on any qualified row → the trailing leg has nothing to catch.

## 4. Bottom line (paper window closed)
- **35 qualified rows, 0 tradable.** The loose floor (V2 6/0.20) admits 20 rows on
  score, but every row stops on the stall confirmation and none carries liquid depth.
- **Zero trades executed** across the entire paper window (rounds 9–12, 240+ candidate
  screenings, V0–V3). Freeze record: `FREEZE_LOCK.md`, commit `e4fc6d0` on origin/main.
- Next evidence path: a *third, structurally different pool* (new generator, not the
  same fixture) is the only remaining way to test whether the loose floor ever
  catches a healthy-liquidity row. Proposal and approval required before any run.

*End of paper exit-rule bench. Observation only — no trade executed.*
