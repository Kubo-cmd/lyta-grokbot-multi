#!/usr/bin/env python3
"""
LYTA Trading Desk — command-line trading desk dashboard
=======================================================
Start a persistent trading-desk dashboard that watches the running paper
session (pumpfun_desk_simulator.py) and prints the overall summary every N
seconds, or renders a full HTML dashboard.

Usage:
    # Terminal mode: print the desk summary every 10 seconds
    python3 trading_desk.py

    # HTML mode: render a full HTML dashboard
    python3 trading_desk.py --html

    # One-shot (print summary once and exit)
    python3 trading_desk.py --once

The dashboard pulls state from TRADE_DESK in pumpfun_desk_simulator.py.
If the paper observer is not running, it starts with an empty desk.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Ensure we can import from the repo root.
# The lyta-grok-desk/ directory has a hyphen (not a valid Python package
# name), so we must use a dynamic import for the trading_desk module.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import importlib.util

# Load TradingDesk from the lyta-grok-desk directory (has a hyphen,
# so we load it as a file, not as a package).
_state_path = os.path.join(REPO_ROOT, "lyta-grok-desk", "trading_desk.py")
if os.path.exists(_state_path):
    _spec = importlib.util.spec_from_file_location("trading_desk", _state_path)
    if _spec is not None and _spec.loader is not None:
        _td_mod = importlib.util.module_from_spec(_spec)
        sys.modules["trading_desk"] = _td_mod
        _spec.loader.exec_module(_td_mod)
        TradingDesk = _td_mod.TradingDesk
    else:
        TradingDesk = None
else:
    TradingDesk = None

# Import pumpfun_desk_simulator to get the global TRADE_DESK instance
# (if it has already been imported, we use its TRADE_DESK; otherwise we
#  create our own fresh desk).
try:
    import pumpfun_desk_simulator as _pfd
    TRADE_DESK = _pfd.TRADE_DESK
except ImportError:
    if TradingDesk is None:
        raise
    TRADE_DESK = TradingDesk(capital=6.0, asset="GOBLIN", config="v3")


def run_terminal(interval: float = 10.0, once: bool = False) -> None:
    """Print the desk summary every `interval` seconds."""
    if once:
        print(TRADE_DESK.render())
        return

    print("=" * 62)
    print("  LYTA TRADING DESK — live monitor (Ctrl+C to stop)")
    print("=" * 62)
    try:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}]")
            print(TRADE_DESK.render(show_bot_votes=True))
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nDesk monitor stopped.")


def run_html(output_path: str = "trading_desk.html") -> None:
    """Render the full HTML dashboard to `output_path`."""
    html = TRADE_DESK.to_html()
    with open(output_path, "w") as f:
        f.write(html)
    print(f"HTML dashboard written to: {os.path.abspath(output_path)}")
    print(f"Open it in a browser to see the live trading desk summary.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LYTA Trading Desk — overall summary dashboard"
    )
    parser.add_argument(
        "--interval", "-i", type=float, default=10.0,
        help="Update interval in seconds (terminal mode)",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Render HTML dashboard instead of terminal",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Print one summary and exit",
    )
    parser.add_argument(
        "--output", "-o", default="trading_desk.html",
        help="Output HTML file path (with --html)",
    )
    args = parser.parse_args()

    if args.html:
        run_html(args.output)
    elif args.once:
        print(TRADE_DESK.render())
    else:
        run_terminal(interval=args.interval)
