# Circuit AI Bots — 10-Agent Architecture (lyta-grok-desk)

Phase 2 of the pump.fun grok trading desk: building **more Circuit AI bots**
on the Circuit platform (circuit.org). This workspace runs a **10-agent
OpenBot layer + 1 coordination router** atop Circuit's Papertrade SDK
(paper-only, no live wallet, no real capital).

## The 10 agents

|| # | Agent | File | Role |
||---|-------|------|------|
|| 1 | `lyta-grok-desk-paper` | `_paper_agent.ts` | Phase 1 paper desk — Circuit Papertrade BTC/ETH paper-only trading |
|| 2 | `lyta-grok-desk-signal` | `_signal_agent.ts` | Scans pump.fun launches + trending + momentum → distributes opportunities |
|| 3 | `lyta-grok-desk-analyst` | `_analyst_agent.ts` | Rug/liquidity/safety evaluation → pass/fail score |
|| 4 | `lyta-grok-desk-trader` | `_trader_agent.ts` | Micro-sizing execution engine — $0.20–$0.85 paper orders |
|| 5 | `lyta-grok-desk-risk` | `_risk_agent.ts` | 6-point stand-down monitor — commands desk to stand down on instability |
|| 6 | `lyta-grok-desk-pumpfun` | `index.ts` | pump.fun memecoin entry point (Phase 2 adapter) |
|| 7 | `lyta-grok-desk-scout` | `_scout_agent.ts` | Narrative/rug signal check — GMGN + wallet analysis |
|| 8 | `lyta-grok-desk-devwatch` | `_devwatch_agent.ts` | On-chain wallet monitoring (Hrundel75 rules) |
|| 9 | `lyta-grok-desk-trencher` | `_trencher_agent.ts` | TrenchesAI deployment monitor + integration |
|| 10 | `grok-bot` | `_grok_router.ts` | Server-side task router — receives tasks from Grok Bot server (xAI managed cloud VM), dispatches to correct agent |

## Agent data flow

```
[Grok Bot server (xAI cloud VM)]
        │  task routing  │
        ▼
[grok-bot _grok_router.ts] ──► [signal _signal_agent.ts] ──► [analyst _analyst_agent.ts]
        │  (dispatch)         │  (scan pump.fun + trending) │  (rug/liq/safety)
        │                     ▼                           ▼
        └────► [paper _paper_agent.ts] ◄────► [trader _trader_agent.ts] ◄─┘
                (paper desk)      (micro-sizing)        (only calls positions.open)
```

## circuit.toml

- `[[agents]]` blocks define each of the 8 agents with `name` + `file`.
- `[settings]` locks the key risk parameters.
- `startingAsset` = `papertrade` / `USDC` / `minimumAmount = "0.50"`.
- `paper_only = { type = "boolean", default = true }`.

## Key parameters (locked)

| Parameter | Default | Range |
|-----------|---------|-------|
| `max_leverage` | 5 | 1–5 |
| `desk_risk_pct` | 3% | 1–3% |
| `risk_per_trade` | 3% | 1–3% |
| `micro_size_min` | $0.20 | ≥0.20 |
| `micro_size_max` | $0.85 | 0.20–0.85 |
| `min_collateral` | $1.50 | 0.50–2.00 |
| `consensus_bar` | 7 | 7–12 |
| `trailing_multiple` | 2.5x | 1.0–5.0 |
| `trailing_drawdown` | 15% | 5–30% |
| `stop_loss_pct` | 35% | 35–50% |
| `take_profit_pct` | 50% | 50–100% |
| `min_liquidity_usd` | $50,000 | ≥50,000 |
| `max_h1_pump_pct` | 100% | 50–100% |
| `paper_only` | true | — |
| `reward_learning_rate` | 0.05 | 0.001–1 |
| `prune_win_rate_min` | 0.35 | 0–1 |
| `prune_drawdown_max` | 0.50 | 0–1 |
| `loss_aversion` | 1.5 | 1–5 |

## Execution model

This is **pure paper trading**. The paper desk uses Circuit's Papertrade SDK
(synthetic perpetuals + PAPER stake) and never touches a real wallet, signs
real transactions, or trades with real capital. The 8-agent architecture
replicates the full openbot pipeline (scan → analyze → execute → risk —
stand down) in a single paper workspace.

## Relationship to the paper_desk_simulator.py

The Python `paper_desk_simulator.py` in the repo root is a **local offline
replica** of the 8-agent paper trading loop — used for backtesting, never for
live trading. It receives the same 8-agent pipeline
(signals → analyst → trader → risk) as its agent loop and outputs the same
position lifecycle logs (entry/exit/stand-down) that the Circuit AI engines
produce live.
