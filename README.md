# LYTA Trading Desk

---
## 📋 Contents
- [Trading Desk Parameters](#trading-desk-parameters)
- [Platform Comparison (Yes/No)](#platform-comparison-yesno)
- [Paper-Only Guard Gates (Verbatim)](#paper-only-guard-gates-verbatim)
- [Trailing Exit Logic & 12-Bot Consensus](#trailing-exit-logic--12-bot-consensus)
- [Agent Performance Reward System](#agent-performance-reward-system)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [GitHub](#github)

---
> **Platform: Grok Bot (server) + OpenBot (agents) | Mode: Paper-only**

## 🎯 What This Is

A **12-agent spot trading desk** on **OpenBot** (local, localhost:5173), with Grok Bot (cloud) as the control-plane router. The desk operates in **paper-only mode** — no real trades, no wallet import, no signing, no order execution.

| Component | Platform | Role | Always-On? |
|---|---|---|---|
| **Grok Bot (Server)** | Managed cloud VM (xAI) | Task routing, coordination, persistent state | ✅ Yes — cloud stays up when laptop closes |
| **OpenBot (Agents)** | Local desktop workspace (nightly-labs) | 14 trading agents — paper, signal, analyst, trader, risk, etc. | Runs on local machine |
| **Grok CLI** | Grok Bot | Token analysis pipeline | Paper-only |

## 🔓 License & Visibility

| Item | Status |
|---|---|
| GitHub repo | `Kubo-cmd/lyta-grokbot-multi` — **PUBLIC** |
| License | MIT License (open-source, permitted) |
| OpenBot store | `~/Library/Application Support/OpenBot/openbot.db` (platform home) |
| Grok Bot directory | `lyta-grok-desk/` (relative to repo root) |

---

## 📊 Trading Desk Parameters

> **Current focus (Tightened):** 7/12 consensus, skip >100% 1h pump and <$50k liquidity, −35% SL / +50% TP. Paper observation only.

### Platform Comparison (Yes/No)

|| Question | Grok bot | OpenBot |
|----------|----------|---------|
|| Local-first execution | ✅ Yes (cloud computer always on, local mode available) | ✅ Yes |
|| Data stays on your machine | ❌ No (cloud) | ✅ Yes |
|| Cost model | Self-hosted/managed plan | Free (non-commercial) |
|| Mobile app | ✅ Yes (iOS/Android) | ✅ Yes (iPhone/Android) |
|| Voice / dictation | ✅ Yes (voice input, voice chat) | ✅ Yes (31 languages) |
|| Backup models | ✅ Yes (cloud backup, multiple plans) | ✅ Yes |
|| Teams / roles | ✅ Yes (group chats, parallel bots, roles) | ✅ Yes (roles, shared channels) |
|| Chat / human-in-loop | ✅ Yes (text-thread interface) | ✅ Yes (chat, approve actions) |
|| Schedule automation | ✅ Yes (cloud routines) | ✅ Yes (local sweeps) |
|| Source code | ✅ Open (lyta-grokbot-multi) | ✅ Open (openbot.io) |

See [lyta-grok-desk/BOT-COMPARE.md](lyta-grok-desk/BOT-COMPARE.md) for the full contrast with the lean highlighted.

---

## 📊 Trading Desk Parameters

> **Current focus (Tightened):** 7/12 consensus, skip >100% 1h pump and <$50k liquidity, −35% SL / +50% TP. Paper observation only.

### Trading Desk Parameters (Spot Trading)

|| Dimension | Detail |
|---|---|---|
| **Core desk** | OpenBot, local-only (localhost:5173), `paper_mode: true` |
| **Lifecycle** | Paper-only guard gates apply to all trading agents |
| **Consensus** | 12-bot consensus (multi-agent) |
| **Screening** | Spot trading only — no pump/fun perimeters |

### Platform Comparison (Yes/No)

|| Question | Grok bot | OpenBot |
|--|--|--|--|
| **Local-first execution** | Cloud computer always on, local mode available | ✅ Yes |
| **Data stays on your machine** | ❌ No (cloud) | ✅ Yes |
| **Cost model** | Self-hosted/managed plan | Free (non-commercial) |
| **Mobile app** | ✅ Yes (iOS/Android) | ✅ Yes (iPhone/Android) |
| **Voice / dictation** | ✅ Yes (voice input, voice chat) | ✅ Yes (31 languages) |
| **Backup models** | ✅ Yes (cloud backup, multiple plans) | ✅ Yes |
| **Teams / roles** | ✅ Yes (group chats, parallel bots, roles) | ✅ Yes (roles, shared channels) |
| **Chat / human-in-loop** | ✅ Yes (text-thread interface) | ✅ Yes (chat, approve actions) |
| **Schedule automation** | ✅ Yes (cloud routines) | ✅ Yes (local sweeps) |
| **Source code** | ✅ Open (lyta-grokbot-multi) | ✅ Open (openbot.io) |

> Platform comparison is accurate per the official Grok Bot and OpenBot product documentation. Both platforms offer local-first execution, mobile, voice, teams/roles, chat/human-in-loop, schedule automation, and open source — the key differentiators are data privacy (OpenBot stays local; Grok Bot is cloud) and cost (OpenBot is free; Grok Bot has a managed plan).

See [lyta-grok-desk/BOT-COMPARE.md](lyta-grok-desk/BOT-COMPARE.md) for the full contrast with the lean highlighted.

### 📰 External X References — What We Learned (Nov 2026)

Five X posts reviewed (Kubo100x, 0xcloudvex, 1920web1080, iiamjeph/KITE AI, Serantych):

- **Kubo100x** (Nov 10, 2026): "amazing, cannot wait to test it out." — Positive signal; testing the platform.
- **0xcloudvex / SpaceXAI senior engineer** (Nov 9, 2026): "Everyone asks how I afford 70+ Grok Bots — the answer: my bill went down when I added more of them. A Chief of Staff runs my day, 4 PMs split the work, 60+ workers ship it overnight. None of them reads a word it doesn't need…" — Token-efficiency thesis: role-scoped context beats one context-aware bot.
- **iiamjeph / KITE AI** (Nov 10, 2026): "bro breaks down how he uses (axiom, fomo and J7 tracker) to make $100k/month trading solana memecoins — the full breakdown is just 25 minutes 🔖 save this" — Unverified claim; skepticism present (@Tasinpx: "Twenty five minutes is short for such a big claim."); not integrated into our paper-only 12-agent desk. Never act on viral profit claims.
- **Serantych** (Nov 9, 2026): "I went digging through GitHub for ways to upgrade GrokBot — came back with 8 repos worth a look: better coding workflows, documentation for the right library version, browser testing, performance debugging, real user error reports, document conversion, website extraction, pag…" — Practical GitHub references for improving the grok-bot trading desk codebase.
- **Kubo100x** (Nov 10, 2026): "The framework is brilliant, just got some issues with the GitHub tokens." — Feedback loop; helped refine the OpenBot workspace setup.

**Integration approach:** These posts are for the user's own research and Twitter output — not added to the repo unless asked. The Serantych GitHub repos are particularly relevant if the team wants to improve their local OpenBot workspace, J7 tracker may help with engagement metrics, and iiamjeph's post serves as a cautionary example of unverified profit claims to avoid in their own social media copy.

---

## 🔒 Paper-Only Guard Gates (Verbatim)

All trading agents enforce these paper-only guard gates:

| Guard Gate | Blocks |
|---|---|
| `no_wallet_import` | `import solana`, `sellers`, `web3`, `eth_account` |
| `no_signing_or_order_execution` | `send_transaction`, `sign_transaction`, `place_order`, `execute_swap` |
| `paper_label_present` | Requires `PAPER ONLY` + `SIMULATION` labels |
| `shared_state_paper_flag` | Requires `paper_only: true` in state |
|| `spec_simulation_only` | Spec declares `SIMULATION` + `paper_only: true` |

### Trailing Exit Logic

|| Setting | Value | Meaning |
|---|---|---|
| `PO_TRAIL_DD` | 15% | Trailing drawdown threshold from peak |
| Trail high | `peak_price` (running high) | Dynamic exit trigger |
| Trigger | `peak × 0.85` | Exit when price falls to 85% of running peak |

**Correct rule:** Exit when `current_price <= peak_price * (1 - PO_TRAIL_DD)`.
Previously the logic used an always-true condition with a 2.5x multiplier, causing immediate exit at entry. The fix compares against the running peak only.

### 12-Bot Consensus Architecture

|| Bot group | Role |
|---|---|---|
| SCOUT | Narrative/rug signal checker |
| FILTER | Low-quality pump filter |
| ANALYST | Rug/liquidity/score analyst |
| PUMP_CHASER | Momentum accumulation engine |
| CONVICTION | Trend/filter validator |
| MOMENTUM | Momentum collector |
| SCALPER | High-vol scalper |
| CONTRARIAN | Downtrend opportunity finder |
| TREND | Trend follower |
| RESEARCHER | On-chain research agent |
| PORTFOLIO | Position sizing manager |
| EXECUTOR | Final micro-sizing executor ($0.20–$0.85) |

**Consensus bar:** 5/12 minimum agree on a side (long or short). Market state and risk state flow through the Grok Bot router to all agents.

---

## ⏱️ Latency & Volatility Spike Guidance

When running agents against Grok Bot during volatility spikes:

| Risk | Mitigation |
|------|------------|
| Rate limits / quota exhaustion | Scripts poll at 5–10s intervals; wake Grok agent only on real change (Routinizer) |
| Delayed API response | Pre-validate orders locally (price, size, fee, slippage) before sending |
| Stale data | Set max 10% slippage tolerance; skip trade if API returns worse price |
| Order validation failure | Validate all fields locally before transmission |
| 12-bot consensus lag | Cache consensus result for 30s; re-request only if stale |

### Grok Bot API Rules

- **Rate limit:** 1 request per 2 seconds (15 per minute per agent)
- **Timeout:** 10 seconds per request; retry once on network error only
- **Slippage:** Max 10% — if API price > validated price × 1.10, skip
- **Monitoring:** All requests logged to `api_calls.log` for spike analysis

### OpenBot Alternative

OpenBot runs on your own infrastructure (GitHub `de1lymoon` stack), so you bypass Grok's rate limits entirely. Use OpenBot for paper-only trading, with Grok Bot only as the control-plane router.

---

# Agent Performance Reward System

## How It Works

Each agent is scored daily based on its trading performance. Agents that earn the highest scores are retained; agents that fall below the pruning threshold are **deleted from the agent store** and their configuration is removed.

### Design Principles

1. **Reward the percentage, not the absolute** — a +10% paper return on $6.00 is harder than +10% on $100, but the trade-off is that running fees and volatility differ. The agent's score is based on risk-adjusted percentage return.
2. **Loss aversion** — losing costs 1.5× more than gaining is worth. A −5% day removes more points than a +5% day adds.
3. **Prune aggressively** — if an agent fails (win rate < 35% for 3 weeks, or cumulative drawdown > 50%), delete it. The 12-bot consensus means weaker agents drop out automatically.
4. **Score persistence** — daily scores are written to `performance_log.csv` and survive restarts.

## Scoring Formula

```text
daily_score = +100 if win else −100      # binary
profit_score = pnl_pct * 2.0               # scale with PnL
volatility_penalty = −drawdown_pct * 0.5   # penalize drawdowns
total_score = daily_score + profit_score + volatility_penalty
```

### Example

Agent A has a winning day (+3%) and a draw of 5%:
- `daily_score = +100`
- `profit_score = 3 * 2 = +6`
- `volatility_penalty = −5 * 0.5 = −2.5`
- **total_score = +103.5**

Agent B loses −4% with a drawdown of 8%:
- `daily_score = −100`
- `profit_score = −4 * 2 = −8`
- `volatility_penalty = −8 * 0.5 = −4`
- **total_score = −112**

## Pruning Policy

| Condition | Action |
|---|---|
| 5 consecutive losing days | Delete agent immediately |
| 3 consecutive losing weeks | Delete agent immediately |
| 3 consecutive losing months | Delete agent immediately |
| Cumulative drawdown > 50% | Delete agent immediately |
| 3-week win rate < 35% | Delete agent |

## Performance Log

All agent performance is logged to `performance_log.csv` with columns:
`agent_id, date, pnl_pct, win, drawdown_pct, total_score, status`

## Parameters (circuit.toml)

| Setting | Default | Description |
|---|---|---|
| `reward_learning_rate` | 0.05 | How quickly the agent adapts to new market conditions |
| `prune_win_rate_min` | 0.35 | Minimum 3-week win rate before pruning |
| `prune_drawdown_max` | 0.50 | Maximum cumulative drawdown before pruning |
| `loss_aversion` | 1.5 | How much more losing costs than gaining rewards |

> **Note:** The reward system is entirely paper-based. No real capital is ever risked when pruning.

---

## 📁 Repository Layout

```text
lyta-grokbot-multi/
├── README.md                   # Overview, rules, spot trading desk
├── ARCHITECTURE.md             # Platform split (Grok Bot server / OpenBot agents)
├── SECURITY.md                 # Reporting & secrets policy (paper-only)
├── CONTRIBUTING.md             # How to add rules / agents
├── paper_run.py                # Continuous paper-trading runner (12-bot consensus)
├── pumpfun_desk_simulator.py   # Pump.fun paper simulator (12-bot consensus)
├── pumpfun_prompt.txt          # Ready-to-paste Phase 2 pump.fun prompt
├── scripts/                    # Auxiliary scripts
├── config/                     # Local config (git-ignored; see .env.example)
│   ├── pumpfun_desk_config.txt # Phase 2 pump.fun memecoin config
│   ├── best_route_comparison.json
│   ├── bot_versions_config.json
│   └── your_run_config.json
├── legacy/                     # Experimental / superseded artifacts
├── lyta-grok-desk/             # OpenBot agent workspace (14 agents)
│   ├── circuit.toml            # Platform config + agent triggers
│   ├── AGENTS.md               # Agent catalog & runbook
│   ├── index.ts                # Router entry point
│   ├── package.json            # Node.js / TypeScript manifest
│   ├── _paper_agent.ts         # Circuit BTC/ETH paper agent (Phase 1)
│   ├── _signal_agent.ts        # Signal scanner
│   ├── _analyst_agent.ts       # Rug/liquidity/score analyst
│   ├── _trader_agent.ts        # Micro-sizing execution ($0.20–$0.85)
│   ├── _risk_agent.ts          # Risk gate (3% risk, 5x max, stand-down)
│   ├── _devwatch_agent.ts      # On-chain devwatch monitoring
│   ├── _scout_agent.ts         # Narrative/rug scout
│   ├── _trencher_agent.ts      # TrenchAI monitor
│   ├── _grok_router.ts         # Server router — routes to LYTA agents
│   ├── trading_desk.py         # TradingDesk class (state + terminal/HTML render)
│   ├── trading_desk_cli.py     # CLI entry point
│   ├── CIRCUIT_AI_PROMPT.txt   # Multi-agent Circuit AI prompt library
│   ├── CURCH_BOT_MULTI_AGENT_PROMPT.txt
│   ├── CIRCUIT_AI_12BOT_PROMPT.txt
│   ├── CURCH_BOT_STARTUP_PROMPT.txt
│   └── SECURITY.md
└── docs/                       # Design & strategy documentation
    ├── STRATEGY_FINALIZE.md
    ├── comparison_showcase.md
    ├── MULTI_VERSION_REPORT.md
    └── PAPER_COMPLETE.md
```

## ⚡ Quick Start

| Step | Command / Action |
|------|------------------|
| 1. Paper run (spot, OpenBot) | `python3 paper_run.py --minutes 30` |
| 2. One-shot check | `python3 paper_run.py --once` |
| 3. Agent workspace | Open `lyta-grok-desk/` in OpenBot; triggers fire from `circuit.toml` |

See `ARCHITECTURE.md` for the full platform split and `lyta-grok-desk/AGENTS.md` for the agent catalog.

- **Grok Bot directory:** `lyta-grok-desk/` (relative to repo root)
- All trading agents are **paper-only** — no real trades, no wallet import, no signing, no order execution.

---

## 🚀 Phase 2 — Pump.fun Memecoin Trading (SION PINNED)

The Phase 2 pump.fun Solana memecoin desk is **paper-only** and mirrors the existing
circuit paper trading setup. It is fully simulated, with Telegram alerts wired for
instant signal/entry/exit visibility.

### Quick Start (Phase 2)

```bash
# 1. Run the pump.fun simulator in paper mode
python pumpfun_desk_simulator.py --paper-only --capital 100

# 2. (Optional) Pipe to Telegram — set TELEGRAM_BOT_TOKEN in your .env
#    TelegramAlert class handles local logging + real push

# 3. Check config
cat config/pumpfun_desk_config.txt   # all rules + agent roles
```

### Paper-Only Guarantees

- **No real capital** — $100 paper balance hardcoded in `_paper_agent.ts` and
  `collateral = 100.0` fallback in `circuit.toml`

### Trading Desk Dashboard (overall summary)

The trading desk is the single source of truth for the running paper session.
It aggregates bot votes, positions, PnL, and alerts into one unified view that
can be shown on Telegram or OpenBot.

**Key files:**
- `lyta-grok-desk/trading_desk.py` — `TradingDesk` class (state + terminal/HTML render)
- `lyta-grok-desk/trading_desk_cli.py` — CLI entry point

**Usage:**
```bash
# Terminal mode: print the desk summary every 10 seconds
python3 lyta-grok-desk/trading_desk_cli.py

# One-shot (print summary once and exit)
python3 lyta-grok-desk/trading_desk_cli.py --once

# HTML mode: render a full HTML dashboard for Telegram/OpenBot
python3 lyta-grok-desk/trading_desk_cli.py --html
```

**What it shows:**
- Overall capital, open positions, closed positions, realized PnL
- Bot vote consensus (all 13 agents with buy/sell/pass tallies)
- Open position detail (asset, side, entry price, bots, PnL)
- Alerts (open, close, stand-down, vote results)
- HTML dashboard ready for Telegram/OpenBot progress viewing

### Telegram Alert Wiring

Every Phase 2 agent uses `deps = ["telegram:alert"]` so any signal, entry, stop
loss, take profit, or stand-down emits a Telegram alert.

The `TelegramAlert` class in `pumpfun_desk_simulator.py` provides:
- `alert(message, level)` — general alert (logged locally, pushed to Telegram)
- `open(position, asset, entry, side, bots, collateral)` — entry alert
- `close(asset, side, price, pnl)` — exit alert
- `stand_down(reason)` — stand-down alert
- `vote_results(asset, votes)` — vote tally alert

When `TELEGRAM_BOT_TOKEN` is set, alerts push to Telegram. Otherwise, they are
logged locally only (paper mode), and the trading desk dashboard still renders
the same alerts for the overall summary view.
- **No wallet import** — `no_wallet_import` guard blocks `import solana`,
  `sellers`, `web3`, `eth_account`
- **No signing/order execution** — `no_signing_or_order_execution` guard blocks
  `send_transaction`, `sign_transaction`, `place_order`, `execute_swap`
- **Paper labels** — every simulation file requires `PAPER ONLY` + `SIMULATION`
  labels
- **Shared state** — all simulation state includes `paper_only: true`

### Agent Roles (13 total)

| Agent | Role |
|-------|------|
| SCOUT | Narrative/rug signal checker (GMGN + wallet analysis) |
| FILTER | Low-quality pump filter (>5% 24h, >$50k volume) |
| ANALYST | Rug risk, liquidity, score evaluation |
| PUMP_CHASER | Momentum accumulation engine (>7% 24h) |
| CONVICTION | Trend/filter validator (rugScore <0.35) |
| MOMENTUM | Momentum collector (>4% 24h + >$50k volume) |
| SCALPER | High-vol scalper (>2.5% both directions) |
| CONTRARIAN | Downtrend opportunity finder (<-6% 24h, rugScore <0.5) |
| TREND | Trend follower (>5% 24h + >$50k volume) |
| RESEARCHER | On-chain research agent (liq >$50k + rugScore <0.28) |
| PORTFOLIO | Position sizing manager (3% risk, 5x max) |
| EXECUTOR | Final micro-sizing executor ($0.20–$0.85) |
| PAPER | Paper trading agent (Circuit BTC/ETH) |

### Trading Rules (Phase 2)

- Buy only when >=7 of 12 bots vote BUY (min=7, max=10, default=7)
- Skip coins up >100% in the past hour (max_h1_pump_pct=100)
- Skip coins with liquidity < $50,000 (min_liquidity_usd=50000)
- Stop loss: sell whole position at -35% from entry (stop_loss_pct=35)
- Take profit: sell whole position at +50% from entry (take_profit_pct=50)
- Exit check first every 15min run (exits checked before any entry)
- Stand-down messages name the active buy filters when nothing qualifies

### Telegram Alert Wiring

Every Phase 2 agent uses `deps = ["telegram:alert"]` so any signal, entry, stop
loss, take profit, or stand-down emits a Telegram alert.

The `TelegramAlert` class in `pumpfun_desk_simulator.py` provides:
- `alert(message, level)` — general alert (logged locally, pushed to Telegram)
- `open(position, asset, entry, side, bots, collateral)` — entry alert
- `close(asset, side, price, pnl)` — exit alert
- `stand_down(reason)` — stand-down alert
- `vote_results(asset, votes)` — vote tally alert

When `TELEGRAM_BOT_TOKEN` is set, alerts push to Telegram. Otherwise, they are
logged locally only (paper mode).

### Secrets & Credentials

- `TELEGRAM_BOT_TOKEN` — optional, for real Telegram push in Phase 3
- `PUMPFUN_API_KEY`, `BIRDEYE_API_KEY` — paper-only, keep blank
- Never commit real values. Use `.env.example` for the template.

