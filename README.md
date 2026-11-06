# LYTA Pump.fun Trading Desk

> **Platform: OpenBot + Grok Bot + Circuit + Trencher AI | 7 trading agents | Mode: Paper-only**

## 🎯 What This Is

A **12-bot trading desk** that trades **memecoins on pump.fun**. Agents are carried across three platforms:

| Platform | Role |
|---|---|
| **OpenBot** | Core 7-agent trading desk (paper + signal + analyst + trader + risk + grok-bot) — the execution desk |
| **Grok Bot** | Primary routing bot — sends tasks to the right LYTA agent |
| **Circuit AI** | Parameter engine — holds the circuit.toml configuration and publishes platform parameters |
| **Trencher AI** | Secondary platform — paper-only copy with fixed-size buy, no dynamic sizing |

The desk is **paper-only**: no real trades, no wallet import, no signing, no order execution.

---

## 🤖 Trading Agent Suite (7 Agents)

| Agent | Platform | Role | Paper Guards |
|---|---|---|---|
| `lyta-grok-desk-paper` | OpenBot | Circuit paper (BTC/ETH) — Phase 1 baseline | `SIMULATION` + `paper_only` |
| `lyta-grok-desk-pumpfun` | OpenBot | **Pump.fun memecoin trading — Phase 2** | `SIMULATION` + `paper_only` |
| `lyta-grok-desk-signal` | OpenBot | Signal generator — scans pump.fun for opportunities | Paper-only |
| `lyta-grok-desk-analyst` | OpenBot | Analyst — evaluates rug risk, liquidity, score | Paper-only |
| `lyta-grok-desk-trader` | OpenBot | Execution agent — micro-sizing $0.20–$0.85 | Paper-only |
| `lyta-grok-desk-risk` | OpenBot | Risk manager — 3% risk, 5x max, stand-down | Paper-only |
| `grok-bot` | Grok Bot | Primary bot — routes tasks to the right LYTA agent | Paper-only |

---

## 📊 Trading Desk Parameters

> **Current focus (Tightened, Phase 2):** 7/12 consensus, skip >100% 1h pump and <$50k liquidity, −35% SL / +50% TP. Paper observation only.

### Platform Perimeters (Current State)

| Platform | Mode | Key Settings | Dynamic Sizing |
|---|---|---|---|
| **Circuit** | `mode = PAPER` | `allowed_sources = ["pump.fun"]`, `max_open_positions = 1`, `buy_slippage = 10%` | Yes — `micro_size` 0.20–0.50 |
| **Trencher AI** | `mode = PAPER` | `allowed_sources = ["pump.fun"]`, `max_open_positions = 1`, `buy_slippage = 10%`, `stop_loss = 0.65x entry` | **No** — fixed 0.05 SOL |

### Capital, Sizing & Stop-Loss

| Metric | Circuit | Trencher AI | Notes |
|---|---|---|---|
| Paper capital | **$2–$6** | **$2–$6** | Tightened micro paper capital, no live capital |
| Buy size | micro $0.20–$0.85 | 0.05 SOL fixed | Circuit uses 3% risk micro-size; Trencher is fixed |
| Break-even | ~1.06x | ~1.06x | Under current fee examples |
| Stop loss | −35% (0.65x) | −35% (0.65x) | Tightened STOP_LOSS=0.35 / TAKE_PROFIT=0.50 |
| Stop-loss type | Request-based exit; rug may fill worse or not at all | Same | Guaranteed cap is an illusion; the bot may exit at −35%, −40%, or not at all |

### Trailing Exit Logic

| Setting | Value | Meaning |
|---|---|---|
| `PO_TRAIL` | 2.5x | Target exit multiple |
| `PO_TRAIL_DD` | 15% | Trailing drawdown threshold |
| Trail high | `peak_price × 2.5x` | Dynamic exit trigger |
| Trigger | `peak × 2.5x × (1 − 15%)` | Exit when price falls to this level |

**Example:** Entry @ 1.00x → Peak @ 1.50x. Trail high = 1.50 × 2.5 = **3.75x**. Trigger = 3.75 × (1 − 0.15) = **3.19x**.

### 12-Bot Consensus

| Bot group | Role |
|---|---|
| Market analysis | Market data |
| Analyst | Expert commentary |
| Risk Manager | Position sizing (5x) |
| Semantic (CROSS) | Cross-check |
| Trailing | Trailing exit logic |

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

### Trencher AI Note

Trencher AI **does not support** user-editable config files or execution restrictions. Its paper copy uses `mode = PAPER` and `allowed_sources = ["pump.fun"]` only. It cannot enforce:

- dynamic percentage or USD sizing
- leverage, `risk_per_trade`, or configurable polling/API timeouts
- network-only retry rules
- code-import/call blocking
- score-collapse exits

Therefore `paper_only = true` files and execution restrictions **cannot be cleanly enforced on Trencher** — they are enforced on OpenBot (the core desk) and on Circuit (via circuit.toml), but not on Trencher.

---

## ⏱️ Latency & Volatility Spike Guidance (Grok Bot API)

When running agents against Grok Bot during volatility spikes:

| Risk | Mitigation |
|---|---|
| Rate limits / quota exhaustion | Scripts poll pump.fun at 5–10s intervals; wake Grok agent only on real change (Routinizer) |
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
| License | Unpublished — paper-only desk, closed for trading |
| OpenBot store | `~/Library/Application Support/OpenBot/openbot.db` (platform home) |
| Grok Bot directory | `lyta-grok-desk/` (relative to repo root) |

---

## 📤 Quick Reference

- **Freebot/Turnstone:** [aryanvij02](https://x.com/aryanvij02) — run Grok bots on any AI subscription; GrokBot hit usage limits → move bots to Claude/ChatGPT via Turnstone
- **Open-source alternative stack:** [de1lymoon](https://x.com/de1lymoon) — 9 tools (Rakazo, OpenMausBot, OpenBot, eigent, paperclip, openhuman, hermes-agent, nanoclaw, openclaw); OpenBot (7.0K★) is our platform
- **Routinizer:** [0ooooo0](https://x.com/0ooooo0) — scripts replace repeating bot routines to cut quota by 80–90%
- **GitHub:** `https://github.com/Kubo-cmd/lyta-grokbot-multi` (**PRIVATE** — do not publish)
- **OpenBot store:** `~/Library/Application Support/OpenBot/openbot.db`
- **Grok Bot directory:** `lyta-grok-desk/` (relative to repo root)

All trading agents are **paper-only** — no real trades, no wallet import, no signing, no order execution.
