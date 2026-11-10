# Agent Setup Summary — LYTA Pump.fun Grok Bot Trading Desk

## 🟦 OpenBot Agent Store (7 Agents, 8 Routines)

All 7 agents are configured in the OpenBot agent store at:
- **OpenBot store:** `~/.openbot/openbot.db` (or `$OPENBOT_BASE_DIR/openbot.db`)

| # | Agent ID | Role | Tagline | Routines |
|---|----------|------|---------|----------|
| 0 | `lyta-grok-desk-paper` | Phase 1 Circuit Paper Trading | 12-bot Circuit Papertrade desk · $2–$6 paper trading · paper-only | 1 |
| 1 | `lyta-grok-desk-pumpfun` | Spot trading (future Phase) | 12-agent spot trading desk · paper-only | 1 |
| 2 | `grok-bot` | Primary Routing Bot | Routes any task to the right LYTA agent | 0 |
| 3 | `lyta-grok-desk-signal` | Signal Generator | Pump.fun signal generator · no execution · paper-only | 1 |
| 4 | `lyta-grok-desk-analyst` | Memecoin Analyst | Evaluates tokens for rug risk, liquidity, analyst_score | 1 |
| 5 | `lyta-grok-desk-trader` | Execution Agent | Executes trades with micro sizing $0.20–$0.85 | 1 |
| 6 | `lyta-grok-desk-risk` | Risk Manager | Enforces 3% risk, 5x max, stand-down on minimums | 1 |

### Routines Breakdown
- **lyta-grok-desk-paper**: 12-Bot Paper Trading Desk (12-bot consensus on Circuit Papertrade)
- **lyta-grok-desk-pumpfun**: 12-Bot Pumpfun Paper Desk (12-bot consensus on pump.fun)
- **lyta-grok-desk-signal**: Signal Generation (analyzes market → generates trade_signal)
- **lyta-grok-desk-analyst**: Analyst Evaluation (evaluates tokens → analyst_report)
- **lyta-grok-desk-trader**: Trade Execution (executes trades, verifies paper_only)
- **lyta-grok-desk-risk**: Risk Enforcement (3% risk, 5x max, stand-down)

## 🟨 Grok Bot Agent (lyta-grok-desk/)

- **Grok Bot directory:** `lyta-grok-desk/` (relative to repo root)

- **index.ts**: Full 12-bot trading desk (Circuit Papertrade)
- **circuit.toml**: Papertrade network, 3% risk, 5x max leverage
- **AGENTS.md**: Complete agent documentation (19,258 chars)
- **CIRCUIT_PAPER_PROMPT.txt**: Copy-paste prompt for Builder
- **description.md**: Thesis, strategy, exposure parameters

### 12 Bot Personalities
SCOUT, FILTER, ANALYST, PUMP_CHASER, CONVICTION, MOMENTUM, SCALPER, CONTRARIAN, TREND, RESEARCHER, PORTFOLIO, EXECUTOR

### Consensus Requirements
- **Min 5/12 bots** agree on a side
- **3% risk** per trade
- **5x max** position size
- **Micro sizing** $0.20–$0.85

## 🔒 Upstream Learnings (from today's research)

| Source | Insight | Application |
|---|---|---|
| [0ooooo0 - Routinizer](https://x.com/0ooooo0) | Bots waste quota on repeating routines | Scripts replace polling loops; bots only wake on real change |
| [AIDuckLabs](https://x.com/AIDuckLabs) | 50-agent company built overnight via GrokBot | 12-bot desk is the "team" — Chief of Staff (grok-bot) routes |
| [aryanvij02 - Freebot](https://x.com/aryanvij02) | GrokBot hits usage limits; move to Turnstone | Run on any AI subscription (Claude, ChatGPT) when Grok runs out |
| [de1lymoon - Open source stack](https://x.com/de1lymoon) | 9 open-source tools | OpenBot (7.0K★) is platform; Rakazo, OpenMausBot, eigent, paperclip, openhuman, hermes-agent, nanoclaw, openclaw are alternatives |

## 📤 Upstream Status
- **PO_TRAIL**: 2.5x target exit multiple
- **PO_TRAIL_DD**: 15% trailing drawdown threshold
- **Example**: Entry @ 1.00x → Peak 1.50x → Trail high 3.75x → Trigger 3.19x → Exit @ 2.5x = +150% P&L before costs

## % Allocations (Paper Mode)
| Parameter | Value |
|-----------|-------|
| Paper capital | $6.00 |
| Risk per trade | 3% ($0.18) |
| Micro sizing | $0.20–$0.85 |
| Max position | 5x |
| Entry window | 8%–70% |
| Top-10 concentration | ≤30% |
| Developer holdings | ≤15% |
| Consensus bar | 7/12 (58%) |

## 🔒 Paper-Only Guard Gates (Verbatim)
- `no_wallet_import`: rejects `import solana / sellers / web3 / eth_account`
- `no_signing_or_order_execution`: rejects `send_transaction`, `sign_transaction`, `place_order`, `execute_swap`
- `paper_label_present`: requires `PAPER ONLY` + `SIMULATION`
- `shared_state_paper_flag`: requires `paper_only: true` in state
- `spec_simulation_only`: spec declares `SIMULATION` + `paper_only: true`

---

## 💰 Agent Reward System (Paper-Based)

Agents are scored daily and pruned when they underperform. All operations are
**paper-only — no real capital is ever risked**.

### Scoring Formula
```
daily_score = +100 if win else −100
profit_score = pnl_pct * 2.0
volatility_penalty = −drawdown_pct * 0.5
total_score = daily_score + profit_score + volatility_penalty
```

### Pruning Policy
| Condition | Action |
|---|---|
| 5 consecutive losing days | Delete agent |
| 3 consecutive losing weeks | Delete agent |
| Cumulative drawdown > 50% | Delete agent |
| 3-week win rate < 35% | Delete agent |

### Parameters (circuit.toml)
| Parameter | Default | Description |
|---|---|---|
| `reward_learning_rate` | 0.05 | How fast the agent adapts |
| `prune_win_rate_min` | 0.35 | Minimum 3-week win rate before pruning |
| `prune_drawdown_max` | 0.50 | Max drawdown before pruning |
| `loss_aversion` | 1.5 | Losing costs 1.5× more than gaining is worth |

### Implementation
- `reward_tracker.py` — Computes scores, logs performance, checks prune conditions, manages leaderboard
- `performance_log.csv` — Persistent score log (survives restarts)
- `lyta-grok-desk/AGENTS.md` — Agent documentation with reward system section
- OpenBot `openbot.db` — Agent store where pruned agents are deleted

### Example Commands
```bash
# Log a day's performance
python3 reward_tracker.py --log agent_lyta-grok-desk-signal 3.5 true 1.0

# Check pruning status for all agents
python3 reward_tracker.py --check

# Show leaderboard
python3 reward_tracker.py --leaderboard 10

# Prune failing agents
python3 reward_tracker.py --prune agent_lyta-grok-desk-signal
```
