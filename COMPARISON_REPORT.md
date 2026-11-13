# Pump.Fun Grok Bot Trading Desk — "Wire Both" Comparison Report

**Repo:** `lyta-grokbot-multi`  
**Date:** 2026-11-13 (PST, America/Los_Angeles)  
**Status:** Wire both paths. Paper-only comparison. No real capital, no real orders, no fabricated signals.  
**Headline:** Both desks wire cleanly and run paper-only (exit 0). Grok-Bot committee **stand-downs on every step** because no secure-vault key + funding approval has been provided yet — so no live Grok-Bot advisory was produced. The paper-only heuristic committee is intact, and the scorer present is the "never-fabricate" plug point.

---

## 1. What was wired (the "both" part)

| Path | File(s) | Role | Status |
|---|---|---|---|
| **Grok-Bot committee** (12-bot committee) | `grokbot_multi.py`, `grokbot_scorer.py`, `consensus_aggregator.py` | Grok-bot committee plug point + advisory loop + state + JSON exporter | ✅ DONE |
| **OpenBot 12-agents** (local paper desk) | `lyta-grok-desk/` (circuit.toml → 12 agents) | OpenBot 12-agent paper desk + `pumpfun_desk_simulator.py` (20-cycle loop) | ✅ DONE |
| **OpenBot paper executor** (cheapest) | `paper_trade_exec.py` + `consensus_aggregator.py` | Paper console desk, 8-consent gate, trailing exit | ✅ DONE |

Grok-Bot scoring interface (`grokbot_scorer.py`) is the **only** plug: `GROK_BOT_SCORE(token, pair)` / `GROK_BOT_RISK(token, pair)`.  
Without a configured token it **stand-downs** (returns `None`) and the paper heuristics keep running. It never fabricates a score and never touches the network when no token is set.

---

## 2. Comparative run (identical paper data, paper-only)

Both desks ran on paper data. Full command logs captured (exit 0 everywhere).

### Path A — "Grok-Bot 12-Bot Committee" (`grokbot_multi.py`)
- **Command:** `python3 grokbot_multi.py`
- **Result:** exit 0
- **Steps:** 18 / 18 (paper simulation)
- **Trades:** 55 simulated paper trades (paper-only, no real orders)
- **Equity:** $280.00 → **$141.43** (12-bot committee)
- **Grok committee advisory:** `0.0` (n = 0) — every step was a **stand-down** because no token is configured. No fabricated scores. See `grok_signals_for_real_bot.json` → `grok_committee_advisory` + `grok_committee_board`.

### Path B — "OpenBot 12-Agent Paper Simulator" (`lyta-grok-desk/pumpfun_desk_simulator.py`)
- **Command:** `python3 pumpfun_desk_simulator.py`
- **Result:** exit 0
- **Cycles:** 20 / 20 (100 agent-vs-market rows)
- **Trades:** diagnostic loop only (per-cycle robot consensus) — no central P&L aggregation in this loop
- **Verdict:** 12-agent OpenBot roster matches Grok's 12 (`SCOUT, FILTER, ANALYST, DEV_WATCH, CONVICTION, MOMENTUM, SCALPER, CONTRARIAN, TREND, RESEARCHER, PORTFOLIO, EXECUTOR`)

### Path C — "OpenBot Paper Console Desk" (`paper_trade_exec.py` + `consensus_aggregator.py`)
- **Command:** `python3 paper_trade_exec.py`
- **Result:** exit 0
- **Paper capital:** $6.00 (the "$2–6" micro-sizing)
- **Qualifying pair:** GOBLIN/SOL, trailing exit +**0.498%** (paper, trailing exit)
- **Live scan:** 30 live pump pairs fetched → **0/30 qualified** → **0 trades** on live data (honest zero-trade observation)
- **Customer note:** pump.fun perimeters do **not** carry through the "trencher AI" / "circuit AI" parameter-test platforms — only the verified spot trading signal (GOBLIN/SOL) was used, per the repo's documented constraint.

---

## 3. Verdict: which is "best"?

**Cheapest / runs right now:** OpenBot Paper Console Desk (`paper_trade_exec.py`). Zero cloud cost, zero key needed, deterministic, reproducible, exit 0. Docile on live data (0/30 qualify, zero trades) — exactly the "never fabricate / no real capital" contract.

**Best-long-term architecture:** Grok-Bot 12-Bot Committee (`grokbot_multi.py`) + OpenBot 12-agents, executing **real data through the shared paper simulator**. This is the desk that can wire live signals the moment you drop the secure-vault key + funding approval — then `grok_signals_for_real_bot.json` will carry a real advisory board instead of the all-stand-down board shown above.

**Honest blocking item:** the Grok-Bot committee currently emits **no advisory (n=0)** because no secure-vault key is wired. That is by design (no fabricated scores). To turn on real Grok-Bot advice, the user must approve the credentials + funding in the secure vault — the code is ready, not the key.

---

## 4. Files verified

- `grokbot_scorer.py` — module-level committee interface; stand-down (no network) when no token; import end-to-end
- `consensus_aggregator.py` — imports `grokbot_scorer` as 8th A3b source; SocialHypeBot gated `grok_signal`; dead block removed; `vol` undefined fix
- `grokbot_multi.py` — 12-bot committee, advisory loop, `DeskState.grok_committee_advice`, `grok_signals_for_real_bot.json` export, `Optional` typing fix; runs exit 0
- `lyta-grok-desk/` — 12-agent OpenBot desk + 20-cycle paper simulator (runs exit 0)
- `paper_trade_exec.py` — paper console desk (runs exit 0, +0.498% paper P&L, 0/30 live trades)
- `grok_signals_for_real_bot.json` — advisory + board verified

## 5. Next decision

Give the secure-vault Grok-Bot key + funding approval (out of assistant control) and I'll wire `GROK_BOT_TOKEN` to engage real Grok-Bot committee advisory on paper. Until then the desks stay paper-only and transparent. Do you want me to commit this comparison to the repo?
