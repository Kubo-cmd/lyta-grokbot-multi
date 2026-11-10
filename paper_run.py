#!/usr/bin/env python3
"""
LYTA Grok Trading Desk — Paper Trading Runner
==============================================
Runs a continuous paper trading session and updates the Trading Desk
in real-time.  Shows a live terminal summary every N seconds, plus
regenerates the HTML dashboard.

Usage:
    python3 paper_run.py              # run for 30 minutes (default)
    python3 paper_run.py --minutes 60
    python3 paper_run.py --once       # one tick only, print and exit

Requires: python3, no external deps.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import random
from datetime import datetime

# ── Load TradingDesk ───────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import importlib.util
_desk_path = os.path.join(REPO_ROOT, "lyta-grok-desk", "trading_desk.py")
_spec = importlib.util.spec_from_file_location("trading_desk", _desk_path)
_td_mod = importlib.util.module_from_spec(_spec)
sys.modules["trading_desk"] = _td_mod
_spec.loader.exec_module(_td_mod)
TradingDesk = _td_mod.TradingDesk

# Create the global trading desk (same as pumpfun_desk_simulator.py)
TRADE_DESK = TradingDesk(capital=100.0, asset="GOBLIN", config="v3")

# ── 12-bot roster (mirrors pumpfun_desk_simulator.py) ─────────────
BOT_NAMES = [
    "SCOUT", "FILTER", "ANALYST", "PUMP_CHASER", "CONVICTION",
    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
    "PORTFOLIO", "EXECUTOR"
]

# Simple bot logic: each bot returns buy/sell/pass based on market data
def run_bot(bot_name: str, market: dict) -> str:
    """Run a single bot and return its decision."""
    score = market.get("score", 50)
    rug_risk = market.get("rug_risk", 0.5)
    liquidity = market.get("liquidity", 1.0)
    volume = market.get("volume", 1.0)
    change24h = market.get("change24h", 0)

    if bot_name == "SCOUT":
        # Look for early signals
        if change24h > 2 and volume > 0.5:
            return "buy"
        if change24h < -1:
            return "sell"
        return "pass"
    elif bot_name == "FILTER":
        # Filter for quality
        if liquidity > 0.6 and rug_risk < 0.4:
            return "buy"
        if rug_risk > 0.7:
            return "sell"
        return "pass"
    elif bot_name == "ANALYST":
        # Analyze fundamentals
        if rug_risk < 0.3 and liquidity > 0.5:
            return "buy"
        if rug_risk > 0.6:
            return "sell"
        return "pass"
    elif bot_name == "PUMP_CHASER":
        # Late momentum
        if change24h > 10:
            return "buy"
        if change24h < -15:
            return "sell"
        return "pass"
    elif bot_name == "CONVICTION":
        # Conviction check
        if score > 70:
            return "buy"
        if score < 30:
            return "sell"
        return "pass"
    elif bot_name == "MOMENTUM":
        # Momentum follower
        if change24h > 3:
            return "buy"
        if change24h < -5:
            return "sell"
        return "pass"
    elif bot_name == "SCALPER":
        # Short-term scalper
        if 2 <= abs(change24h) <= 8:
            return "buy" if change24h > 0 else "sell"
        return "pass"
    elif bot_name == "CONTRARIAN":
        # Contrarian
        if change24h > 10 and score > 60:
            return "sell"
        if change24h < -10:
            return "buy"
        return "pass"
    elif bot_name == "TREND":
        # Trend follower
        if change24h > 4 and volume > 0.6:
            return "buy"
        if change24h < -4:
            return "sell"
        return "pass"
    elif bot_name == "RESEARCHER":
        # Research
        if rug_risk < 0.35 and liquidity > 0.55:
            return "buy"
        if rug_risk > 0.65:
            return "sell"
        return "pass"
    elif bot_name == "PORTFOLIO":
        # Portfolio manager
        if score > 65 and rug_risk < 0.4:
            return "buy"
        if score < 35:
            return "sell"
        return "pass"
    elif bot_name == "EXECUTOR":
        # Executor (only acts on strong signals)
        if score > 80 and rug_risk < 0.25:
            return "buy"
        if score < 20 or rug_risk > 0.7:
            return "sell"
        return "hold"
    elif bot_name == "DEV_WATCH":
        # Dev watch (never trades, stands down)
        return "stand_down"

    return "pass"

# ── Market data generator ─────────────────────────────────────────
def generate_market() -> dict:
    """Generate a synthetic market state for a pump.fun token."""
    return {
        "symbol": f"GOBLIN#{random.randint(0,99):02d}",
        "score": random.uniform(40, 85),
        "rug_risk": random.uniform(0.1, 0.7),
        "liquidity": random.uniform(0.2, 1.0),
        "volume": random.uniform(0.2, 1.0),
        "change24h": random.uniform(-15, 20),
        "price": random.uniform(0.1, 0.9),
    }

# ── Main paper trading loop ───────────────────────────────────────
def run_session(minutes: float = 30.0, interval: float = 10.0, verbose: bool = True):
    """Run the paper trading session."""
    start = time.time()
    end = start + minutes * 60
    tick = 0
    last_html = 0
    html_interval = 30  # seconds between HTML updates

    print("=" * 62)
    print("  LYTA GROK DESK — PAPER TRADING RUNNER")
    print("  Press Ctrl+C to stop early")
    print("=" * 62)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Duration: {minutes} minutes")
    print(f"  Paper capital: $100.00")
    print(f"  Asset: GOBLIN")
    print(f"  Session interval: {interval} seconds")
    print("-" * 62)

    try:
        while time.time() < end:
            tick += 1
            now = time.time()
            market = generate_market()

            # Run all bots
            votes = {}
            for bot in BOT_NAMES:
                votes[bot] = run_bot(bot, market)

            # Update trading desk with this tick
            TRADE_DESK.set_alert(f"🎯 Tick {tick}: {market['symbol']} — score {market['score']:.0f}")

            # Add votes
            for bot, side in votes.items():
                TRADE_DESK.add_vote(bot, side)

            # Update capital based on market signal
            new_capital = TRADE_DESK.state.capital
            if market["change24h"] > 5:
                new_capital = TRADE_DESK.state.capital * 1.01
            elif market["change24h"] < -5:
                new_capital = TRADE_DESK.state.capital * 0.99
            TRADE_DESK.update_capital(new_capital)

            # Update timestamp
            TRADE_DESK.state.last_update = datetime.now()

            # Print live summary
            if verbose:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tick {tick}")
                print(TRADE_DESK.render(show_bot_votes=True))

            # Generate HTML dashboard periodically
            if now - last_html > html_interval:
                html = TRADE_DESK.to_html()
                with open("trading_desk.html", "w") as f:
                    f.write(html)
                last_html = now

            # Sleep until next tick
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nSession stopped by user.")
        print(f"Total ticks processed: {tick}")

    # Final summary
    print("\n" + "=" * 62)
    print("  SESSION COMPLETE")
    print("=" * 62)
    print(f"  Ticks processed: {tick}")
    print(f"  Final capital: ${TRADE_DESK.state.capital:.2f}")
    print(f"  Final asset: {TRADE_DESK.state.asset}")
    print(f"  Open positions: {len(TRADE_DESK.state.positions)}")
    print(f"  Total votes: {TRADE_DESK.state.vote_results['total']}")
    print(f"  Last update: {TRADE_DESK.state.last_update}")
    print(f"  Final HTML: trading_desk.html")
    print("=" * 62)

    # Save final HTML
    final_html = TRADE_DESK.to_html()
    with open("trading_desk.html", "w") as f:
        f.write(final_html)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LYTA Paper Trading Runner")
    parser.add_argument("--minutes", "-m", type=float, default=30.0,
                        help="Session duration in minutes (default: 30)")
    parser.add_argument("--interval", "-i", type=float, default=10.0,
                        help="Update interval in seconds (default: 10)")
    parser.add_argument("--once", action="store_true",
                        help="Run one tick and exit")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON (for machine parsing)")
    args = parser.parse_args()

    if args.once:
        market = generate_market()
        votes = {b: run_bot(b, market) for b in BOT_NAMES}
        TRADE_DESK.set_alert(f"🎯 One-shot tick")
        for bot, side in votes.items():
            TRADE_DESK.add_vote(bot, side)
        TRADE_DESK.update_capital(100.0 * (1 + market["change24h"] / 100))
        TRADE_DESK.set_alert("Session complete")
        if args.json:
            import json
            print(json.dumps(TRADE_DESK.to_dict(), indent=2))
        else:
            print(TRADE_DESK.render(show_bot_votes=True))
            final_html = TRADE_DESK.to_html()
            with open("trading_desk.html", "w") as f:
                f.write(final_html)
            print("\nHTML written to trading_desk.html")
    else:
        run_session(minutes=args.minutes, interval=args.interval)
