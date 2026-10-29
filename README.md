# LYTA GrokBot Multi — Autonomous Multi-Bot Trader

**Open source autonomous trader using multiple Grok-powered bots with distinct personalities.**

Inspired by:
- Pump.fun-native AI agents (like the Lilly @lillyonpump concept) and **6-agent desk pipelines**
- **Oren ⚡** — AI-powered agentic trading terminal for tokenized stocks on Solana by @itsdavetech  
  (https://x.com/itsdavetech/status/2115571527509017068)

Built around **explicit multi-bot architecture** with different risk profiles, biases, and trading styles (now expanded toward a fuller agentic desk covering research + portfolio + execution).

## Key Features

- **12 specialized Grok bots** (full agentic desk — Pump.fun style + Oren tokenized-stock inspiration):
  - **SCOUT**: Early pair hunter. Aggressive on brand-new launches and is_pump signals.
  - **FILTER**: Extremely strict rule-based. Only the cleanest setups (low rug, high score, decent volume/liquidity).
  - **ANALYST**: Heavy analyst_score bias. Very selective high-conviction scorer.
  - **PUMP_CHASER**: Loves early is_pump launches. Classic 1.5x chatbot TP.
  - **CONVICTION**: High analyst_score bias. Tighter risk. More selective.
  - **MOMENTUM**: Price change + buy ratio focused. Balanced.
  - **SCALPER**: Fast in/out. Tight stops, small quick targets, high frequency bias.
  - **CONTRARIAN**: Bets against recent crowd momentum on still-clean setups.
  - **TREND**: Rides stronger sustained moves with higher TP targets.
  - **RESEARCHER** (Oren-inspired): Deep research focus — high score, clean liquidity, ignores hype.
  - **PORTFOLIO** (Oren-inspired): Portfolio-level allocation + risk overlay.
  - **EXECUTOR** (Oren-inspired): Clean execution focus, slippage-aware, disciplined exits.
- Realistic price movement model based on **liquidity + volume**.
- Liquidity-respecting position sizing (never over-allocates to thin books).
- Bot-specific risk parameters (hard stops, trailing, TP levels).
  - Tuned closer to video reference: baseline ~ -6% hard stops + strict 8% max position sizing.
- Full **paper trading only** (zero-burn, observation mode by default).
- Exports:
  - `paper_trades_autonomous_grok.csv`
  - `equity_curve_autonomous_grok.csv`
  - `grok_signals_for_real_bot.json` (actionable signals with 12-agent labels + Oren-inspired agents)
- Pure stdlib verification (no pandas required for analysis).
- Terminal-style realtime desk dashboard prints every 5 steps (agent activity + open positions + equity).
- Per-bot equity curves available via post-run analysis (`verify_80step.py`).
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
python3 grokbot_multi.py viable_test   # longer 80-step viability run + signals + curves
```

After a viable_test run you can also run:
```bash
python3 verify_80step.py   # pure stdlib per-bot equity curves + full verification
```

To support terminal dashboard feel, the main runner now prints periodic [DESK] recent activity lines (every 5 steps) with bot activity counts.

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

## Circuit Platform Port (Real-Life Testing)
We scaffolded a native Circuit agent (`lyta-grok-desk/`) that ports the 12-bot desk concept to the actual platform.

- Uses **Papertrade** (the most popular mode on app.circuit.org for high-leverage PAPER farming agents).
- The 12 personalities (SCOUT → EXECUTOR) are implemented as voting bots inside `index.ts`.
- All risk parameters mirror the Python simulation (video-tuned -6% stops + 8% sizing).
- Start in paper mode on the platform.

### How to test on Circuit
```bash
cd lyta-grok-desk
circuit check
circuit run --paper     # simulated / paper trading mode (recommended first)
```

Once it runs cleanly in paper, you can upload it via the Circuit app for real testing (with your own wallet, still controllable).

**Important:** Circuit agents are TypeScript. The Python simulator remains the research / signal generation tool. The TS version is for running on the actual platform.

## Structure

- `grokbot_multi.py` — Main autonomous multi-bot runner (self-contained)
- `README.md` — This file
- Exported CSVs + JSON on every run

## Extending the Bots

Edit the `BOT_PROFILES` and `GrokBot.decide()` logic inside `grokbot_multi.py`. Add new personalities easily:

```python
BOT_PROFILES["SCALPER"] = { ... }
```

The current 12 personalities were expanded (SCOUT, FILTER, ANALYST + PUMP_CHASER, CONVICTION, MOMENTUM + SCALPER, CONTRARIAN, TREND + RESEARCHER, PORTFOLIO, EXECUTOR) to mirror both Pump.fun-style 6+ agent desk systems and the Oren ⚡ agentic terminal concept (research + portfolio + execution layers) from https://x.com/itsdavetech/status/2115571527509017068.

Example from 80-step viability test (pure stdlib):
- ~128–190 trades, ~30–34% win rate
- Per-bot equity curves show wide variance (SCOUT more active/aggressive, new Oren-inspired bots more selective)
- Full grok_signals_for_real_bot.json exported with 12-agent labels
- Terminal desk dashboard lines every 5 steps for realtime feel (shows open positions + equity)

## Relationship to Lilly-style Agents

This is the **multi-bot Grok version** of the autonomous trader idea. One bot = one personality. Multiple bots running in parallel on the same survivor pool creates interesting emergent behavior and risk diversification.

## License

MIT — see LICENSE.

## Disclaimer

**All trading simulation. Not financial advice. Past paper performance is not indicative of future results.** Use at your own risk for research and learning only.

PATTERN PERSISTS.
