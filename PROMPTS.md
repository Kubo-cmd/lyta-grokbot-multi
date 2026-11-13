# PROMPTS.md — Ready-to-Paste Prompt Templates

Copy‑paste these to run the trading desk **paper-only** on a parameter-testing
platform (trencher AI / circuit AI — neutral test surfaces) or a local
simulator. Both templates replicate the exact spec and committed code
(`consensus_aggregator.py` + `paper_trade_exec.py`).

- **No real orders, no wallet, no signing, no real capital.** Live DEX spot
  data is real; execution is simulated on paper.
- **Gate:** \|signal\| ≥ 0.35 **AND** consent ≥ 8 → paper fill. Else stand down.
- **Sizing:** `PAPER_CAPITAL=6.0`, `BUY_SIZE=0.05` SOL (PO_BNavy), `PO_STOP_LOSS=0.82`
  (trigger-only), `PO_TRAIL_DD=0.15`, `PO_STALE=90`, `PO_DEAD=240`.
- **One paper trade per qualified signal, then re-gate.** No over-trading.

---

## Template A — Parameter-testing platform (Trencher AI / Circuit AI / Builder)

> Use this prompt verbatim on any parameter-testing platform to run the paper-only
> desk over a grid of parameter sets, using real DEX spot pairs only.
> Trenchher AI / Circuit AI are neutral test surfaces: no special reliability
> assumptions; spot-only data feeds are trusted.

```text
You are running the LYTA paper-only trading desk on a parameter-testing
surface (Trencher AI / Circuit AI / any Builder). Zero real capital, zero
real orders, zero live execution. Live DEX spot pairs ARE real data; everything
else is a transparent paper proxy of the Grok-bot committee.

SPEC (replicate exactly):
- Data: real pairs only via real_trade_feed.py (DexScreener REST + PumpDev WS).
  Pump.fun metrics are NOT trusted on this surface; spot-only feeds are used.
- Gate (A3b, 8-vote floor): 5 distinct paper bots + 3 momentum copies.
  |score| >= 0.35 AND consent >= 8  ->  QUALIFIED BUY (paper fill)
  Else  ->  STAND-DOWN, log the reason (thin data / low confidence / red flag).
- Paper sizing: PAPER_CAPITAL=6.0; BUY_SIZE=0.05 SOL; PO_STOP_LOSS=0.82
  (trigger-only); PO_TRAIL_DD=0.15; PO_STALE=90; PO_DEAD=240; PAPER_TICK=1.0.
- Execution: one paper trade per qualified signal, then re-gate.

RUNNER:
1. Fetch the live pump pairs (expect 30).
2. Score each pair through the 8-bot gate; print every vote and stand-down
   reason. Verbose.
3. Classify: STAND-DOWN or QUALIFIED-BUY. Today expect 0/30 qualify.
4. On QUALIFIED-BUY: paper fill ONLY (simulated). On stand-down: no fill.
5. Verify: python3 -m py_compile + both scanners exit 0; no secrets; README
   reads back exactly what runs.

OUTPUT: table with pair_id, base/quote, consent, score, tag, decision,
stand-down reason. Then a summary: N/30 qualify, 0 trades.
```

---

## Template B — Local simulator (replicates the spec exactly)

> Use this prompt to run the local simulator that exactly replicates the
> committed spec. It exercises the A3b gate and the paper-only execution
> layer, and must produce the same result classes as the committed code.

```text
You are the LYTA paper-only trading desk simulator, running automatically.
You must reproduce the EXACT committed behavior of consensus_aggregator.py
and paper_trade_exec.py. Zero real capital, zero real orders.

SPEC (hard constraints, do not change):
- Gate (A3b 8-vote): 5 distinct bots + 3 momentum copies.
  |score| >= 0.35 AND consent >= 8  ->  QUALIFIED-BUY (paper fill only)
  Else  ->  STAND-DOWN (thin data / low confidence / red flag / stale).
- Paper sizing: PAPER_CAPITAL=6.0; BUY_SIZE=0.05 SOL; PO_STOP_LOSS=0.82
  (trigger-only); PO_TRAIL_DD=0.15; PO_STALE=90; PO_DEAD=240; PAPER_TICK=1.0.
- Data: real DEX spot pairs via real_trade_feed.py only. Paper constructions
  (e.g., GOBLIN/SOL scenario) are EXPLICITLY LABELED paper-only, not live fills.
- Data policy: trencher AI / circuit AI are neutral parameter-test surfaces.
  Trust ONLY real DEX spot feedback.

SCENARIOS to run, in order:
1. run_live: fetch the live pump pairs and gate each one. Expect 0/30 qualify,
   0 trades, all stand-down. Print every vote + stand-down reason.
2. run_realistic: built-in qualifying scenario (8/8 consent, green spot
   narrative) -> paper fill enters -> drift through the trailing rule.
   Expect entry->peak->sell-off below 85% of peak->trailing exit. Label the
   final P&L as paper-only. Today full output (tail -20):
     - real pair scans: 30, all standby, zero qualify
     - scenario pair: GOBLIN/SOL 8/8 buy (simulated) entry 0.0287 SOL
     - [paper-simulated] exit_reason=trailing exit, exit_price=0.0436
     - [paper] P&L +0.498% on paper pair live-GOBLIN/SOL
     - PAPER P&L: +0.498%   reason=trailing exit

VERIFY & REPORT:
- python3 -m py_compile paper_trade_exec.py  (expect COMPILE OK, exit 0)
- python3 pumpfun_phase2_paper_run.py      (expect 0 of 30 qualify, zero trades)
- python3 consensus_aggregator.py          (expect gate stand-down + BUY demo)
- git status --short (expect clean)
- Secret scan returns no real credentials.

Report: number of live pairs scanned, number that qualified, number of trades
executed (must be 0), and the exit reason + P&L for the constructed scenario.
Be transparent: mark every number as either live-data-derived or a documented
paper construction.
```

---

## Template C — Paper-only live→paper execution driver

> Use this prompt to wire a real live pair through the gate and simulate the
> trade on paper only, for a single pair.

```text
WIRING TEMPLATE (paper-only):
1. Real pair from real_trade_feed.py (live DEX spot), e.g. base="GOBLIN",
   quote="SOL", price_usd=0.0287, vol24_usd=3_000_000,
   liquidity_usd=4_000_000, fee=0.002, age_minutes=60.
2. ConsensusAggregator(augmented, narrative="green") -> decide_pair().
3. If decision == BUY-SIG (consent >= 8 AND |score| >= 0.35):
      enter_live_pair() -> paper fill at entry_price, size = BUY_SIZE (0.05 SOL).
      drift_to_exit() -> paper trajectory: ramp -> peak -> sell-off below
      85% of peak -> trailing exit (PO_TRAIL_DD=0.15).
      Result: exit_reason, exit_price, pnl_pct. LABEL AS PAPER ONLY.
   Else:
      Print "stands down: consent=<c>/8 score=<s> tag=<t> -> <decision>".
      No fill. No order.

Note: today's live pairs never reach 8/8 consent, so live runs stand down.
      The GOBLIN/SOL pair above is a documented paper construction, NOT a live
      fill. No real wallet, no real DEX, no real mint.
```

---

## Template D — Two ways to choose (runs paper-only, no capital)

> Use these one-liners to run **way A** (OpenBot local desk) or **way B** (Grok-Bot cloud committee). Both are paper-only and read the same shared simulator. Pick the way above: run A today, move to B when you want always-on Grok-Bot advisory (needs a vault token + funding, outside assistant control).

### (A) OpenBot — local 12-agent paper desk (cheapest, runs now)

```bash
# single paper step
cd /Users/test/projects/lyta-grokbot-multi/lyta-grok-desk
python3 trading_desk_cli.py --once

# full paper loop (20 cycles, local 12 agents)
cd /Users/test/projects/lyta-grokbot-multi/lyta-grok-desk
python3 pumpfun_desk_simulator.py
```

- **What it runs:** 12 local OpenBot agents (circuit paper, spot, signal, analyst, trader, risk, scout, devwatch, trencher, grok-bot, …) via `lyta-grok-desk/circuit.toml` (`paper_only = true`).
- **Cost:** $0. **Always-on:** No (local only).
- **Today's result:** exit 0, full diagnostics, 20-cycle run; both desks verified on real paper data.

### (B) Grok-Bot — cloud committee + OpenBot execution (best long-term)

```bash
cd /Users/test/projects/lyta-grokbot-multi
python3 grokbot_multi.py            # paper-only Grok-Bot committee, exit 0
```

- **What it runs:** the 12-Bot Grok-Bot committee (`grokbot_scorer.py` plug point, `grokbot_multi.py` advisory loop, `DeskState.grok_committee_advice`, `grok_signals_for_real_bot.json` export). Reads the shared `pumpfun_desk_simulator.py` paper simulator for execution.
- **Cost:** Paid managed Grok-Bot plan. **Always-on:** Yes (cloud stays up). **Live advisory:** needs a secure-vault `GROK_BOT_TOKEN` + funding approval (outside assistant control).
- **Today's result:** 18 steps, 55 simulated paper trades, $280 → **$141.43 equity**, advisory `0.0` (n=0 — every committee step stand-down, *no fabricated scores*).

### Which one to run?

| I want to… | Run |
|---|---|
| Test a strategy today, zero risk | **(A) OpenBot** — `python3 pumpfun_desk_simulator.py` |
| Keep the desk alive with my laptop closed | **(B) Grok-Bot** — `python3 grokbot_multi.py` |
| Get live Grok-Bot advisory | **(B)** (add your vault token + funding) |
| Compare both on identical data | **(A)** then **(B)**, read them side by side in `COMPARISON_REPORT.md` |

**Note:** both ways are paper-only here. No real orders, no real capital, no fabricated scores. Switch between them with one command — the shared simulator state is identical.
