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

# PHASE 2 ACTIVE — PUMP.FUN MEMECOIN (PAPER ONLY)
# pumpfun trigger: ACTIVATED. Paper-only trading, no live trades,
# no wallet import, no signing.
# Trading costs: 0.02% fees, 0.05% slippage, fixed gas per trade
# 12 bots: SCOUT, FILTER, ANALYST, DEV_WATCH, CONVICTION, MOMENTUM,
#          SCALPER, CONTRARIAN, TREND, RESEARCHER, PORTFOLIO, EXECUTOR
# Paper pool: $100 (enforced in _paper_agent.ts)
# Session: 60 minutes (Phase 1 completed with $35.10 final capital)

"""
from __future__ import annotations

import argparse
import json
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

# TradingDesk initialization — single live instance below (config v3)
# (A v3-enhanced copy at line 49 was dead code — removed in this cleanup pass.)

# TelegramAlert (Phase 2) - pushes alerts to Telegram if token configured
_telegram_path = os.path.join(REPO_ROOT, "pumpfun_desk_simulator.py")
_telegram_spec = importlib.util.spec_from_file_location("pumpfun_desk_simulator", _telegram_path)
_telegram_mod = importlib.util.module_from_spec(_telegram_spec)
sys.modules["pumpfun_desk_simulator"] = _telegram_mod
_telegram_spec.loader.exec_module(_telegram_mod)
TelegramAlert = _telegram_mod.TelegramAlert

# Create the global trading desk (same as pumpfun_desk_simulator.py)
TRADE_DESK = TradingDesk(capital=100.0, asset="GOBLIN", config="v3")

# Global flag: is Telegram configured?
TELEGRAM_CONFIGURED = TelegramAlert._TG_CONFIGURED()

# ── 12-bot roster (mirrors pumpfun_desk_simulator.py) ─────────────
BOT_NAMES = [
    "SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
    "PORTFOLIO", "EXECUTOR"
]

# 6+ bot consensus required before any paper capital move
CONSENSUS_MIN = 8
# Per-tick direction bias — A3b paper-desk knobs (values live below in run_session)
SIGNAL_GATE = 0.35      # |signal| >= 0.35 → qualifies for a trade
BASE_CHANGE_BUY = 0.010 # +1.0% on BUY
BASE_CHANGE_SELL = -0.010 # −1.0% on SELL
# Per-consensus-tick % P&L — feeds win_rate / expectancy on the desk
_tick_pnls: list[float] = []
# Per-trade log: tick-level P&L, votes, gate reasons (tuning data)
_trade_log: list[dict] = []

# ── Signal processor ───────────────────────────────────────────────
def compute_signal(market: dict) -> dict:
    """Compute a composite signal from raw market data."""
    score = market.get("score", 50)
    rug_risk = market.get("rug_risk", 0.5)
    liquidity = market.get("liquidity", 0.5)
    volume = market.get("volume", 0.5)
    change24h = market.get("change24h", 0)
    price = market.get("price", 0.5)

    # --- Trend factor (wind direction) ---
    # Positive for UP trends, negative for DOWN trends
    # Trend staleness: decay trend weight over time (1 tick = 5% decay)
    # Returns get stale in pump.fun; require fresh direction confirmation
    trend_factor = 0.0
    if market.get("trend") == "up":
        trend_factor = 0.75
    elif market.get("trend") == "down":
        trend_factor = -0.75

    # Trend staleness: decay after the *current* regime has lasted 20 ticks
    # 5% extra decay per tick past 20, capped at 65% penalty
    trend_age = int(market.get("trend_age", 0) or 0)
    if trend_age > 20:
        decay = min(0.65, (trend_age - 20) * 0.05)
        trend_factor = trend_factor * (1.0 - decay)

    # Normalize score (0-100 -> -1 to +1)
    score_norm = (score / 100) * 2 - 1

    # Rug risk inverted (lower = better)
    rug_norm = 1 - rug_risk

    # Liquidity (higher = better)
    liq_norm = liquidity

    # Volume (higher = more activity)
    vol_norm = volume

    # Momentum (price momentum, -1 to +1 roughly)
    mom_norm = change24h / 25.0

    # --- Change24h amplification (non-linear) ---
    # High momentum tokens (> threshold) get non-linear boost
    # Threshold: 12.5% 24h change (mom_norm > 0.5)
    # Amplification strength: proportional to deviation from threshold
    change_amp = 0.0
    if abs(mom_norm) > 0.5:
        # Excess momentum beyond threshold
        excess = abs(mom_norm) - 0.5
        # Cap amplification at ±0.15
        change_amp = (excess * 0.3) * (1.0 if mom_norm > 0 else -1.0)
        change_amp = max(-0.15, min(0.15, change_amp))

    # Composite signal: weighted sum.
    # Trend factor reduced to 30% (was 45%) to reduce dominance
    # Rug and liquidity increased to 20% each to weight survival factors higher
    # Change amplification adds non-linear boost for high-momentum tokens
    signal = (
        trend_factor * 0.30 +           # 30% (was ~45%)
        score_norm * 0.15 +             # 15%
        rug_norm * 0.20 +               # 20% (was 15%)
        liq_norm * 0.20 +               # 20% (was 15%)
        vol_norm * 0.05 +               # 5% (was 10%)
        mom_norm * 0.10 +               # 10% (was 15%)
        change_amp                      # non-linear amplification
    )

    return {
        "score": score,
        "rug_risk": rug_risk,
        "liquidity": liquidity,
        "volume": volume,
        "change24h": change24h,
        "signal": signal,
        "score_norm": score_norm,
        "rug_norm": rug_norm,
        "liq_norm": liq_norm,
        "vol_norm": vol_norm,
        "mom_norm": mom_norm,
        "trend": market.get("trend", "sideways"),
    }

# ── Bot logic (uses compute_signal) ────────────────────────────────
def run_bot(bot_name: str, signal: dict) -> str:
    """Run a single bot and return its decision based on the signal."""
    s = signal
    score = s["score"]
    rug_risk = s["rug_risk"]
    liquidity = s["liquidity"]
    volume = s["volume"]
    change24h = s["change24h"]

    if bot_name == "SCOUT":
        # Early signal detector
        if change24h > 2 and volume > 0.5:
            return "buy"
        if change24h < -1:
            return "sell"
        return "pass"

    elif bot_name == "FILTER":
        # Quality filter
        # In DOWN markets, require higher quality for buys
        if liquidity > 0.6 and rug_risk < 0.4:
            s_trend = s.get("trend", "sideways")
            if s_trend == "down":
                return "buy" if change24h > 0 else "sell"
            return "buy"
        if rug_risk > 0.7:
            return "sell"
        return "pass"

    elif bot_name == "ANALYST":
        # Fundamental analysis
        # In DOWN markets, be more conservative
        if rug_risk < 0.3 and liquidity > 0.5:
            s_trend = s.get("trend", "sideways")
            if s_trend == "down":
                return "buy" if change24h > 0 else "sell"
            return "buy"
        if rug_risk > 0.6:
            return "sell"
        return "pass"

    elif bot_name == "DEV_WATCH":
        # Late momentum chaser
        if change24h > 10:
            return "buy"
        if change24h < -15:
            return "sell"
        # In DOWN markets, don't chase falling knives
        if s.get("trend") == "down" and change24h < -5:
            return "sell"
        return "pass"

    elif bot_name == "CONVICTION":
        # Conviction threshold - higher bar for conviction
        if score >= 75:
            return "buy"
        if score <= 25:
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
        if 1 <= abs(change24h) <= 10:
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
        # Research-focused
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

# ── Realistic market simulation ─────────────────────────────────────
# Simulates realistic market dynamics: trend regimes, volatility clustering,
# volume spikes, and mean reversion.  All simulated — no real trades.

# Market state (persisted across ticks to create realistic continuity)
_market_state = {
    "trend": random.choice(["up", "down", "sideways"]),
    "trend_strength": random.uniform(0.0, 0.05),
    "volatility": random.uniform(0.02, 0.08),
    "volume_mult": max(0.2, min(3.0, random.gauss(1.0, 0.3))),
    "price": random.uniform(0.1, 0.9),
    "last_change": 0.0,
    "_ticks": [],  # tick history for dashboard + staleness
    "trend_age": 0,
}

def generate_market() -> dict:
    """Generate a realistic market state for a pump.fun token.

    Uses a simple mean-reverting random walk with:
    - Trend regimes (up/down/sideways) that persist for several ticks
    - Volatility clustering (periods of high/low volatility)
    - Volume spikes (news events, whale moves)
    - Serial correlation (returns persist for a few ticks)
    """
    global _market_state

    # --- Trend regime logic ---
    if _market_state["trend"] == "up":
        _market_state["trend_strength"] += random.uniform(0.001, 0.003)
        _market_state["trend_strength"] = min(_market_state["trend_strength"], 0.12)
    elif _market_state["trend"] == "down":
        _market_state["trend_strength"] -= random.uniform(0.001, 0.003)
        _market_state["trend_strength"] = max(_market_state["trend_strength"], -0.12)

    # --- Volatility clustering ---
    if _market_state["volatility"] > 0.10:
        _market_state["volatility"] *= 0.95  # mean-revert volatility
    elif _market_state["volatility"] < 0.015:
        _market_state["volatility"] *= 1.05

    # --- Random regime switches (reset trend_age on a real change) ---
    if random.random() < 0.08:
        new_trend = random.choice(["up", "down", "sideways"])
        if new_trend != _market_state["trend"]:
            _market_state["trend"] = new_trend
            _market_state["trend_age"] = 0
        else:
            _market_state["trend_age"] += 1
    else:
        _market_state["trend_age"] += 1

    # --- Generate returns ---
    noise = random.gauss(0, _market_state["volatility"])
    # Add trend component
    if _market_state["trend"] == "up":
        trend_component = _market_state["trend_strength"] * 2.0
    elif _market_state["trend"] == "down":
        trend_component = -_market_state["trend_strength"] * 2.0
    else:
        trend_component = 0.0
    # Add serial correlation (returns persist)
    if _market_state["last_change"] != 0:
        noise += _market_state["last_change"] * 0.3

    # --- Apply returns to price ---
    price_change = noise * 0.5
    _market_state["price"] *= (1 + price_change)
    _market_state["last_change"] = price_change

    # --- Volume spikes ---
    if random.random() < 0.05:  # 5% chance of volume spike
        _market_state["volume_mult"] *= random.uniform(2.0, 5.0)
    elif _market_state["volume_mult"] > 0.3:
        _market_state["volume_mult"] *= 0.98

    # --- Clip price to reasonable range ---
    _market_state["price"] = max(0.01, min(1.5, _market_state["price"]))

    # --- Score (rumor mill score) ---
    # Range 50-90 (shifted upward), more realistic for pump.fun tokens
    score = random.randint(50, 90)

    # --- Rug risk ---
    rug_risk = random.weibullvariate(1.0, 1.2) / 2.5
    rug_risk = max(0.02, min(0.85, rug_risk))

    # --- Liquidity ---
    liquidity = max(0.05, min(1.0, random.gauss(0.6, 0.2) + noise * 0.5))

    # --- Volume ---
    volume = max(0.05, min(1.5, _market_state["volume_mult"] * (0.3 + random.gauss(0, 0.15))))

    # --- 24h change (blended: trend + noise) ---
    # Amplify trend contribution to match signal strength
    base_trend = (_market_state["trend"] == "up" and 8.0 or
                  _market_state["trend"] == "down" and -8.0 or 0.0)
    # Add trend_strength to change24h for stronger market signal
    change24h = base_trend + noise * 2.0 + (0.5 - random.random()) * 8.0 +                 _market_state["trend_strength"] * 15.0
    change24h = max(-30, min(45, change24h))

    return {
        "symbol": f"GOBLIN#{random.randint(0,99):02d}",
        "score": score,
        "rug_risk": rug_risk,
        "liquidity": liquidity,
        "volume": volume,
        "change24h": change24h,
        "price": _market_state["price"],
        "volatility": _market_state["volatility"],
        "trend": _market_state["trend"],
        "trend_strength": _market_state["trend_strength"],
        "trend_age": _market_state["trend_age"],
    }

# ── Realistic trading costs (paper trading) ─────────────────────────
# Realistic trading costs: fees, slippage, and gas.
# These are paper-simulation costs, NOT real money charges.
# Typical crypto fees: 0.01-0.1% per trade (paper simulation)
TRADING_FEES = 0.0002   # 0.02% per trade (maker-taker blended, paper sim)
SLIPPAGE = 0.0005       # 0.05% typical slippage (paper sim)
GAS_COST = 0.001        # Fixed gas cost per trade (paper sim)

def apply_trading_costs(capital: float, trades: int) -> float:
    """Apply realistic trading costs to capital."""
    if trades == 0:
        return capital
    # Fee: 0.25% per trade
    fees = capital * TRADING_FEES * trades
    # Slippage: 0.5% per trade (on average)
    slippage = capital * SLIPPAGE * trades
    # Fixed gas cost
    total_cost = fees + slippage + (GAS_COST * trades)
    return capital - total_cost

# ── Main paper trading loop ───────────────────────────────────────
def run_session(minutes: float = 30.0, interval: float = 10.0, verbose: bool = True):
    """Run the paper trading session through the SHARED engine.

    OpenBot and Grok-Bot both run the SAME shared PaperDesk:
      * A3b consensus gate (consent >= 8 AND |combined| >= 0.35)
      * paper-only capital guard (no real capital)
      * same verbose per-tick stand-down logging (per-bot votes + reasons)
    Only the advisory column differs per desk (OpenBot heuristics here;
    Grok committee plug in grokbot_multi.py).  No real trades, no real capital.
    """
    start = time.time()
    end = start + minutes * 60
    tick = 0
    last_html = 0
    html_interval = 30  # seconds between HTML updates

    # ── SHARED PAPER-ONLY RUN ENGINE (same setup for OpenBot + Grok-Bot) ───
    import importlib.util as _ilu
    _core_path = os.path.join(REPO_ROOT, "lyta-grok-desk", "paper_run_core.py")
    _core_spec = _ilu.spec_from_file_location("lyta_grok_desk_paper_core", _core_path)
    _core_mod = _ilu.module_from_spec(_core_spec)
    sys.modules["lyta_grok_desk_paper_core"] = _core_mod
    _core_spec.loader.exec_module(_core_mod)
    from lyta_grok_desk_paper_core import PaperDesk, Signal
    desk = PaperDesk(name="OpenBot", capital=100.0)
    # ── END SHARED ENGINE ───────────────────────────────────────────────────

    print("=" * 72)
    print("  LYTA GROK DESK — PAPER TRADING RUNNER  (SHARED ENGINE)")
    print("  A3b consensus gate + paper-only capital guard + verbose stand-down logging")
    print("=" * 72)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Duration: {minutes} minutes")
    print(f"  Paper capital: $100.00  (paper-only, no real trades)")
    print(f"  Asset: GOBLIN")
    print(f"  Session interval: {interval} seconds")
    print("-" * 72)

    try:
        while time.time() < end:
            tick += 1
            market = generate_market()
            market['_ticks'] = _market_state['_ticks']
            market['tick'] = tick

            # OpenBot spot/narrative heuristics -> composite signal
            signal = compute_signal(market)

            # Run all OpenBot bots on the signal
            votes = {bot: run_bot(bot, signal) for bot in BOT_NAMES}

            def _to_signals(votes_dict):
                _kind = {"buy": "buy", "sell": "sell", "pass": "pass"}
                out = {}
                for name, v in votes_dict.items():
                    kind = _kind.get(str(v), "pass")
                    out[name] = Signal(
                        name=name, kind=kind,
                        score=1.0 if kind == "buy" else -1.0 if kind == "sell" else 0.0)
                return out

            # OpenBot heuristics = composite spot/narrative signal alone (no committee).
            def _advice(pair, votes=None):
                val = float(signal["signal"])
                return val if abs(val) >= 0.05 else 0.0

            def _execute(pair, direction, gate):
                # Engine gate dict (apply_a3b_gate) carries 'qualified' / 'base_change',
                # not 'gate_passed'.
                if not gate.get("qualified"):
                    return {"executed": False,
                            "reason": gate.get("stand_down_reason") or "entry not qualified"}
                size = cap * 0.10
                trend_mult = {
                    "up": 1.0 + abs(market.get("trend_strength", 0.0)) * 0.3,
                    "down": 1.0 - abs(market.get("trend_strength", 0.0)) * 0.3,
                }.get(market.get("trend"), 1.0)
                new_cap = cap * (1.0 + gate["base_change"] * trend_mult)
                new_cap = apply_trading_costs(new_cap, 1)
                desk.equity = new_cap
                side = "LONG" if gate["base_change"] > 0 else "SHORT"
                pnl_frac = (new_cap - cap) / cap if cap else 0.0
                desk.trades.append({
                    "symbol": pair["symbol"], "tick": tick, "side": side,
                    "size": round(size, 4), "pnl_pct": round(pnl_frac * 100.0, 2),
                })
                return {
                    "executed": True, "symbol": pair["symbol"],
                    "side": side, "size": round(size, 4),
                    "base_change": gate["base_change"],
                    "pnl_pct": round(pnl_frac * 100.0, 2),
                }

            result = None
            try:
                result = desk.run_tick(
                    market, narrative=str(signal["signal"]),
                    vote_fn=_to_signals, advice_fn=_advice, execute_fn=_execute,
                )
            except Exception as exc:
                print(f"  [WARN] tick {tick} engine error: {exc}")
                result = None

            # Mirror shared-engine state into the Dashboard for the web view.
            TRADE_DESK.update_capital(max(0.01, desk.equity))
            TRADE_DESK.update_state({
                "capital": desk.equity,
                "ticks": tick,
                "tick_history": list(_market_state["_ticks"][-10:]),
                "positions": len([p for p in TRADE_DESK.state.positions if p.pnl is None]),
                "total_votes": len(votes),
                "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S-08:00"),
                "last_update": datetime.now().strftime("%H:%M:%S"),
                "session_running": True,
                "session_status": "PAPER-ONLY",
                "alerts": TRADE_DESK.state.alerts[-5:] if (hasattr(TRADE_DESK.state, "alerts") and TRADE_DESK.state.alerts) else [],
                "votes": {b: str(v) for b, v in votes.items()},
                "bots": [{"bot": b, "side": str(v), "score": market["score"],
                          "liquidity": market["liquidity"], "rug_risk": market["rug_risk"],
                          "change24h": market["change24h"]} for b, v in votes.items()],
            })

            # Keep the staleness tracker healthy across ticks.
            _market_state["_ticks"].append({
                "tick": tick, "symbol": market["symbol"], "trend": market["trend"],
                "change24h": market["change24h"], "score": market["score"],
            })
            if len(_market_state["_ticks"]) > 200:
                _market_state["_ticks"] = _market_state["_ticks"][-200:]

            # Per-tick log (pure paper simulation)
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tick {tick} {market['symbol']}")
            print(f"  Market: {market['trend'].upper()} trend | {market['change24h']:+.1f}% 24h | "
                  f"rug {market['rug_risk']:.2f} | liq {market['liquidity']:.2f} | score {market['score']:.0f}")
            print(f"  Signal: {signal['signal']:+.2f} ({'BUY' if signal['signal'] > 0.05 else 'SELL' if signal['signal'] < -0.05 else 'HOLD'})")
            print(f"  Bot votes: {votes}")
            if result is not None:
                if result.get("executed"):
                    t = result.get("trade") or {}
                    print(f"  Engine: {t.get('side')} {t.get('size')} pnl {t.get('pnl_pct')}% | "
                          f"consent {result['consent']}/8 | score {result['combined_score']:+.3f}")
                else:
                    print(f"  Engine stand-down: {result.get('stand_down_reason')}")
            print(f"  Capital: ${desk.equity:.2f} | Stand-downs: {desk.stand_downs} | "
                  f"Advisory: {result.get('advice') if result else None}")

            if TELEGRAM_CONFIGURED:
                TelegramAlert.alert(f"Tick {tick} | {market['symbol']} | capital ${desk.equity:.2f}", "info")

            # Generate HTML dashboard periodically
            if time.time() - last_html > html_interval:
                with open("trading_desk.html", "w") as f:
                    f.write(TRADE_DESK.to_html())
                last_html = time.time()

            # Sleep until next tick
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nSession stopped by user.")
        print(f"Total ticks processed: {tick}")

    # Final summary (shared engine only)
    print("\n" + "=" * 72)
    print("  SESSION COMPLETE")
    print("=" * 72)
    print(f"  Ticks processed: {tick}")
    print(f"  Final paper capital: ${desk.equity:.2f}")
    print(f"  Trades executed: {len(desk.trades)}")
    print(f"  Stand-downs: {desk.stand_downs}")
    print(f"  Advisory samples: {desk.grok_committee_advice[-5:]}")
    print(f"  Last signal: {desk.signals[-1] if desk.signals else 'n/a'}")
    print(f"  Final HTML: trading_desk.html")
    print("=" * 72)

    # Save final HTML (dashboard still rendered from the live TRADE_DESK)
    with open("trading_desk.html", "w") as f:
        f.write(TRADE_DESK.to_html())

    # Machine-readable paper record for the OpenBot desk
    record = {
        "desk": desk.name, "paper_only": True,
        "start": datetime.now().strftime("%Y-%m-%dT%H:%M:%S-08:00"),
        "duration_min": minutes, "tick_interval_s": interval,
        "ticks_processed": tick, "final_paper_capital": round(desk.equity, 2),
        "trades_executed": len(desk.trades), "stand_downs": desk.stand_downs,
        "advisory_samples": [a for a in desk.grok_committee_advice][-5:],
        "last_signal": desk.signals[-1] if desk.signals else None,
        "trades": list(desk.trades),
    }
    with open(os.path.join(REPO_ROOT, "paper_desk_openbot_record.json"), "w") as _f:
        json.dump(record, _f, indent=2)
    print(f"  Paper record written: paper_desk_openbot_record.json")




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
            # Write state JSON for web dashboard
            import json
            # Get per-bot vote counts from agent_votes
            def bot_side(bot):
                av = TRADE_DESK.state.agent_votes.get(bot, {})
                for side in ['buy', 'sell', 'hold', 'stand_down', 'pass']:
                    if av.get(side, 0) > 0:
                        return side
                return 'pass'
            TRADE_DESK.update_state({
                "capital": TRADE_DESK.state.capital,
                "asset": TRADE_DESK.state.asset,
                "ticks": 1,
                "positions": len([p for p in TRADE_DESK.state.positions if p]),
                "total_votes": sum(1 for b in BOT_NAMES if TRADE_DESK.state.agent_votes.get(b)),
                "last_update": datetime.now().strftime("%H:%M:%S"),
                "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S-08:00"),
                "session_running": False,
                "alerts": TRADE_DESK.state.alerts[-5:] if hasattr(TRADE_DESK.state, 'alerts') else [],
                "votes": {b: {"side": bot_side(b), "score": 0, "liquidity": 0, "rug_risk": 0, "change24h": 0} for b in BOT_NAMES},
                "bots": [{"bot": b, "side": bot_side(b), "score": 0, "liquidity": 0, "rug_risk": 0, "change24h": 0} for b in BOT_NAMES],
                "error": None
            })
            print("\nHTML written to trading_desk.html")
            print("State written to trading_desk_state.json")
    else:
        run_session(minutes=args.minutes, interval=args.interval)
