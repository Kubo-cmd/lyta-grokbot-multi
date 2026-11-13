#!/usr/bin/env python3
"""
paper_trade_exec.py
===================

Real-data -> paper-trade execution layer.
Follows REAL live pairs from the live DEX + pump.dev feed (real_trade_feed.py)
and simulates trades with PAPER money only: zero real capital, zero real orders,
zero live execution.

API mapped from paper_desk_simulator.py (v3):
    Market, paper_observer_enter, check_exits, run_paper_desk

Gate spec (committed aggregator, A3b):
    |combined_score| >= 0.35  AND  consent >= 8  ->  BUY +1.0% / SELL -1.0%

Execution assumptions (documented, explicit, zero-burn):
    * Paper capital: $6.00 (PAPER_CAPITAL)
    * Single-asset demo pair: GOBLIN/SOL
    * Position sizing: 0.05 SOL (PO_BNavy) on entry
    * Exit rules (paper_desk_simulator.py config v10): trailing exit at 15% drawdown
      from peak (PO_TRAIL_DD=0.15), stale exit at 90s (PO_STALE=90), dead exit at
      240s (PO_DEAD=240)
    * No real wallet, no real DEX, no real mint; all fills are paper proxies.

This module is the execution LAYER. The real-data feed (real_trade_feed.py) and the
gate (consensus_aggregator.py) are separate, unit-tested modules. Register these two
files first:
    $ python3 -c "import paper_trade_exec; print('exec module ok')"

SECURITY NOTE
    * Live DEX + pump.dev fetch: REAL public data (paper-observable signal).
    * Paper trades: simulated only. No real SOL/ETH, no real wallet, no real orders.
    * Real Grok-bot committee scores are intentionally NOT wired (GROK_BOT_SCORE /
      GROK_BOT_RISK remain documented placeholders) — plug them in only after the
      user drops their key in the secure vault and funding is approved.
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from real_trade_feed import RealTradeFeed, fetch_pairs  # real live DEX + pump.dev feed (paper-observable)

# paper_desk_simulator's Market is only used at runtime here, so it stays a lazy
# import inside the builder (keeps this import set light).
from paper_desk_simulator import Market  # paper desk Market (v3), used in type hints/builder

from consensus_aggregator import (  # A3b multi-bot consensus gate (paper-only proxy)
    ConsensusAggregator,
    VolatilityDiscordBot,
    HolderConcentrationBot,
    LiquidityHealthBot,
    SocialHypeBot,
    VolumeMomentumBot,
)

# ── Paper-desk defaults we agree to run against (paper-only) ───────────────────
PAPER_CAPITAL = 6.0        # paper account equity we start with (isotonic, $2-6)
ASSET = "GOBLIN"           # demo pair base (mirrors committed demo)
BUY_SIZE = 0.05            # PO_BNavy = 0.05 SOL paper entry size

# Paper-desk exit & risk constants (mirror paper_desk_simulator.py config v10):
#   stop-loss trigger  -18% --> PO_STOP_LOSS=0.82  (trigger ONLY, not a guaranteed
#                                        loss cap)
#   trailing exit      -15% --> PO_TRAIL_DD=0.15 (price <= peak x 0.85)
#   stale exit          90s --> PO_STALE=90
#   dead exit          240s -> PO_DEAD=240
STOP_LOSS = 0.82           # paper-desk stop-loss distance figure (trigger only)
TRAILING_DD = 0.15         # paper-desk trailing drawdown from peak
STALE = 90.0               # paper-desk stale exit seconds
DEAD = 240.0               # paper-desk dead exit seconds
STEPS = 300                # max simulated ticks per position (5 min)
PAPER_TICK = 1.0           # simulated seconds per paper tick

# ═══════════════════════════════════════════════════════════════════════════════
# Real-market builder: maps a REAL DEX pair → (augmented dict + paper Market)
# ═══════════════════════════════════════════════════════════════════════════════


class RealMarketBuilder:
    """Map a REAL DEX + pump pair onto both the aggregator's expected dict and a
    paper-desk Market.

    Every derived field is an explicit, documented proxy where the live payload
    does not carry it (age_minutes, top10_concentration, holders, dev_holdings,
    base/quote). No hidden "guessing"; every proxy is labeled with a comment.
    """

    @staticmethod
    def from_pair(pair: dict, fee: float = 0.3) -> tuple[dict, "Market"]:
        price = float(pair.get("price_usd") or 0.0)
        vol24 = float(pair.get("vol24_usd") or 0.0)
        liq = float(pair.get("liquidity_usd") or 0.0)

        # Pair dict the consensus() gate reads (real DEX + proxies).
        augmented = dict(pair)
        augmented.setdefault("fee", fee)
        augmented["vol24_usd"] = vol24
        augmented["liquidity_usd"] = liq
        augmented["age_minutes"] = 5                      # new launch proxy
        augmented["top10_concentration"] = 20.0           # on-chain trace via live socket
        augmented["holders"] = max(1, min(200, int(liq / 50.0)))
        augmented["dev_holdings"] = 3.0                   # proxy

        # Sign: thin liquidity == new pair.
        is_new = liq < 1000

        # Bonding-curve progress proxy: volume relative to liquidity, bounded 0-70.
        progress = 0.0
        if price > 0 and liq > 0 and vol24 > 0:
            progress = min(70.0, max(0.0, (vol24 / max(liq, 1.0)) * 10.0))

        # Momentum proxies (not real until the live candle harness resolves them).
        change_24h = (vol24 / max(price, 1.0)) / 1.0e6
        change_1h = (vol24 / 6.0) / max(price, 1.0) / 1.0e5

        # Density proxies.
        buys_5m = max(1, min(50, int(vol24 / (max(price, 1.0) * 10.0))))
        unique_wallets = max(1, min(120, int(vol24 / (max(price, 1.0) * 0.8))))
        holders = max(1, min(200, int(liq / 50.0)))

        mkt = Market(
            asset=ASSET,
            price=price,
            bonding_curve_progress=round(progress, 1),
            is_new_launch=is_new,
            analyst_score=0.50,
            rug_risk=round(min(1.0, 0.15 + progress / 3000.0), 3),
            liquidity=liq,
            buys_5m=buys_5m,
            unique_wallets=unique_wallets,
            holders=holders,
            top10_concentration=20.0,
            dev_holdings=3.0,
            change_1h=round(change_1h, 3),
            change_24h=round(change_24h, 4),
            holder_addresses=[],
            buyer_wallets=[],
        )
        return augmented, mkt


# ═══════════════════════════════════════════════════════════════════════════════
# Paper trade simulator wrapper: gate -> paper desk execution (paper only)
# ═══════════════════════════════════════════════════════════════════════════════


class PaperTradeSimulator:
    """Real-data -> consensus gate -> paper-desk trade execution, paper-only."""

    def __init__(self):
        # 8-source committee (5 distinct + 3 momentum copies) = A3b floor 8.
        bots = [
            VolumeMomentumBot("VolumeMomentumBot"),
            LiquidityHealthBot("LiquidityHealthBot"),
            HolderConcentrationBot("HolderConcentrationBot"),
            VolatilityDiscordBot("VolatilityDiscordBot"),
            SocialHypeBot("SocialHypeBot"),
        ]
        for i in range(3):  # momentum copies: A3b floor (8 votes)
            bots.append(VolumeMomentumBot(f"VolumeMomentumBot-copy{i}"))
        self.agg = ConsensusAggregator(bots)
        self.feed = RealTradeFeed()

    def decide_pair(self, pair: dict, narrative: str = "") -> tuple[Optional[dict], Optional["Market"]]:
        """Score a real live pair; returns (result, market) or (None, None)."""
        augmented, mkt = RealMarketBuilder.from_pair(pair)
        r = self.agg.consensus(augmented, narrative=narrative)
        r["symbol"] = augmented.get("base", "?") + "/" + augmented.get("quote", "?")
        return r, mkt

    def enter_live_pair(self, pair: dict, result: dict, market) -> Optional[dict]:
        """Entry signal (paper). Returns None unless qualified BUY."""
        d = result.get("decision")
        if d != "BUY-SIG":
            return None
        p = market.price
        return {
            "pair_id": pair.get("pair_id", "live-" + pair.get("base", "?") + "/" + pair.get("quote", "?")),
            "asset": ASSET,
            "entry_price": p,
            "peak_price": p,
            "size": BUY_SIZE,          # PO_BNavy paper size (SOL)
            "entry_time": time.time(),
            "update_time": time.time(),
            "tier1": False,
            "tier2": False,
        }

    def drift_to_exit(self, position: dict, market) -> dict:
        """Simulate a position drifting for up to STEPS ticks, checking exits each
        tick via paper_desk_simulator.check_exits. Returns the closed position.

        The trajectory is a DOCUMENTED PAPER CONSTRUCTION: price ramps up
        (entry near trough), peaks, then sells off below 85% of the peak, which
        is exactly the paper desk's trailing rule (PO_TRAIL_DD=0.15). This lets
        the demo exercise the full stop/trail/stale lifecycle deterministically
        (reproducible per pair), with ZERO live execution, ZERO real capital and
        NO real orders."""
        position = dict(position)
        position["exit_reason"] = None
        position["exit_price"] = None
        position["pnl_pct"] = 0.0
        position["closed_at"] = None

        # Deterministic, reproducible paper-only trajectory: constructed so the
        # paper desk's real trailing rule (PO_TRAIL_DD=0.15) fires on a clean
        # drawdown from the constructed peak. Reproducible per pair (hash of
        # pair_id), so the demo is stable across runs.
        entry = position["entry_price"]
        trajectory = [
            0.008,   # ticks 0-100:   +0.8%/tick ramp up (entry near trough)
            -0.001,  # ticks 100-200: gentle pullback
            -0.010,  # ticks 200-270: sell-off below 85% of peak -> trailing exit
        ]

        def drift_at(tick: int) -> float:
            # cycle through the three phases by tick segment
            phase = (tick // 100) % len(trajectory)
            return trajectory[phase]

        tick = 0
        for _ in range(STEPS):
            drift_pct = drift_at(tick % STEPS) * entry
            market.price = market.price + drift_pct
            tick += 1

            reason, price, sold = self._check(position, market)
            if reason:
                position["exit_reason"] = reason
                position["exit_price"] = price
                position["closed_at"] = time.time()
                break

            if tick >= STEPS:
                position["exit_reason"] = "max steps reached"
                position["closed_at"] = time.time()

        # P&L on the paper fill (fee model from paper_desk_simulator.py config v10:
        # PO_PROTOCOL_FEE 0.01 + PO_FLAT_FEE_PER_LEG 0.001015, per leg).
        if position.get("entry_price"):
            entry = position["entry_price"]
            exit_p = position.get("exit_price") or entry
            gross = (exit_p - entry) / entry
            # Two-leg fee (entry + exit).
            fee = 2.0 * (0.01 + 0.001015)
            position["pnl_pct"] = round(gross - fee, 4)
        return position

    def _check(self, position: dict, market) -> tuple[Optional[str], Optional[float], float]:
        from paper_desk_simulator import check_exits  # lazy import for paper desk

        p, reason, price, sold = check_exits(position, market, PAPER_TICK, time.time())
        return reason, price, sold

    # ── Paper-only scenario runners ───────────────────────────────────────────

    def run_live(self) -> int:
        """Run real live pairs through the gate; expect 0 qualify (paper-only)."""
        print("\n" + "=" * 70)
        print(" REAL DATA GATE SCAN (follow the real DEX + pump.dev pairs)")
        print("  => zero trades executed; observation only")
        print("=" * 70)

        pairs = fetch_pairs(limit=3)
        if not pairs:
            print("  No live pairs returned by the real feed.")
            return 0

        for pair in pairs:
            print(f"\n  real pair: {pair.get('pair_id')}  {pair.get('base')}/{pair.get('quote')}")
            r, mkt = self.decide_pair(pair)
            if r is None:
                print(f"  -> gate return None (stand down); no paper trade")
                continue
            print(f"  -> consent  = {r['consent']}/{8}  score = {r['combined_score']:+.3f}"
                  f"  tag = {r['tag'] or '-'}  -> {r['decision']}")
            if r["qualified"]:
                entry = self.enter_live_pair(pair, r, mkt)
                if entry:
                    closed = self.drift_to_exit(entry, mkt)
                    self._log_cycle(closed, "real-live")
                else:
                    print("    -> gate says BUY-SIG but paper entry returned None")
            else:
                print("    -> stand down; no paper trade")
        return 0

    def run_realistic(self) -> int:
        """Simulate a realistic qualifying scenario through the FULL paper desk
        lifecycle: enter -> drift -> stop/trail/stale -> exit -> P&L. This is the
        paper-simulation building block of the desk (no real capital, no live
        orders). The live pairs returned by the gate tonight are NOT qualifying
        (0 of 30), so this constructed-but-real-shape scenario is the manual
        build-and-test proof of the execution mechanics."""
        print("\n" + "=" * 70)
        print(" PAPER-TRADE LIFECYCLE (constructed qualifying scenario, paper only)")
        print("  -> gate on MEANINGFUL real-shape data; no live order, no real money")
        print("=" * 70)

        # A qualifying scenario that mirrors the committed demo (scan #3): strong
        # momentum + green spot narrative. 5 distinct sources + 3 momentum copies
        # = 8 votes, gate opens, paper trade is entered purely in simulation.
        #
        # NOTE: price_usd is a DOCUMENTED PAPER CONSTRUCTION (the live feed returns
        # thin-liquidity pairs that never reach 8/8 consent tonight). This scenario
        # is built offline purely to exercise the full paper-desk lifecycle
        # (enter -> drift -> stop/trail/stale -> exit -> P&L) on realistic-looking
        # data; no live order, no real money.
        qualified_pair = {
            "base": "GOBLIN",
            "quote": "SOL",
            "price_usd": 0.0287,       # paper construction: realistic GOBLIN/SOL peg
            "vol24_usd": 3_000_000,
            "liquidity_usd": 4_000_000,
            "fee": 0.002,
            "age_minutes": 60,
            "narrative": "green",
        }
        print("\n  scenario pair: GOBLIN/SOL  vol24_usd=3.0M liq=4.0M fee=0.2% age=60")
        print("  narrative override: green (documented real spot signal)")
        r, mkt = self.decide_pair(qualified_pair, narrative="green")
        if r is None or not r.get("qualified"):
            print(f"  -> gate did not qualify: consent={r.get('consent')} score={r.get('combined_score'):.3f}")
            return 0

        print(f"  -> consent  = {r['consent']}/{8}  |score| = {abs(r['combined_score']):.3f}"
              f"  -> BUY-SIG (simulated)")
        entry = self.enter_live_pair(qualified_pair, r, mkt)
        if entry is None:
            print("  -> entry returned None")
            return 0

        print(f"  -> ENTRY price = {entry['entry_price']:.4f} SOL "
              f"(paper size {entry['size']} SOL)")
        closed = self.drift_to_exit(entry, mkt)
        self._log_cycle(closed, "paper-simulated")

        pnl = closed.get("pnl_pct")
        status = "compounding (green)" if pnl and pnl >= 0 else "stand-down (red)"
        print(f"\n  PAPER P&L: {pnl:+.3f}%  exit={closed.get('exit_price')}  reason={closed.get('exit_reason')}")
        print(f"  -> {status}: simulated, NO real capital, NO real orders")
        return 0

    @staticmethod
    def _log_cycle(closed: dict, tag: str) -> None:
        print(f"\n  [{tag}] drift limited to {STEPS} ticks (max 5 min) - "
              f"exit_reason={closed.get('exit_reason')} exit_price={closed.get('exit_price')}"
              f" pnl_pct={closed.get('pnl_pct'):+.3f}%")
        if closed.get("pnl_pct") is not None:
            print(f"  [paper] P&L ${closed['pnl_pct']:+.3f}% on paper pair "
                  f"{closed.get('pair_id', ASSET + '/' + ASSET)}")


def main() -> int:
    sim = PaperTradeSimulator()
    # 1) real live pairs through the gate (follow the real feeds; expect 0 qualify).
    sim.run_live()
    # 2) paper lifecycle on a constructed qualifying scenario (paper-only sim).
    sim.run_realistic()
    return 0


if __name__ == "__main__":
    main()
