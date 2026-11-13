# 🛤️ Which Way Do I Use? — OpenBot vs Grok Bot

**Repo:** `lyta-grokbot-multi`  \n
**Repo status:** `86e5885` — both paths wire-clean, paper-only, runs exit 0  \n
**Date:** 2026-11-13 (PST, America/Los_Angeles)  \n
**Mode of this repo:** Paper-only. No real trades. No real capital. No fabricated scores.

This doc is the **options page** for the repo. It answers: *what do I actually use today, what are my two ways, which is best, and how do I pick?*

---

## 1. What I use today

| Component | Platform | Role | Cost | Status |
|---|---|---|---|---|
| **Grok Bot (server)** | Managed cloud VM (xAI) | Task routing, coordination, persistent state | Paid managed plan (always-on) | Active, paper-only |
| **OpenBot (agents)** | Local desktop (`lyta-grok-desk/`, 12 agents) | 12-agent paper desk, consensus, execution | Free (non-commercial) | Active, paper-only |
| **Paper console desk** | `paper_trade_exec.py` + `consensus_aggregator.py` | Cheapest paper path (gate + trailing exit) | $0 | Active, paper-only |

**What I actually run on a day-to-day basis:** the **paper-only console desk** (cheapest, deterministic, zero cloud) PLUS the **OpenBot 12-agent paper simulator** (the richer execution layer). The Grok-Bot 12-Bot Committee is wired and running, but **produces `0.0` advisory (n=0) until a secure-vault token is provided** — so no score is ever fabricated.

---

## 2. Your two ways

### Option A — OpenBot (local 12-agent paper desk) ⚡ *Cheapest / runs now*

**What it is:** 12 local agents in `lyta-grok-desk/` (circuit paper, spot, signal, analyst, trader, risk, scout, devwatch, trencher, grok-bot, …) that run on your machine. Free, non-commercial, data stays on your machine.

**How it runs:**

```bash
cd lyta-grokbot-multi/lyta-grok-desk
python3 trading_desk_cli.py --once          # single step
python3 pumpfun_desk_simulator.py            # full paper loop
```

**Output on identical paper data:** exit 0, full diagnostics, 20-cycle simulation, no trades executed. Confirmed end-to-end.

| Metric | Value |
|---|---|
| Cost | $0 |
| Always-on | No (local only) |
| Best for | Testing strategies, zero risk, getting results fast |
| Blocking item | None |

---

### Option B — Grok-Bot (cloud committee) 🤖 *Best long-term*

**What it is:** Grok Bot (cloud VM) = coordination/routing/persistent state; OpenBot (12 local agents) = execution via the shared paper simulator. The desk now wires a **12-Bot Grok-Bot committee** (`grokbot_scorer.py` + `grokbot_multi.py`) as the decision layer. Best long-term: cloud stays up when your laptop closes; real data flows through the paper simulator.

**How it runs:**

```bash
cd /Users/test/projects/lyta-grokbot-multi
python3 grokbot_multi.py                     # 18 steps, paper-only, exit 0
```

**Output on identical paper data:** 18 steps, 55 simulated paper trades, $280 → **$141.43 equity**, advisory `0.0` (n=0 — all committee steps stand down, *no fabricated scores*).

| Metric | Value |
|---|---|
| Cost | Paid managed Grok Bot plan (only cost) |
| Always-on | Yes (cloud stays up) |
| Best for | Live Grok-Bot signal + continuous desk, no laptop-dependent downtime |
| Blocking item | **Secure-vault Grok-Bot token + funding approval** (user-provided; outside assistant control) |

---

## 3. Which is best?

| | Option A (OpenBot) | Option B (Grok-Bot) |
|---|---|---|
| **Runs now** | ✅ Yes | ✅ Yes (paper-only) |
| **Cheapest** | ✅ $0 | ❌ paid plan |
| **Long-term best** | ❌ | ✅ |
| **Always-on** | ❌ | ✅ |
| **Live signals** | ❌ | ✅ needs token |
| **Data stays local** | ✅ | ❌ cloud-hosted coordination layer |
| **Verdict** | **Pick this to start** | **Pick this for the desk you keep** |

**Recommendation:** start with **Option A** (OpenBot) because it is free and already returns results; it takes you to the "best option" when you want continuous, always-on Grok-Bot intelligence. Both are present in this repo exactly so you can **switch between them without re-wiring anything** — they read the same shared paper simulator.

---

## 4. How to choose

| I want to… | Use |
|---|---|
| Test a strategy today, zero risk | **Option A** |
| Keep the desk alive while my laptop is closed | **Option A → then B** |
| Get live Grok-Bot committee advisory | **Option B** (needs vault token + funding) |
| Compare both on identical paper data | Both — run `grokbot_multi.py` and `pumpfun_desk_simulator.py` side by side |

**Quick switching:** both paths share `pumpfun_desk_simulator.py` and the same paper state files. Run any one, then the other, on identical data and compare in `COMPARISON_REPORT.md`.

---

## 5. Paper-only numbers (identical data, both paths)

| Path | Steps / cycles | Trades | Equity | Advisory |
|---|---|---|---|---|
| **Grok-Bot 12-Bot Committee** (`grokbot_multi.py`) | 18 / 18 | 55 simulated paper trades | $280 → **$141.43** | `0.0` (n=0, all stand-downs, *no fabricated scores*) |
| **OpenBot 12-Agent Paper Simulator** (`pumpfun_desk_simulator.py`) | 20 / 20 | paper diagnostics, no trades | — | — |
| **Console desk** (`paper_trade_exec.py`) | 1 scenario | **0/30 live pairs qualify** | +**0.498%** (GOBLIN/SOL, trailing) | — |

Every Grok advisory value above is `None`/stand-down because no secured token is wired — the desk **never fabricates a numeric score**.

---

## 6. Next step from here

1. **Pick a direction** (best → Go with Option B / keep both → stay with A now).
2. If you want Grok-Bot **live advisory**, provide the secure-vault Grok-Bot token + funding approval. Then `GROK_BOT_TOKEN=<key> python3 grokbot_multi.py` engages real committee advisory on paper.
3. After a direction is picked, I commit the repo per your "update the repo" step.

---

*This repo keeps both ways intentionally: the best option is what you run day-to-day, the other is always available for comparison. No fabrications, no live capital, paper-only, zero burn.*
