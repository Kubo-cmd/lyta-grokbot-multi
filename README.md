# LYTA GrokBot Multi — Autonomous Multi-Bot Trader

**Open source autonomous trader using multiple Grok-powered bots with distinct personalities.**

Inspired by Pump.fun-native AI agents (like the Lilly @lillyonpump concept) but built around **explicit multi-bot architecture** with different risk profiles, biases, and trading styles.

## Key Features

- **Three specialized Grok bots** (easily extensible):
  - **PUMP_CHASER**: Loves early is_pump launches. Slightly more aggressive on fresh Pump.fun-style tokens. Classic 1.5x chatbot TP.
  - **CONVICTION**: High analyst_score bias. Tighter risk. More selective.
  - **MOMENTUM**: Price change + buy ratio focused. Balanced.
- Realistic price movement model based on **liquidity + volume**.
- Liquidity-respecting position sizing (never over-allocates to thin books).
- Bot-specific risk parameters (hard stops, trailing, TP levels).
- Full **paper trading only** (zero-burn, observation mode by default).
- Exports:
  - `paper_trades_autonomous_grok.csv`
  - `equity_curve_autonomous_grok.csv`
  - `grok_signals_for_real_bot.json` (actionable signals for a *separate* real executor)
- Pure stdlib + optional pandas fallback.
- Designed so the simulation can be studied, tuned, and extended openly.

## Philosophy

This project keeps the simulation **strictly paper** so anyone can study realistic micro-cap dynamics (slippage, rugs, liq impact, bot variance) without risk.

The multi-bot design lets you observe how different personalities perform across the same market conditions — exactly the kind of thing a real autonomous trader would need.

Real execution (wallets, signing, on-chain) is intentionally **out of scope**. Export clean signals instead.

## Quick Start

```bash
cd lyta-grokbot-multi
python3 grokbot_multi.py          # default ~18 steps
python3 grokbot_multi.py 5        # short controlled run
python3 grokbot_multi.py viable_test   # longer 80-step viability run
```

No external keys or accounts required. Everything is simulated.

## Example Output (typical 5-step run)

- Multiple bots independently scanning and deciding
- Bot-specific exits (hard stop vs 1.5x TP vs trailing)
- Equity curve + per-bot PnL breakdown
- Realistic fees/slippage applied on every paper trade

## Project Goals

- Make a high-quality, auditable, multi-personality autonomous trading simulator open source.
- Provide a foundation others can fork, improve the decision logic, add new bots, or connect to their own execution layer.
- Stay true to "paper first" while producing exportable signals that could be consumed by a real system.

## Structure

- `grokbot_multi.py` — Main autonomous multi-bot runner (self-contained)
- `README.md` — This file
- Exported CSVs + JSON on every run

## Extending the Bots

Edit the `BOT_PROFILES` and `GrokBot.decide()` logic inside `grokbot_multi.py`. Add new personalities easily:

```python
BOT_PROFILES["SCALPER"] = { ... }
```

## Relationship to Lilly-style Agents

This is the **multi-bot Grok version** of the autonomous trader idea. One bot = one personality. Multiple bots running in parallel on the same survivor pool creates interesting emergent behavior and risk diversification.

## License

MIT — see LICENSE.

## Disclaimer

**All trading simulation. Not financial advice. Past paper performance is not indicative of future results.** Use at your own risk for research and learning only.

PATTERN PERSISTS.
