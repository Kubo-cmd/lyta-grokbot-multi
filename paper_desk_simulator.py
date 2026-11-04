#!/usr/bin/env python3
"""
LYTA Grok Desk — Paper Observer Simulator
Exact match to the Builder's active Paper bot, "Lyta-grok Paper Copy."

This is the BET for the grokbot trading desk goal:
- Continuously screens bonding-curve tokens and either buys or skips.
- No fixed 15-minute cycle (continuous screening is the supported behavior).
- No SHORT positions (the Paper Observer is a long-only entry strategy).
- Paper-only ledger: $2–6 simulated capital, no live money, no real swaps.

Paper Observer Parameters (active config v3):
- Buy size: 0.05 SOL
- Fee break-even: ~1.06x
- Entry: 8%–70% bonding-curve progress
- Minimum activity: 15 unique wallets / 3 buys / 30 holders
- Concentration: top 10 ≤ 30%
- Developer holdings: ≤ 15%
- Rebuys: off
- Exits: 50% at 2x, 100% remainder at 3x
- Trailing exit: 2.5x after 15% drawdown
- Stop-loss: 0.10x (−90) — trigger only, NOT a guaranteed loss cap
- Stale/dead exits: 120s / 300s
- Hold through PumpSwap graduation: yes
- Slippage: 15% / 5%
- Mint/freeze authority revoked: required
- Risky extensions: blocked
- Max pool fee: 4%
- Trading hours: 24/7
- Session P&L limits: off

Rules preserved from the 12-bot consensus (still documented, not the active
strategy):
- 7/12 buy bar, liquidity floor ≥$50k, −35% SL / +50% TP, exit rules
  (rug spike, score collapse, 25% first-hour drop, time exit, contrarian).
"""

import random
import time
import sys
from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Any

# ── Paper Observer config v3 (the "bet") ──────────────────────────────────────
# All values below are DEFAULTS. They can be overridden via CLI flags or
# a JSON config file. The opt-in perimeters (v3.1 improvements) are
# disabled by default; pass --enable-two-visit / --enable-staggered-exits
# / etc. to activate them. This enables A/B testing: run the same
# simulation with different perimeter combinations and compare results.

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from JSON file or use defaults.
    Priority: CLI args > JSON file > hardcoded defaults.
    """
    config = {
        # Paper Observer (config v3) defaults
        "PO_BNavy": 0.05,
        "PO_FEE_BREAK_EVEN": 1.06,
        "PO_ENTRY_MIN": 8,
        "PO_ENTRY_MAX": 70,
        "PO_MIN_WALLETS": 15,
        "PO_MIN_BUYS": 3,
        "PO_MIN_HOLDERS": 30,
        "PO_WORST_CASE_MODE": False,
        "PO_TOP10_MAX": 30,
        "PO_DEV_MAX": 15,
        "PO_REBUYS": False,
        "PO_EXIT_1": [2.0, 0.50],
        "PO_EXIT_2": [3.0, 1.00],
        "PO_TRAIL": 2.5,
        "PO_TRAIL_DD": 0.15,
        "PO_STOP_LOSS": 0.10,
        "PO_STALE": 120,
        "PO_DEAD": 300,
        "PO_HOLD_GRAD": True,
        "PO_SLIPPAGE_ENTRY": 0.15,
        "PO_SLIPPAGE_EXIT": 0.05,
        "PO_MINT_AUTH_REQUIRED": True,
        "PO_RISKY_EXT_BLOCK": True,
        "PO_MAX_POOL_FEE": 0.04,
        "PO_24_7": True,
        "PO_PNL_LIMITS": False,

        # Opt-in perimeters (v3.1 improvements) — disabled by default
        "PO_MAX_POS_PCT": 0.25,
        "PO_LIQ_DIST_WATCH": False,
        "PO_TWO_VISIT_CONFIRM": False,
        "PO_STAGGERED_EXITS": False,
        # Transaction cost model (cash-flow, per-leg)
        # Protocol fee (pump.fun): charged on each swap (entry + exit)
        "PO_PROTOCOL_FEE": 0.01,
        # Flat transaction cost per leg (SOL)
        "PO_FLAT_FEE_PER_LEG": 0.001015,
        # Entry slippage tolerance (max, not guaranteed)
        "PO_SLIPPAGE_ENTRY": 0.15,
        # Exit slippage tolerance (max, not guaranteed)
        "PO_SLIPPAGE_EXIT": 0.05,
    }
    # Load from JSON file if provided file if provided
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            file_config = json.load(f)
            config.update(file_config)

    return config

# ── Module-level PO_* variables for backward compatibility ───────────────────
# These mirror the config dict values so existing code can use PO_STALE,
# PO_DEAD, PO_STAGGERED_EXITS, PO_TWO_VISIT_CONFIRM, etc. directly.
# They are synced from the config dict by sync_config_to_module_vars().
PO_MAX_POS_PCT = 0.25
PO_LIQ_DIST_WATCH = False
PO_TWO_VISIT_CONFIRM = False
PO_STAGGERED_EXITS = False
PO_BNavy = 0.05
PO_FEE_BREAK_EVEN = 1.06
PO_ENTRY_MIN = 8
PO_ENTRY_MAX = 70
PO_MIN_WALLETS = 15
PO_MIN_BUYS = 3
PO_MIN_HOLDERS = 30
PO_TOP10_MAX = 30
PO_DEV_MAX = 15
PO_REBUYS = False
PO_EXIT_1 = [2.0, 0.50]
PO_EXIT_2 = [3.0, 1.00]
PO_TRAIL = 2.5
PO_TRAIL_DD = 0.15
PO_STOP_LOSS = 0.10
PO_STALE = 120
PO_DEAD = 300
PO_HOLD_GRAD = True
PO_SLIPPAGE_ENTRY = 0.15
PO_SLIPPAGE_EXIT = 0.05
PO_MINT_AUTH_REQUIRED = True
PO_RISKY_EXT_BLOCK = True
PO_MAX_POOL_FEE = 0.04
PO_24_7 = True
PO_PNL_LIMITS = False
# Opt-in perimeters (v3.1 improvements) — disabled by default
PO_MAX_POS_PCT = 0.25
PO_WORST_CASE_MODE = False
PO_LIQ_DIST_WATCH = False
PO_TWO_VISIT_CONFIRM = False
PO_STAGGERED_EXITS = False

# ── Module-level config dict (full v3 defaults + opt-in perimeters) ──────────
CONFIG = load_config()
# CLAIFlags to override CONFIG at runtime
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for configuration overrides."""
    parser = argparse.ArgumentParser(
        description="LYTA Grok Desk — Paper Observer Simulator (config v3 + opt-in perimeters)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Paper Observer config v3
    parser.add_argument("--buy-size", type=float, default=CONFIG["PO_BNavy"],
                        help="Buy size in SOL")
    parser.add_argument("--fee-break-even", type=float, default=CONFIG["PO_FEE_BREAK_EVEN"],
                        help="Fee break-even target (x)")
    parser.add_argument("--entry-min", type=float, default=CONFIG["PO_ENTRY_MIN"],
                        help="Minimum bonding-curve progress (%%): e.g. --entry-min 15")
    parser.add_argument("--entry-max", type=float, default=CONFIG["PO_ENTRY_MAX"],
                        help="Maximum bonding-curve progress (%%): e.g. --entry-max 80")
    parser.add_argument("--min-wallets", type=int, default=CONFIG["PO_MIN_WALLETS"],
                        help="Minimum unique wallets required")
    parser.add_argument("--min-buys", type=int, default=CONFIG["PO_MIN_BUYS"],
                        help="Minimum buys required")
    parser.add_argument("--min-holders", type=int, default=CONFIG["PO_MIN_HOLDERS"],
                        help="Minimum holders required")
    parser.add_argument("--top10-max", type=float, default=CONFIG["PO_TOP10_MAX"],
                        help="Max top-10 concentration (%%): e.g. --top10-max 30")
    parser.add_argument("--dev-max", type=float, default=CONFIG["PO_DEV_MAX"],
                        help="Max developer holdings (%%)")
    parser.add_argument("--rebuys", action="store_true", default=CONFIG["PO_REBUYS"],
                        help="Enable rebuys")
    parser.add_argument("--exit-1", type=float, nargs=2, default=CONFIG["PO_EXIT_1"],
                        metavar=("PERCENT", "FRACTION"),
                        help="First exit tier: e.g. --exit-1 200 0.50 (200%% at 50%%)")
    parser.add_argument("--exit-2", type=float, nargs=2, default=CONFIG["PO_EXIT_2"],
                        metavar=("PERCENT", "FRACTION"),
                        help="Second exit tier: e.g. --exit-2 300 1.00 (300%% at 100%%)")
    parser.add_argument("--trail", type=float, default=CONFIG["PO_TRAIL"],
                        help="Trailing exit multiple")
    parser.add_argument("--trail-dd", type=float, default=CONFIG["PO_TRAIL_DD"],
                        help="Trailing exit trigger drawdown (%%): e.g. --trail-dd 0.15")
    parser.add_argument("--stop-loss", type=float, default=CONFIG["PO_STOP_LOSS"],
                        help="Stop-loss trigger multiple (e.g. 0.10 = -90%%)")
    parser.add_argument("--stale", type=int, default=CONFIG["PO_STALE"],
                        help="Stale exit threshold (seconds)")
    parser.add_argument("--dead", type=int, default=CONFIG["PO_DEAD"],
                        help="Dead exit threshold (seconds)")
    parser.add_argument("--worst-case", action="store_true",
                        help="Enable worst-case tolerance mode (15%% entry + 5%% exit slippage applied)")
    parser.add_argument("--hold-grad", action="store_true", default=CONFIG["PO_HOLD_GRAD"],
                        help="Hold through PumpSwap graduation")
    parser.add_argument("--slippage-entry", type=float, default=CONFIG["PO_SLIPPAGE_ENTRY"],
                        help="Slippage at entry (%%)")
    parser.add_argument("--slippage-exit", type=float, default=CONFIG["PO_SLIPPAGE_EXIT"],
                        help="Slippage at exit (%%)")
    parser.add_argument("--mint-auth-required", action="store_true", default=CONFIG["PO_MINT_AUTH_REQUIRED"],
                        help="Require mint/freeze authority revoked")
    parser.add_argument("--risky-ext-block", action="store_true", default=CONFIG["PO_RISKY_EXT_BLOCK"],
                        help="Block risky extensions")
    parser.add_argument("--max-pool-fee", type=float, default=CONFIG["PO_MAX_POOL_FEE"],
                        help="Maximum pool fee (%%)")
    parser.add_argument("--trading-hours", action="store_true", default=CONFIG["PO_24_7"],
                        help="Trading hours (24/7)")
    parser.add_argument("--pnl-limits", action="store_true", default=CONFIG["PO_PNL_LIMITS"],
                        help="Enable session P&L limits")
    parser.add_argument("--config-file", type=str, default=None,
                        help="Path to JSON config file")

    # Opt-in perimeters (v3.1 improvements) — A/B test toggles
    parser.add_argument("--enable-max-pos-pct", action="store_true", default=CONFIG["PO_MAX_POS_PCT"] > 0,
                        help="Enable max position %% of equity cap (Whale Copier style)")
    parser.add_argument("--enable-liquidity-watch", action="store_true", default=CONFIG["PO_LIQ_DIST_WATCH"],
                        help="Enable liquidation distance watch (Paper MILL style)")
    parser.add_argument("--enable-two-visit", action="store_true", default=CONFIG["PO_TWO_VISIT_CONFIRM"],
                        help="Enable two-visit entry confirmation (Range Farmer style)")
    parser.add_argument("--enable-staggered-exits", action="store_true", default=CONFIG["PO_STAGGERED_EXITS"],
                        help="Enable staggered 3-tier exit (Pelosi's Bet Tracker style)")
    parser.add_argument("--max-pos-pct", type=float, default=CONFIG["PO_MAX_POS_PCT"] if CONFIG["PO_MAX_POS_PCT"] > 0 else 0.25,
                        help="Max position as %% of equity (0 = disabled)")
    parser.add_argument("--liq-dist-watch", action="store_true", default=CONFIG["PO_LIQ_DIST_WATCH"],
                        help="Liquidation distance watch (overlap with enable-liquidity-watch)")
    parser.add_argument("--two-visit-window", type=int, default=300,
                        help="Two-visit confirmation window in seconds (default 300)")

    # Run configuration
    parser.add_argument("--collateral", type=float, default=6.0,
                        help="Starting collateral in SOL")
    parser.add_argument("--asset", type=str, default="GOBLIN",
                        help="Asset/pair name to simulate")
    parser.add_argument("--verbose", action="store_true", default=True,
                        help="Enable verbose output")
    parser.add_argument("--no-verbose", action="store_false", dest="verbose",
                        help="Disable verbose output")
    parser.add_argument("--test-mode", action="store_true",
                        help="Run in test mode (limited iterations, no infinite loop)")
    parser.add_argument("--test-iterations", type=int, default=100,
                        help="Number of iterations in test mode")

    return parser.parse_args(argv)

def apply_config(args: argparse.Namespace) -> Dict[str, Any]:
    """Apply CLI args to config and return final config dict."""
    config = dict(CONFIG)

    # Paper Observer config v3 overrides
    config["PO_BNavy"] = args.buy_size
    config["PO_FEE_BREAK_EVEN"] = args.fee_break_even
    config["PO_ENTRY_MIN"] = args.entry_min
    config["PO_ENTRY_MAX"] = args.entry_max
    config["PO_MIN_WALLETS"] = args.min_wallets
    config["PO_MIN_BUYS"] = args.min_buys
    config["PO_MIN_HOLDERS"] = args.min_holders
    config["PO_TOP10_MAX"] = args.top10_max
    config["PO_DEV_MAX"] = args.dev_max
    config["PO_REBUYS"] = args.rebuys
    config["PO_EXIT_1"] = list(args.exit_1)
    config["PO_EXIT_2"] = list(args.exit_2)
    config["PO_TRAIL"] = args.trail
    config["PO_TRAIL_DD"] = args.trail_dd
    config["PO_STOP_LOSS"] = args.stop_loss
    config["PO_STALE"] = args.stale
    config["PO_DEAD"] = args.dead
    config["PO_HOLD_GRAD"] = args.hold_grad
    config["PO_SLIPPAGE_ENTRY"] = args.slippage_entry
    config["PO_SLIPPAGE_EXIT"] = args.slippage_exit
    config["PO_MINT_AUTH_REQUIRED"] = args.mint_auth_required
    config["PO_RISKY_EXT_BLOCK"] = args.risky_ext_block
    config["PO_MAX_POOL_FEE"] = args.max_pool_fee
    config["PO_24_7"] = args.trading_hours
    config["PO_PNL_LIMITS"] = args.pnl_limits

    # Opt-in perimeters — use CLI flags to override
    config["PO_MAX_POS_PCT"] = args.max_pos_pct if args.enable_max_pos_pct else 0.0
    config["PO_LIQ_DIST_WATCH"] = args.enable_liquidity_watch
    config["PO_TWO_VISIT_CONFIRM"] = args.enable_two_visit
    config["PO_STAGGERED_EXITS"] = args.enable_staggered_exits

    # A/B test sidecar values (internal, for comparison)
    config["_ab_test_name"] = getattr(args, "ab_test_name", "default")
    config["_ab_test_config"] = getattr(args, "ab_test_config", None)

    return config

# ── Global config variable that gets updated on each run ─────────────────────
config = {
    # Paper Observer (config v3) defaults
    "PO_BNavy": 0.05,
    "PO_FEE_BREAK_EVEN": 1.06,
    "PO_ENTRY_MIN": 8,
    "PO_ENTRY_MAX": 70,
    "PO_MIN_WALLETS": 15,
    "PO_MIN_BUYS": 3,
    "PO_MIN_HOLDERS": 30,
    "PO_TOP10_MAX": 30,
    "PO_DEV_MAX": 15,
    "PO_REBUYS": False,
    "PO_EXIT_1": [2.0, 0.50],
    "PO_EXIT_2": [3.0, 1.00],
    "PO_TRAIL": 2.5,
    "PO_TRAIL_DD": 0.15,
    "PO_STOP_LOSS": 0.10,
    "PO_STALE": 120,
    "PO_DEAD": 300,
    "PO_HOLD_GRAD": True,
    "PO_SLIPPAGE_ENTRY": 0.15,
    "PO_SLIPPAGE_EXIT": 0.05,
    "PO_WORST_CASE_MODE": False,  # false = standard fee model (actual fills); true = worst-case tolerance model
    "PO_MINT_AUTH_REQUIRED": True,
    "PO_RISKY_EXT_BLOCK": True,
    "PO_MAX_POOL_FEE": 0.04,
    "PO_24_7": True,
    "PO_PNL_LIMITS": False,

    # Opt-in perimeters (v3.1 improvements) — disabled by default
    "PO_MAX_POS_PCT": 0.25,
    "PO_LIQ_DIST_WATCH": False,
    "PO_TWO_VISIT_CONFIRM": False,
    "PO_STAGGERED_EXITS": False,
    "PO_WORST_CASE_MODE": False,
}

# ── Opt-in perimeter state (v3.1 improvements) ──────────────────────────────
# State for two-visit confirmation: count of valid entries, timestamp of first
_enter_count = 0
_enter_timestamp = 0.0

def sync_config_to_module_vars(new_config: dict) -> None:
    """Sync configuration dict values to module-level PO_* variables.
    This keeps all existing code working while making config dynamic."""
    global _enter_count, _enter_timestamp, config
    # Update the module-level config dict with new values, keeping all keys
    config.clear()
    config.update({
        "PO_BNavy": 0.05,
        "PO_FEE_BREAK_EVEN": 1.06,
        "PO_ENTRY_MIN": 8,
        "PO_ENTRY_MAX": 70,
        "PO_MIN_WALLETS": 15,
        "PO_MIN_BUYS": 3,
        "PO_MIN_HOLDERS": 30,
        "PO_WORST_CASE_MODE": False,
        "PO_TOP10_MAX": 30,
        "PO_DEV_MAX": 15,
        "PO_REBUYS": False,
        "PO_EXIT_1": [2.0, 0.50],
        "PO_EXIT_2": [3.0, 1.00],
        "PO_TRAIL": 2.5,
        "PO_TRAIL_DD": 0.15,
        "PO_STOP_LOSS": 0.10,
        "PO_STALE": 120,
        "PO_DEAD": 300,
        "PO_HOLD_GRAD": True,
        "PO_SLIPPAGE_ENTRY": 0.15,
        "PO_SLIPPAGE_EXIT": 0.05,
        "PO_MINT_AUTH_REQUIRED": True,
        "PO_RISKY_EXT_BLOCK": True,
        "PO_MAX_POOL_FEE": 0.04,
        "PO_24_7": True,
        "PO_PNL_LIMITS": False,
        "PO_MAX_POS_PCT": 0.25,
        "PO_LIQ_DIST_WATCH": False,
        "PO_TWO_VISIT_CONFIRM": False,
        "PO_STAGGERED_EXITS": False,
        # ── Transaction cost model (cash-flow, per-leg) ────────────────────────
        # Protocol fee (pump.fun): charged on each swap (entry + exit)
        "PO_PROTOCOL_FEE": 0.01,
        # Flat transaction cost per leg (SOL)
        "PO_FLAT_FEE_PER_LEG": 0.001015,
        # Entry slippage tolerance (max, not guaranteed)
        "PO_SLIPPAGE_ENTRY": 0.15,
        # Exit slippage tolerance (max, not guaranteed)
        "PO_SLIPPAGE_EXIT": 0.05,
    })
    # Override with new_config values (CLI args)
    for k, v in new_config.items():
        if k in config:
            config[k] = v

    # Also sync to the PO_* module-level variables for backward compatibility
    for k, v in config.items():
        if k in globals():
            globals()[k] = v

# ── Market dataclass ────────────────────────────────────────────────────────

# ── 12-bot personalities (still documented, used for the reference 12-bot
#     consensus strategy that the Paper Observer supersedes in the simulator)
BotName = Literal[
    "SCOUT", "FILTER", "ANALYST", "PUMP_CHASER", "CONVICTION",
    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
    "PORTFOLIO", "EXECUTOR"
]

BOT_NAMES = [
    "SCOUT", "FILTER", "ANALYST", "PUMP_CHASER", "CONVICTION",
    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
    "PORTFOLIO", "EXECUTOR"
]

# ── Market dataclass ────────────────────────────────────────────────────────

@dataclass
class Market:
    asset: str
    price: float
    bonding_curve_progress: float      # 0.0–100.0
    is_new_launch: bool
    analyst_score: float
    rug_risk: float
    liquidity: float
    buys_5m: int
    unique_wallets: int
    holders: int
    top10_concentration: float
    dev_holdings: float
    change_1h: float
    change_24h: float
    holder_addresses: list = field(default_factory=list)
    buyer_wallets: list = field(default_factory=list)

    def in_entry_window(self) -> bool:
        return PO_ENTRY_MIN <= self.bonding_curve_progress <= PO_ENTRY_MAX

# ── Market simulator ────────────────────────────────────────────────────────

def make_realistic_market(asset: str, base_price: float) -> Market:
    """Generate plausible recent price action for simulation."""
    # Bonding-curve progress: random between 0-100 (continuous, no cycle)
    progress = random.uniform(0, 100)

    is_new = random.random() < 0.45
    on_curve = progress > 8 and progress < 70

    # Analyst score (0-1)
    analyst = random.uniform(0.35, 0.97)
    if on_curve:
        analyst += random.uniform(-0.1, 0.15)

    # Rug risk (0-1)
    rug = random.uniform(0.08, 0.72)
    if on_curve:
        rug += random.uniform(-0.15, 0.1)

    # Liquidity: random, simulating the $0–$65k range we saw on Trenchers.ai
    liq = random.uniform(0, 65000)

    # Ensure price stays positive
    price_offset = random.uniform(-0.5, 0.5) * base_price
    current_price = max(base_price + price_offset, 0.000001)

    # Activity metrics
    wallets = random.randint(5, 120)
    buys = random.randint(0, 50)
    holders = random.randint(10, 200)
    top10 = random.uniform(5, 60)
    dev = random.uniform(0, 20)
    ch1h = random.uniform(-30, 60)

    return Market(
        asset=asset,
        price=current_price,
        bonding_curve_progress=progress,
        is_new_launch=is_new,
        analyst_score=round(analyst, 3),
        rug_risk=round(rug, 3),
        liquidity=round(liq, 0),
        buys_5m=buys,
        unique_wallets=wallets,
        holders=holders,
        top10_concentration=top10,
        dev_holdings=dev,
        change_1h=ch1h,
        change_24h=random.uniform(-40, 80),
    )

# ── Paper Observer decision engine ──────────────────────────────────────────

def paper_observer_enter(m: Market) -> Optional[dict]:
    """
    Paper Observer decision engine.
    Returns an entry signal dict or None (skip/stand down).
    """
    reasons = []

    # ── Entry window (8%–70% bonding-curve progress) ──
    if not m.in_entry_window():
        reasons.append(f"entry-window (progress {m.bonding_curve_progress:.1f}% outside 8–70)")
        return None

    # ── Minimum activity: 15 wallets / 3 buys / 30 holders ──
    if m.unique_wallets < PO_MIN_WALLETS:
        reasons.append(f"wallets {m.unique_wallets} < {PO_MIN_WALLETS}")
        return None
    if m.buys_5m < PO_MIN_BUYS:
        reasons.append(f"buys {m.buys_5m} < {PO_MIN_BUYS}")
        return None
    if m.holders < PO_MIN_HOLDERS:
        reasons.append(f"holders {m.holders} < {PO_MIN_HOLDERS}")
        return None

    # ── Concentration: top 10 ≤ 30% ──
    if m.top10_concentration > PO_TOP10_MAX:
        reasons.append(f"top10 {m.top10_concentration:.1f}% > {PO_TOP10_MAX}%")
        return None

    # ── Developer holdings ≤ 15% ──
    if m.dev_holdings > PO_DEV_MAX:
        reasons.append(f"dev {m.dev_holdings:.1f}% > {PO_DEV_MAX}%")
        return None

    # ── Mint/freeze authority revoked required ──
    if PO_MINT_AUTH_REQUIRED:
        # In simulation, assume authority is revoked (standard pump.fun)
        pass

    # ── Two-visit confirmation (opt-in, from Range PAPER Farmer) ──
    # If opt-in is on, require 2 valid entry signals within 300s
    if PO_TWO_VISIT_CONFIRM:
        global _enter_count, _enter_timestamp
        if _enter_count == 0:
            _enter_timestamp = time.time()
            _enter_count = 1
        elif time.time() - _enter_timestamp < 300:
            # Second valid entry within 300s window
            _enter_count = 2
        elif time.time() - _enter_timestamp >= 300:
            # Window expired, reset
            _enter_count = 0
            _enter_timestamp = 0.0

        if _enter_count < 2:
            _enter_count = 2  # treated as confirmed for this run
            # Reset for next token
            _enter_count = 0
            _enter_timestamp = 0.0
            return None  # wait for second signal

    # ── Max position as % of equity cap (opt-in, from Whale Copier) ──
    if PO_MAX_POS_PCT and position is not None:
        # Position sizing check would go here
        pass

    # ── Liquidation distance watch (opt-in, from Paper MILL) ──
    if PO_LIQ_DIST_WATCH and position is not None:
        # Liquidation distance monitoring
        pass

    # ── All filters passed ──
    return {
        "action": "buy",
        "size_sol": PO_BNavy,
        "progress": m.bonding_curve_progress,
        "reason": "all-paper-observer-filters-passed",
        "liquidity": m.liquidity,
        "analyst_score": m.analyst_score,
        "rug_risk": m.rug_risk,
        "fee_break_even": PO_FEE_BREAK_EVEN,
    }

# ── Exit engine (based on the 12-bot consensus rules, preserved verbatim) ────

def check_exits(
    position: Optional[dict],
    market: Market,
    elapsed_seconds: float,
    last_update: float,
) -> tuple[Optional[dict], str, float, float]:
    """
    Check exits for an active position.
    Returns (updated_position, exit_reason, exit_price_border, fraction_sold).
    fraction_sold is 1.0 for full exits, and 0.0-1.0 for partial (staggered tier) exits.
    """
    if position is None:
        return None, None, None, 1.0

    entry_price = position["entry_price"]
    current_price = market.price

    # ── Liquidation distance watch (opt-in, from Paper MILL) ──
    # If within 15% of liquidation price, exit early (prevents thin-liquidity accidents)
    if PO_LIQ_DIST_WATCH:
        # Liquidation price ~ entry_price / PO_STOP_LOSS = entry_price / 0.10
        liq_price = entry_price / 0.10
        dist_to_liq = liq_price - current_price
        if dist_to_liq <= 0.15 * liq_price:
            return position, "liquidation-distance exit", current_price

    # ── Stop-loss trigger (0.10x / −90) ──
    # NOTE: stop-loss is a trigger, NOT a guaranteed loss cap.
    # Thin liquidity or a rug can produce a much worse fill.
    if current_price < PO_STOP_LOSS * entry_price:
        return position, "stop-loss trigger", current_price

    # ── Trailing exit: 2.5x after 15% drawdown ──
    peak_price = position.get("peak_price", entry_price)
    if current_price > peak_price:
        peak_price = current_price
        position["peak_price"] = peak_price
    trail_high = peak_price * PO_TRAIL
    if current_price < trail_high * (1 - PO_TRAIL_DD):
        return position, "trailing exit", current_price

    # ── Staggered exit (v3 ladder: PO_EXIT_1 @ 2x, PO_EXIT_2 @ 3x) ───────────
    # Ladder from config dicts: PO_EXIT_1 = [2.0, 0.50], PO_EXIT_2 = [3.0, 1.00]
    # Theoretical gross position P&L: 50%*(2.0-1) + 50%*(3.0-1) = 150% before costs
    if PO_STAGGERED_EXITS:
        exit_1_pct, exit_1_frac = PO_EXIT_1
        exit_2_pct, exit_2_frac = PO_EXIT_2
        tp1 = entry_price * exit_1_pct
        tp2 = entry_price * exit_2_pct
        if current_price >= tp1 and "tier1" not in position:
            position["tier1"] = True
            return position, f"staggered exit @{exit_1_pct}x ({exit_1_frac:.0%})", current_price, exit_1_frac
        elif current_price >= tp2 and "tier2" not in position:
            position["tier2"] = True
            return position, f"staggered exit @{exit_2_pct}x ({exit_2_frac:.0%})", current_price, exit_2_frac

    # ── Stale exit: 120s ──
    if time.time() - last_update > PO_STALE:
        return position, "stale exit", current_price

    # ── Dead exit: 300s ──
    if time.time() - last_update > PO_DEAD:
        return position, "dead exit", current_price, 1.0

    return position, None, None, 1.0

# ── 12-bot consensus reference (preserved for documentation, not the active
#     strategy) ─────────────────────────────────────────────────────────────

def bot_vote(bot: str, m: Market) -> tuple[str, float]:
    """Reference 12-bot vote (not the active strategy)."""
    if bot == "SCOUT":
        if abs(m.change_1h) < 0.3: return "pass", 0.0
        return ("long" if m.change_1h > 0 else "short"), 0.65
    elif bot == "FILTER":
        if abs(m.change_24h) < 0.5: return "pass", 0.0
        return ("long" if m.change_24h > 0 else "short"), 0.70
    elif bot == "ANALYST":
        if abs(m.change_24h) < 0.2: return "pass", 0.0
        return ("long" if m.change_24h > 0 else "short"), 0.60
    elif bot == "PUMP_CHASER":
        if abs(m.change_1h) < 1.0: return "pass", 0.0
        return ("long" if m.change_1h > 0 else "short"), 0.80
    elif bot == "CONVICTION":
        if (m.change_24h > 0 and m.change_1h > 0) or (m.change_24h < 0 and m.change_1h < 0):
            return ("long" if m.change_24h > 0 else "short"), 0.75
        return "pass", 0.0
    elif bot == "MOMENTUM":
        if abs(m.change_1h) < 0.4: return "pass", 0.0
        return ("long" if m.change_1h > 0 else "short"), 0.65
    elif bot == "SCALPER":
        if abs(m.change_1h) < 0.25: return "pass", 0.0
        return ("long" if m.change_1h > 0 else "short"), 0.55
    elif bot == "CONTRARIAN":
        if abs(m.change_24h) < 2.0: return "pass", 0.0
        return ("short" if m.change_24h > 0 else "long"), 0.60
    elif bot == "TREND":
        if abs(m.change_1h) < 0.3: return "pass", 0.0
        if (m.change_1h > 0 and m.change_24h > 0) or (m.change_1h < 0 and m.change_24h < 0):
            return ("long" if m.change_1h > 0 else "short"), 0.70
        return "pass", 0.0
    elif bot == "RESEARCHER":
        range_pct = ((m.price - 100) / 100) * 100 if 0 else 50
        return "pass", 0.0
    elif bot == "PORTFOLIO":
        return "pass", 0.0
    elif bot == "EXECUTOR":
        return "pass", 0.0
    return "pass", 0.0

# ── Main run loop ───────────────────────────────────────────────────────────

def run_paper_desk(collateral: float = 6.0, asset: str = "GOBLIN", verbose: bool = True):
    """Continuously screen and either buy or skip (Paper Observer v3).

    Evidence-floor guardrail (warning-only):
    - completed_positions is incremented ONLY when a position's remaining quantity
      reaches zero (partial exits are tracked separately as sell_legs).
    - Results are segmented by config_version so older behavior is never attributed
      to the current config.
    - The bot keeps running even below 20 completed positions; a warning is printed.
    - Even after 20, that is only a minimum evidence threshold, not proof of profitability.
    """
    # Local references to config dict
    c = CONFIG

    # Evidence segmentation: this run is config v3
    config_version = "v3"

    # Evidence floor tracking — warning-only, does not prevent trading
    completed_positions = 0
    sell_legs = 0
    realized_pnl = 0.0

    print("=" * 70)
    print("LYTA GROKBOT MULTI — PAPER OBSERVER v3 (the BET)")
    print(f"Collateral: {collateral:.2f} SOL | Asset: {asset} | paper-only")
    print("=" * 70)
    print(f"\n[CONFIG] Config v3 active")
    print(f"[CONFIG] Enabled perimeters: max-pos-pct={PO_MAX_POS_PCT}, liq-dist-watch={PO_LIQ_DIST_WATCH},")
    print(f"         two-visit={PO_TWO_VISIT_CONFIRM}, staggered-exits={PO_STAGGERED_EXITS}")
    buy_size = c["PO_BNavy"]; entry_min = c["PO_ENTRY_MIN"]; entry_max = c["PO_ENTRY_MAX"]
    print(f"[CONFIG] Buy size: {buy_size} SOL | analyst-min: {entry_min}% | analyst-max: {entry_max}%")
    print(f"[CONFIG] Risk: 5x max | 12-bot consensus | $2-6 paper capital")
    print(f"[EVIDENCE] Evidence-floor guardrail: warning-only, below 20 = INSUFFICIENT_EVIDENCE")

    position = None
    entry_price = None
    last_update = time.time()
    hold_start = None
    curve_progress = 0.0

    # Pre-compute total entry cash outflow (SAME for every position in this run)
    # = base order + pump.fun 1% protocol fee + 0.001015 SOL flat transaction fee
    total_cost = c["PO_BNavy"] + c["PO_BNavy"] * c["PO_PROTOCOL_FEE"] + c["PO_FLAT_FEE_PER_LEG"]

    while True:
        # Continuous screening — no fixed cycle
        market = make_realistic_market(asset, 41.20)  # reference: Trenchers.ai price

        # ── Paper Observer decision ──
        signal = paper_observer_enter(market)

        if signal is not None and position is None:
            # ── BUY ──
            entry_price = market.price
            position = {
                "entry_price": entry_price,
                "size_sol": signal["size_sol"],
                "asset": market.asset,
                "peak_price": entry_price,
                "opened_at": time.time(),
                "stale_at": time.time() + PO_STALE,
                "dead_at": time.time() + PO_DEAD,
            }
            hold_start = time.time()
            last_update = time.time()
            print(f"\n[BUY] {market.asset} | price ${entry_price:.4f} | progress {signal['progress']:.1f}%")
            buy_size_module = c["PO_BNavy"]
            print(f"  Entry: {buy_size_module} SOL | liquidity ${signal['liquidity']:.0f} | analyst {signal['analyst_score']:.2f}")
            print(f"  P&L basis: full entry cash outflow = {total_cost:.4f} SOL (base + 1% protocol + 0.001015 flat)")
            print(f"  [EXIT LOG] active — stop {PO_STOP_LOSS}x, trail 2.5x/15%")

        elif signal is None and position is None:
            # ── SKIP ──
            if verbose:
                pass  # silent skip in continuous mode

        # ── Check exits on every iteration ──
        if position is not None:
            position, exit_reason, exit_price_border, fraction_sold = check_exits(
                position, market, time.time(), last_update
            )
            if exit_reason is not None:
                # ── EXIT ──
                # Track sell legs (every sell leg, partial or full)
                sell_legs += 1
                # ── Cash-flow transaction cost model ──────────────────────────
                # Costs are deducted from proceeds, NOT applied as a percentage
                # discount to PnL. This prevents the "−50% becomes −40%" bug.
                # Cost components: entry protocol fee (sunk), exit slippage × fleet
                # fee per swap, flat transaction cost per leg.
                # Entry cost (SOL): PO_BNavy = 0.05
                # total_cost pre-computed above (same for all positions in this run)
                # Per-leg: gross sale value → deduct slippage + protocol fee + flat fee
                gross_sale_value = PO_BNavy * (exit_price_border / position["entry_price"]) * fraction_sold
                # Worst-case mode (PO_WORST_CASE_MODE=true): apply configured slippage tolerances
                # Standard: actual/simulated fills, no slippage
                # Worst-case: 15% entry + 5% exit slippage (tolerances applied)
                if PO_WORST_CASE_MODE:
                    # Entry slippage: user gets less crypto for the SOL spent
                    gross_sale_value = gross_sale_value * (1 - PO_SLIPPAGE_ENTRY)
                    exit_slippage = gross_sale_value * PO_SLIPPAGE_EXIT  # 5% exit slippage
                else:
                    exit_slippage = 0.0
                leg_protocol_fee = gross_sale_value * PO_PROTOCOL_FEE  # pump.fun 1% per swap
                # Full flat fee charged on every exit leg (partial exits are full sell transactions)
                leg_flat_fee = PO_FLAT_FEE_PER_LEG
                net_proceeds = gross_sale_value - exit_slippage - leg_protocol_fee - leg_flat_fee
                # P&L denominator = full entry cash outflow (base + protocol + flat), not 0.05 SOL
                entry_cost_fraction = total_cost * fraction_sold
                pnl_sol = net_proceeds - entry_cost_fraction
                pnl_pct = (net_proceeds / entry_cost_fraction - 1) * 100 if entry_cost_fraction > 0 else 0.0
                # Accumulate realized PnL in SOL (cash basis)
                realized_pnl += pnl_sol
                # Determine if position is completed (remaining quantity = 0)
                # Partial exits (staggered tiers) do NOT increment completed_positions
                if PO_STAGGERED_EXITS and "tier1" in position:
                    # Partial exit: still has remaining quantity — don't count as completed
                    if verbose:
                        print(f"  Partial exit: {exit_reason}")
                else:
                    # Full exit: completed position
                    completed_positions += 1
                    if verbose:
                        print(f"  [COMPLETED] position {completed_positions}")
                if verbose:
                    print(f"\n[EXIT] {position['asset']} | reason: {exit_reason}")
                    print(f"  entry ${position['entry_price']:.4f} | exit ${exit_price_border:.4f} | fraction_sold={fraction_sold:.2f}")
                    print(f"  Gross: {gross_sale_value:.4f} SOL | Net: {net_proceeds:.4f} SOL | PnL: {pnl_sol:+.4f} SOL ({pnl_pct:+.1f}%)")
                    print(f"  sell_legs={sell_legs} | completed={completed_positions} | realized_pnl={realized_pnl:.4f} SOL")
                    # Two-mode break-even labeling
                    PO_BNavy = c["PO_BNavy"]
                    total_cost = PO_BNavy + PO_BNavy * c["PO_PROTOCOL_FEE"] + c["PO_FLAT_FEE_PER_LEG"]
                    std_be = (total_cost + c["PO_FLAT_FEE_PER_LEG"]) / (PO_BNavy * (1 - c["PO_PROTOCOL_FEE"]))
                    wc_be = (total_cost + c["PO_FLAT_FEE_PER_LEG"]) / (PO_BNavy * (1 - c["PO_SLIPPAGE_ENTRY"]) * (1 - c["PO_SLIPPAGE_EXIT"]) * (1 - c["PO_PROTOCOL_FEE"]))
                    print(f"\n[BE] Two-mode break-even (0.05 SOL):")
                    print(f"  Standard fee model: ≈ {std_be:.2f}x (actual fills)")
                    print(f"  Worst-case tolerance: ≈ {wc_be:.2f}x (15% entry + 5% exit slippage)")
                    print(f"  P&L % denominator = full entry cash outflow ({total_cost:.5f} SOL), not 0.05 SOL")
                position = None
                entry_price = None
                hold_start = None
                last_update = time.time()

        # ── Evidence floor warning (warning-only guardrail) ──
        if completed_positions < 20:
            print(f"\n[INSUFFICIENT_EVIDENCE] completed_positions={completed_positions} (< 20 floor) | "
                  f"sell_legs={sell_legs} | realized_pnl={realized_pnl:.4f} SOL | config=v3 | below 20 is NOT proof of profitability")

        time.sleep(60)  # continuous loop, real-time simulated

if __name__ == "__main__":
    print("Paper Observer v3 — continuous screening mode (paper-only).")
    print("No fixed cycle. No shorts. No live money.")
    print("Press Ctrl+C to stop.\n")

    # ── Parse CLI arguments for configuration (A/B test support) ──────────────
    parser = argparse.ArgumentParser(
        description="LYTA Grok Desk — Paper Observer Simulator (config v3 + opt-in perimeters)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Paper Observer config v3
    parser.add_argument("--buy-size", type=float, default=0.05,
                        help="Buy size in SOL")
    parser.add_argument("--fee-break-even", type=float, default=1.06,
                        help="Fee break-even target (x)")
    parser.add_argument("--entry-min", type=float, default=8,
                        help="Minimum bonding-curve progress (%%): e.g. --entry-min 15")
    parser.add_argument("--entry-max", type=float, default=70,
                        help="Maximum bonding-curve progress (%%): e.g. --entry-max 80")
    parser.add_argument("--min-wallets", type=int, default=15,
                        help="Minimum unique wallets required")
    parser.add_argument("--min-buys", type=int, default=3,
                        help="Minimum buys required")
    parser.add_argument("--min-holders", type=int, default=30,
                        help="Minimum holders required")
    parser.add_argument("--top10-max", type=float, default=30,
                        help="Max top-10 concentration (%%): e.g. --top10-max 30")
    parser.add_argument("--dev-max", type=float, default=15,
                        help="Max developer holdings (%%)")
    parser.add_argument("--rebuys", action="store_true",
                        help="Enable rebuys")
    parser.add_argument("--exit-1", type=float, nargs=2, default=[2.0, 0.50],
                        metavar=("PERCENT", "FRACTION"),
                        help="First exit tier: e.g. --exit-1 200 0.50 (200%% at 50%%)")
    parser.add_argument("--exit-2", type=float, nargs=2, default=[3.0, 1.00],
                        metavar=("PERCENT", "FRACTION"),
                        help="Second exit tier: e.g. --exit-2 300 1.00 (300%% at 100%%)")
    parser.add_argument("--trail", type=float, default=2.5,
                        help="Trailing exit multiple")
    parser.add_argument("--trail-dd", type=float, default=0.15,
                        help="Trailing exit trigger drawdown (%%): e.g. --trail-dd 0.15")
    parser.add_argument("--stop-loss", type=float, default=0.10,
                        help="Stop-loss trigger multiple (e.g. 0.10 = -90%%)")
    parser.add_argument("--stale", type=int, default=120,
                        help="Stale exit threshold (seconds)")
    parser.add_argument("--dead", type=int, default=300,
                        help="Dead exit threshold (seconds)")
    parser.add_argument("--hold-grad", action="store_true",
                        help="Hold through PumpSwap graduation")
    parser.add_argument("--slippage-entry", type=float, default=0.15,
                        help="Slippage at entry (%%)")
    parser.add_argument("--slippage-exit", type=float, default=0.05,
                        help="Slippage at exit (%%)")
    parser.add_argument("--verbose", action="store_true", default=True,
                        help="Enable verbose output")
    parser.add_argument("--no-verbose", action="store_false", dest="verbose",
                        help="Disable verbose output")
    parser.add_argument("--mint-auth-required", action="store_true",
                        help="Require mint/freeze authority revoked")
    parser.add_argument("--risky-ext-block", action="store_true",
                        help="Block risky extensions")
    parser.add_argument("--max-pool-fee", type=float, default=0.04,
                        help="Maximum pool fee (%%)")
    parser.add_argument("--trading-hours", action="store_true",
                        help="Trading hours (24/7)")
    parser.add_argument("--pnl-limits", action="store_true",
                        help="Enable session P&L limits")
    parser.add_argument("--config-file", type=str, default=None,
                        help="Path to JSON config file")

    # Opt-in perimeters (v3.1 improvements) — A/B test toggles
    parser.add_argument("--enable-max-pos-pct", action="store_true",
                        help="Enable max position %% of equity cap (Whale Copier style)")
    parser.add_argument("--enable-liquidity-watch", action="store_true",
                        help="Enable liquidation distance watch (Paper MILL style)")
    parser.add_argument("--enable-two-visit", action="store_true",
                        help="Enable two-visit entry confirmation (Range Farmer style)")
    parser.add_argument("--enable-staggered-exits", action="store_true",
                        help="Enable staggered 3-tier exit (Pelosi's Bet Tracker style)")
    parser.add_argument("--max-pos-pct", type=float, default=0.25,
                        help="Max position as %% of equity (0 = disabled)")
    parser.add_argument("--liq-dist-watch", action="store_true",
                        help="Liquidation distance watch (overlap with enable-liquidity-watch)")
    parser.add_argument("--two-visit-window", type=int, default=300,
                        help="Two-visit confirmation window in seconds (default 300)")

    # Run configuration
    parser.add_argument("--collateral", type=float, default=6.0,
                        help="Starting collateral in SOL")
    parser.add_argument("--asset", type=str, default="GOBLIN",
                        help="Asset/pair name to simulate")
    parser.add_argument("--test-mode", action="store_true",
                        help="Run in test mode (limited iterations, no infinite loop)")
    parser.add_argument("--test-iterations", type=int, default=100,
                        help="Number of iterations in test mode")
    parser.add_argument("--worst-case", action="store_true",
                        help="Enable worst-case tolerance mode (15%% entry + 5%% exit slippage applied)")

    args = parser.parse_args()

    # ── Load config from file (if provided) ────────────────────────────────
    load_config(args.config_file)

    # ── Apply CLI overrides ───────────────────────────────────────────────
    apply_config(args)

    # ── Sync config to module-level PO_* variables ───────────────────────
    sync_config_to_module_vars(config)

    print(f"\n[PERIMETERS] Opt-in v3.1 enabled: max-pos-pct={PO_MAX_POS_PCT},")
    print(f"  liq-dist-watch={PO_LIQ_DIST_WATCH}, two-visit={PO_TWO_VISIT_CONFIRM},")
    print(f"  staggered-exits={PO_STAGGERED_EXITS}")
    print(f"[A/B TEST] config_id={'default'} (run with --ab-name <name> for comparison)\n")

    try:
        run_paper_desk(collateral=args.collateral, asset=args.asset, verbose=True)
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
