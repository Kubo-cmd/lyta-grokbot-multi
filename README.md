# LYTA Trading Desk

---
## 📋 Contents
- [What This Is](#what-this-is)
- [Trading Agent Suite](#trading-agent-suite-10-agents)
- [Trading Desk Parameters](#trading-desk-parameters)
- [Paper-Only Guard Gates](#paper-only-guard-gates-verbatim)
- [Agent Performance Reward System](#agent-performance-reward-system)
- [Latency & Volatility Spike Guidance](#latency--volatility-spike-guidance)
- [Platform Comparison (Yes/No)](#platform-comparison-yesno)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [GitHub](#github)

---
> **Platform: Grok Bot (server) + OpenBot (agents) | Mode: Paper-only**

## 🎯 What This Is

A **10-agent spot trading desk** on **OpenBot** (local, localhost:5173), with Grok Bot (cloud) as the control-plane router. The desk operates in **paper-only mode** — no real trades, no wallet import, no signing, no order execution.

| Component | Platform | Role | Always-On? |
|-----------|----------|------|------------|
| **Grok Bot (Server)** | Managed cloud VM (xAI) | Task routing, coordination, persistent state | ✅ Yes — cloud stays up when laptop closes |
| **OpenBot (Agents)** | Local desktop workspace (nightly-labs) | 10 trading agents — paper, signal, analyst, trader, risk, etc. | Runs on local machine |
| **Grok CLI** | Grok Bot | Token analysis pipeline | Paper-only |

---

## 🤖 Trading Agent Suite (10 Agents)

| Agent | Platform | Role | Paper Guards |
|-------|----------|------|-------------|
| `lyta-grok-desk-paper` | OpenBot | Circuit BTC/ETH paper trading (Phase 1 baseline) | `SIMULATION` + `paper_only` |
| `lyta-grok-desk-signal` | OpenBot | Signal generator | Paper-only |
| `lyta-grok-desk-analyst` | OpenBot | Analyst — evaluates rug risk, liquidity, score | Paper-only |
| `lyta-grok-desk-trader` | OpenBot | Execution agent — micro-sizing $0.20–$0.85 | Paper-only |
| `lyta-grok-desk-risk` | OpenBot | Risk manager — 3% risk, 5x max, stand-down | Paper-only |
| `lyta-grok-desk-scout` | OpenBot | Narrative/rug signal checker | Paper-only |
| `lyta-grok-desk-devwatch` | OpenBot | On-chain wallet monitoring | Paper-only |
| `lyta-grok-desk-trencher` | OpenBot | TrenchesAI deployment monitor | Paper-only |
| `grok-bot` | Grok Bot | Server — routes tasks to the right LYTA agent | Paper-only |

---

## 📊 Trading Desk Parameters

> **Current focus (Tightened):** 7/12 consensus, skip >100% 1h pump and <$50k liquidity, −35% SL / +50% TP. Paper observation only.

### Platform Comparison (Yes/No)

| Question | OpenBot | Grok bot |
|-----------|---------|----------|
| Local-first execution | ✅ Yes | ❌ No |
| Data stays on your machine | ✅ | ❌ |
| Cost model | Free (non-commercial) | Self-hosted |
|| Mobile app | ✅ Yes | ✅ Yes (iOS/Android) |
|| Voice / dictation | ✅ Yes | ✅ Yes (voice input, voice chat) |
|| Backup models | ✅ Yes | ✅ Yes (cloud backup, multiple plans) |
|| Teams / roles | ❌ No | ✅ Yes (group chats, parallel bots, roles) |
|| Chat / human-in-loop | ✅ Yes | ✅ Yes (text-thread interface) |
|| Schedule automation | ✅ Yes (local sweeps) | ✅ Yes (cloud routines) |
|| Source code | ✅ Open (openbot.io) | ✅ Open (lyta-grokbot-multi) |

See [lyta-grok-desk/BOT-COMPARE.md](lyta-grok-desk/BOT-COMPARE.md) for the full contrast with the lean highlighted.

---

## 📊 Trading Desk Parameters

> **Current focus (Tightened):** 7/12 consensus, skip >100% 1h pump and <$50k liquidity, −35% SL / +50% TP. Paper observation only.

### Trading Desk Parameters (Spot Trading)

| Dimension | Detail |
|-----------|--------|
| **Core desk** | OpenBot, local-only (localhost:5173), `paper_mode: true` |
| **Lifecycle** | Paper-only guard gates apply to all trading agents |
| **Consensus** | 10-bot consensus (multi-agent) |
| **Screening** | Spot trading only — no pump/fun perimeters |

### Trailing Exit Logic

| Setting | Value | Meaning |
|---|---|---|
| `PO_TRAIL_DD` | 15% | Trailing drawdown threshold from peak |
| Trail high | `peak_price` (running high) | Dynamic exit trigger |
| Trigger | `peak × 0.85` | Exit when price falls to 85% of running peak |

**Correct rule:** Exit when `current_price <= peak_price * (1 - PO_TRAIL_DD)`.
Previously the logic used an always-true condition with a 2.5x multiplier, causing immediate exit at entry. The fix compares against the running peak only.

### 10-Bot Consensus

| Bot group | Role |
|---|---|
| Market analysis | Market data |
| Analyst | Expert commentary |
| Risk Manager | Position sizing (5x) |
| Semantic (CROSS) | Cross-check |
| Trailing | Trailing exit logic |
| Scout | Narrative/rug signal checker |
| DevWatch | On-chain wallet monitoring |
| Trencher | TrenchesAI deployment monitor |

---

## 🔒 Paper-Only Guard Gates (Verbatim)

All trading agents enforce these paper-only guard gates:

| Guard Gate | Blocks |
|---|---|
| `no_wallet_import` | `import solana`, `sellers`, `web3`, `eth_account` |
| `no_signing_or_order_execution` | `send_transaction`, `sign_transaction`, `place_order`, `execute_swap` |
| `paper_label_present` | Requires `PAPER ONLY` + `SIMULATION` labels |
| `shared_state_paper_flag` | Requires `paper_only: true` in state |
| `spec_simulation_only` | Spec declares `SIMULATION` + `paper_only: true` |

---

## ⏱️ Latency & Volatility Spike Guidance (Grok Bot API)

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

## 🔓 License & Visibility

| Item | Status |
|---|---|
| GitHub repo | `Kubo-cmd/lyta-grokbot-multi` — **PRIVATE** (do not publish) |
| License | MIT text tracked in this **PRIVATE** tree — unpublished; do not treat as public OSS |
| OpenBot store | `~/Library/Application Support/OpenBot/openbot.db` (platform home) |
| Grok Bot directory | `lyta-grok-desk/` (relative to repo root) |

---

## 📁 Repository Layout

```text
lyta-grokbot-multi/
├── README.md                   # Overview, rules, spot trading desk
├── ARCHITECTURE.md             # Platform split (Grok Bot server / OpenBot agents)
├── SECURITY.md                 # Reporting & secrets policy (paper-only)
├── CONTRIBUTING.md             # How to add rules / agents
├── paper_desk_simulator.py     # Paper-only simulator (test-mode, exit 0)
├── scripts/                    # Auxiliary scripts
├── config/                     # Local config (git-ignored; see .env.example)
├── legacy/                     # Experimental / superseded artifacts
├── lyta-grok-desk/             # OpenBot agent workspace (10 agents)
│   ├── circuit.toml            # Platform config + agent triggers
│   ├── AGENTS.md               # Agent catalog & runbook
│   ├── index.ts                # Router entry point
│   ├── package.json            # Node.js / TypeScript manifest
│   ├── _paper_agent.ts         # Circuit BTC/ETH paper agent (Phase 1)
│   ├── _signal_agent.ts        # Signal scanner
│   ├── _analyst_agent.ts       # Rug/liquidity/score analyst
│   ├── _trader_agent.ts        # Micro-sizing execution ($0.20–$0.85)
│   ├── _risk_agent.ts          # Risk gate (3% risk, 5x max, stand-down)
│   ├── _grok_router.ts         # Server router — routes to LYTA agents
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
| 1. Install dependencies | `pip install -r requirements.txt` (if present) or use the project venv |
| 2. Paper run (spot, OpenBot) | `python paper_desk_simulator.py --test-mode --test-iterations 1` |
| 3. Agent workspace | Open `lyta-grok-desk/` in OpenBot; triggers fire from `circuit.toml` |

See `ARCHITECTURE.md` for the full platform split and `lyta-grok-desk/AGENTS.md` for the agent catalog.

- **Grok Bot directory:** `lyta-grok-desk/` (relative to repo root)
- All trading agents are **paper-only** — no real trades, no wallet import, no signing, no order execution.
