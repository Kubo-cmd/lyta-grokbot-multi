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
    """Run the paper trading session."""
    start = time.time()
    end = start + minutes * 60
    tick = 0
    last_html = 0
    html_interval = 30  # seconds between HTML updates

    print("=" * 72)
    print("  LYTA GROK DESK — PAPER TRADING RUNNER  (ENHANCED)")
    print("  Realistic market sim + trading costs + detailed logging")
    print("=" * 72)
    print(f"  Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Duration: {minutes} minutes")
    print(f"  Paper capital: $100.00  (paper-only, no real trades)")
    print(f"  Asset: GOBLIN")
    print(f"  Session interval: {interval} seconds")
    print(f"  Trading fees: {TRADING_FEES*100:.2f}%  Slippage: {SLIPPAGE*100:.2f}%")
    print("-" * 72)

    # Telegram alert if configured
    if TELEGRAM_CONFIGURED:
        TelegramAlert.alert(f"🚀 Paper session started | {minutes} min @ {interval}s interval | Capital $100.00", "success")

    try:
        while time.time() < end:
            tick += 1
            trades = {}  # Dict of bot_name -> vote_result for this tick
            now = time.time()
            market = generate_market()

            # Add tick history to market dict for trend staleness tracking
            market['_ticks'] = _market_state['_ticks']
            market['tick'] = tick
            
            # Compute composite signal
            signal = compute_signal(market)

            # Run all bots on the signal
            votes = {}
            for bot in BOT_NAMES:
                votes[bot] = run_bot(bot, signal)

            # Store votes for state tracking
            trades = votes

            # Determine overall signal strength
            signal_strength = sum(1 for v in votes.values() if v == "buy") - \
                             sum(1 for v in votes.values() if v == "sell")

            # Update trading desk with this tick
            TRADE_DESK.set_alert(f"🎯 Tick {tick}: {market['symbol']} — score {market['score']:.0f} | signal {signal['signal']:+.2f} | {market['trend'].upper()}")

            # Add votes
            for bot, side in votes.items():
                TRADE_DESK.add_vote(bot, side)

            # Direction-based capital change, gated on 5+ bot consensus
            buy_votes = sum(1 for v in votes.values() if v == "buy")
            sell_votes = sum(1 for v in votes.values() if v == "sell")
            pass_count = sum(1 for v in votes.values() if v == "pass")
            gate_reasons: list[str] = []
            acted = False
            base_change = 0.0
            # Gate 1: minimum signal strength — skip noise (no action below |0.35|)
            signal_gate = abs(signal["signal"]) >= SIGNAL_GATE
            # Gate 2: consensus — only the strongest direction moves capital
            consensus_buy = buy_votes >= CONSENSUS_MIN and buy_votes > sell_votes
            consensus_sell = sell_votes >= CONSENSUS_MIN and sell_votes > buy_votes
            # Gate 3: trend alignment — act with the market, never against it
            trade_with_trend = (market["trend"] == "up" and consensus_buy) or \
                               (market["trend"] == "down" and consensus_sell)
            if trade_with_trend and signal_gate:
                if consensus_buy:
                    base_change = BASE_CHANGE_BUY
                else:
                    base_change = BASE_CHANGE_SELL
                acted = True
            else:
                if not signal_gate:
                    gate_reasons.append(f"signal_gate (signal {signal['signal']:+.2f} < SIGNAL_GATE)")
                elif not consensus_buy and not consensus_sell:
                    gate_reasons.append(f"consensus_min (buy {buy_votes}/sell {sell_votes}, need {CONSENSUS_MIN})")
                else:
                    gate_reasons.append(f"trend_mismatch (trend {market['trend']}, signal {signal['signal']:+.2f})")

            old_capital = TRADE_DESK.state.capital
            new_capital = old_capital
            trade_record = None
            if acted:
                new_capital = old_capital * (1 + base_change)
                trend_multiplier = 1.0
                if market["trend"] == "up":
                    trend_multiplier = 1.0 + abs(market["trend_strength"]) * 0.3 if base_change > 0 else 1.0 - abs(market["trend_strength"]) * 0.3
                elif market["trend"] == "down":
                    trend_multiplier = 1.0 + abs(market["trend_strength"]) * 0.3 if base_change < 0 else 1.0 - abs(market["trend_strength"]) * 0.3
                new_capital = new_capital * trend_multiplier
                # One desk-level paper trade (not per-bot); costs applied once
                new_capital = apply_trading_costs(new_capital, 1)
                TRADE_DESK.add_position(
                    "GOBLIN",
                    "LONG" if base_change > 0 else "SHORT",
                    float(market["price"]),
                    bots=max(buy_votes, sell_votes),
                )
                pnl_frac = (new_capital - old_capital) / old_capital if old_capital else 0.0
                TRADE_DESK.close_position("GOBLIN", pnl_frac)
                _tick_pnls.append(pnl_frac * 100.0)
                trade_record = {
                    "tick": tick,
                    "symbol": market["symbol"],
                    "signal": round(float(signal["signal"]), 4),
                    "votes": {"buy": buy_votes, "sell": sell_votes, "pass": pass_count},
                    "trend": market["trend"],
                    "action": "BUY" if base_change > 0 else "SELL",
                    "base_change_pct": round(base_change * 100, 2),
                    "pnl_pct": round(pnl_frac * 100, 2),
                    "win": "win" if pnl_frac > 0 else "loss",
                }

            TRADE_DESK.update_capital(max(0.01, new_capital))

            # Update timestamp
            TRADE_DESK.state.last_update = datetime.now()

            # Print live summary with rationale
            if verbose:
                # Determine net signal
                buy_count = sum(1 for v in votes.values() if v == "buy")
                sell_count = sum(1 for v in votes.values() if v == "sell")
                pass_count = sum(1 for v in votes.values() if v == "pass")
                stand_down_count = sum(1 for v in votes.values() if v == "stand_down")
                hold_count = sum(1 for v in votes.values() if v == "hold")

                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Tick {tick} {market['symbol']}")
                print(f"  Market: {market['trend'].upper()} trend | {market['change24h']:+.1f}% 24h | vol {market['volume']:.2f} | "
                      f"rug {market['rug_risk']:.2f} | liq {market['liquidity']:.2f} | score {market['score']:.0f}")
                print(f"  Signal: {signal['signal']:+.2f} ({'BUY' if signal['signal'] > 0.05 else 'SELL' if signal['signal'] < -0.05 else 'HOLD'})")
                print(f"  Bot votes: BUY={buy_count} SELL={sell_count} PASS={pass_count} HOLD={hold_count} STAND_DOWN={stand_down_count}")
                print(f"  Stand-down: {'; '.join(gate_reasons) if gate_reasons else 'action taken'}")
                print(f"  Capital: ${TRADE_DESK.state.capital:.2f} (ticker: ${new_capital:.2f})")

            # Telegram alert per tick
            if TELEGRAM_CONFIGURED:
                TelegramAlert.alert(f"Tick {tick} | {market['symbol']} | capital ${TRADE_DESK.state.capital:.2f}", "info")

            # Generate HTML dashboard periodically
            if now - last_html > html_interval:
                html = TRADE_DESK.to_html()
                with open("trading_desk.html", "w") as f:
                    f.write(html)
                last_html = now

            # Write state JSON for web dashboard
            wins = sum(1 for p in _tick_pnls if p > 0)
            win_rate = (wins / len(_tick_pnls) * 100.0) if _tick_pnls else 0.0
            expectancy = (sum(_tick_pnls) / len(_tick_pnls)) if _tick_pnls else 0.0
            peak = TRADE_DESK.state.peak or TRADE_DESK.state.start_capital or 100.0
            current_dd = ((peak - TRADE_DESK.state.capital) / peak * 100.0) if peak else 0.0
            tick_record = {
                "tick": tick,
                "symbol": market["symbol"],
                "asset": TRADE_DESK.state.asset,
                "trend": market["trend"],
                "change24h": round(float(market["change24h"]), 3),
                "score": market["score"],
                "rug_risk": round(float(market["rug_risk"]), 3),
                "liquidity": round(float(market["liquidity"]), 3),
                "volume": round(float(market["volume"]), 3),
                "signal": round(float(signal["signal"]), 4),
                "votes": {"buy": buy_votes, "sell": sell_votes, "pass": pass_count},
            }
            _market_state["_ticks"].append(tick_record)
            if len(_market_state["_ticks"]) > 50:
                _market_state["_ticks"] = _market_state["_ticks"][-50:]
            TRADE_DESK.state.tick_history = list(_market_state["_ticks"])
            TRADE_DESK.update_state({
                "capital": TRADE_DESK.state.capital,
                "asset": TRADE_DESK.state.asset,
                "ticks": tick,
                "tick_count": tick,
                "tick_history": list(_market_state["_ticks"][-10:]),
                "positions": len([p for p in TRADE_DESK.state.positions if p.pnl is None]),
                "total_votes": TRADE_DESK.state.vote_results.get("total", 0),
                "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S-08:00"),
                "last_update": datetime.now().strftime("%H:%M:%S"),
                "session_running": True,
                "session_status": "PAPER-ONLY",
                "alerts": [TRADE_DESK.state.pending_alert] if TRADE_DESK.state.pending_alert else [],
                "votes": {
                    "buy": TRADE_DESK.state.vote_results.get("buy", 0),
                    "sell": TRADE_DESK.state.vote_results.get("sell", 0),
                    "pass": TRADE_DESK.state.vote_results.get("pass", 0),
                    "hold": TRADE_DESK.state.vote_results.get("hold", 0),
                    "stand_down": TRADE_DESK.state.vote_results.get("stand_down", 0),
                },
                "bots": [{"bot": b, "side": v, "score": market["score"], "liquidity": market["liquidity"],
                         "rug_risk": market["rug_risk"], "change24h": market["change24h"]} for b, v in trades.items()],
                "pnl": {
                    "drawdown": round(current_dd, 2),
                    "max_drawdown": round(TRADE_DESK.state.max_drawdown * 100.0, 2),
                    "win_rate": round(win_rate, 1),
                    "expectancy": round(expectancy, 2),
                    "total_trades": len(_tick_pnls),
                },
                "trade_history": list(_trade_log[-50:]),
                "error": None
            })

            # Verbose per-trade logging for tuning (state.json keeps last 50)
            if trade_record is not None:
                _trade_log.append(trade_record)

            # Sleep until next tick
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nSession stopped by user.")
        print(f"Total ticks processed: {tick}")

    # Final summary
    print("\n" + "=" * 72)
    print("  SESSION COMPLETE")
    print("=" * 72)
    print(f"  Ticks processed: {tick}")
    print(f"  Final capital: ${TRADE_DESK.state.capital:.2f}")
    print(f"  Final asset: {TRADE_DESK.state.asset}")
    print(f"  Open positions: {len(TRADE_DESK.state.positions)}")
    print(f"  Total votes: {TRADE_DESK.state.vote_results['total']}")
    print(f"  Last update: {TRADE_DESK.state.last_update}")
    print(f"  Final HTML: trading_desk.html")
    print("=" * 72)

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
