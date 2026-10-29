#!/usr/bin/env python3
"""
LYTA GrokBot Multi — Autonomous Multi-Bot Paper Trader

Open source multi-personality autonomous trader.
Inspired by Pump.fun AI agents but with explicit multiple Grok bots:
  - PUMP_CHASER
  - CONVICTION
  - MOMENTUM

All 100% paper trading. Zero burn. Observation only.
Realistic liquidity/volume model + bot-specific risk + liq-aware sizing.

Run:
  python3 grokbot_multi.py
  python3 grokbot_multi.py 5
  python3 grokbot_multi.py viable_test
"""

import os
import sys
import time
import random
import csv
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from datetime import datetime

# === Branding ===
BRAND = "LYTA GROKBOT MULTI • AUTONOMOUS PAPER TRADER"
MODE = "MULTI-BOT GROK SYSTEM — PAPER ONLY (ZERO BURN)"

# === Shared constants (from desk logic) ===
START_EQUITY = 280.0
MAX_POSITION_PCT = 0.08

# === Step 3: Bot-specific risk parameters (multi-bot core) ===
BOT_PROFILES = {
    "PUMP_CHASER": {
        "hard_stop": -0.055,
        "chatbot_tp": 0.50,      # classic 1.5x
        "trailing_trigger": 0.12,
        "max_rug_tolerance": 0.55,
        "position_mult": 1.05
    },
    "CONVICTION": {
        "hard_stop": -0.045,
        "chatbot_tp": 0.45,
        "trailing_trigger": 0.18,
        "max_rug_tolerance": 0.38,
        "position_mult": 0.90
    },
    "MOMENTUM": {
        "hard_stop": -0.065,
        "chatbot_tp": 0.55,
        "trailing_trigger": 0.10,
        "max_rug_tolerance": 0.48,
        "position_mult": 1.0
    }
}


@dataclass
class Position:
    symbol: str
    entry_price: float
    size: float
    high_water: float
    entry_time: str = ""
    analyst_score: float = 0.0
    liquidity_usd: float = 4500.0
    volume_5m: float = 1200.0
    bot: str = "GROK"


@dataclass
class DeskState:
    equity: float = START_EQUITY
    open_positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Dict] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


def realistic_price_move(liquidity_usd: float = 5000.0, volume_5m: float = 1000.0) -> float:
    """Realistic price move based on liquidity + volume (core model)."""
    liq = max(300.0, liquidity_usd)
    vol_factor = 0.28 * (8000.0 / liq)
    vol = max(0.08, min(0.65, vol_factor))

    move = random.gauss(0.005, vol)

    vol_norm = min(1.0, volume_5m / 15000.0)
    if vol_norm > 0.6 and random.random() < 0.35:
        move = move * 0.6 + random.gauss(0.03, 0.08)

    rug_chance = 0.09
    if liq < 2500:
        rug_chance += 0.11
    if random.random() < rug_chance:
        move = random.uniform(-0.78, -0.48)

    if random.random() < 0.035:
        move = random.uniform(0.55, 2.8)

    return max(-0.96, min(3.5, move))


class GrokBot:
    """Autonomous Grok bot with personality bias (the multi-bot heart)."""
    def __init__(self, name: str, bias: str, conviction: float = 0.75):
        self.name = name
        self.bias = bias
        self.conviction = conviction
        self.trades_made = 0
        self.profile = BOT_PROFILES.get(name, BOT_PROFILES["MOMENTUM"])

    def decide(self, survivor: dict) -> bool:
        score = float(survivor.get("analyst_score", 0.7))
        is_pump = bool(survivor.get("is_pump", False))
        change = float(survivor.get("price_change_m5", 0))
        buys = int(survivor.get("buys_m5", 0))
        liq = float(survivor.get("liquidity", 1000))
        rug = float(survivor.get("rug_risk", 0.25))

        prof = self.profile

        if self.bias == "pump":
            if is_pump:
                return score > 0.65 and rug < prof["max_rug_tolerance"]
            return score > 0.88 and change > -5
        elif self.bias == "conviction":
            return score >= self.conviction and rug < prof["max_rug_tolerance"]
        else:  # momentum
            return (change > 1 or buys > 4) and score > 0.70 and liq > 300


def load_survivors(limit: int = 12) -> list:
    """Load survivors (real file or strong realistic fallback)."""
    try:
        with open("monitor_log.csv", newline="") as f:
            r = csv.DictReader(f)
            rows = list(r)
        passed = [row for row in rows if str(row.get("filter_passed", "True")).lower() in ("true", "1", "yes")]
        if not passed:
            passed = rows
        recent = passed[-limit:]
        out = []
        for r in recent:
            out.append({
                "symbol": str(r.get("symbol", "UNK")),
                "analyst_score": float(r.get("analyst_score", 0.85)),
                "is_pump": str(r.get("is_pump", "False")).lower() in ("true", "1"),
                "price_change_m5": float(r.get("price_change_m5", 3.0)),
                "buys_m5": int(r.get("buys_m5", 6)),
                "liquidity": float(r.get("liquidity", 2500)),
                "rug_risk": float(r.get("rug_risk", 0.18)),
                "volume_5m": float(r.get("volume_5m", 800)),
                "price": float(r.get("price", 0.00001)),
            })
        return out
    except Exception:
        # Strong fallback so the multi-bot sim always runs standalone
        symbols = ["PUMP1", "LOOT", "SPERM", "RUGGY", "BLOSSOM", "FRESH", "SCS", "NEKO"]
        fallback = []
        for i in range(min(limit, 10)):
            sym = random.choice(symbols)
            fallback.append({
                "symbol": sym,
                "analyst_score": round(random.uniform(0.65, 0.92), 3),
                "is_pump": random.random() < 0.55,
                "price_change_m5": round(random.uniform(-4, 18), 1),
                "buys_m5": random.randint(3, 22),
                "liquidity": round(random.uniform(1200, 5200), 0),
                "rug_risk": round(random.uniform(0.12, 0.42), 3),
                "volume_5m": round(random.uniform(250, 1800), 0),
                "price": round(random.uniform(0.000005, 0.0008), 8),
            })
        return fallback


def paper_buy(state: DeskState, survivor: dict, bot_name: str) -> bool:
    if len(state.open_positions) >= 4 or state.equity <= 25:
        return False

    liq = float(survivor.get("liquidity", 2500.0))
    vol = float(survivor.get("volume_5m", 800.0))
    prof = BOT_PROFILES.get(bot_name, BOT_PROFILES["MOMENTUM"])

    max_liq_size = liq * 0.035
    base_size = state.equity * MAX_POSITION_PCT * prof.get("position_mult", 1.0)
    size = min(base_size, max_liq_size, 45.0)

    if size < 5.0:
        return False

    price = max(0.0000001, survivor.get("price", 0.00001) or random.uniform(0.000005, 0.0008))

    slippage = random.uniform(0.02, 0.08)
    fee_pct = 0.015
    effective_size = size * (1 - slippage - fee_pct)

    pos_id = f"{survivor['symbol']}_{int(time.time()*1000)}_{bot_name[:3]}"
    state.open_positions[pos_id] = Position(
        symbol=survivor["symbol"],
        entry_price=price * (1 + slippage),
        size=effective_size,
        high_water=price * (1 + slippage),
        entry_time=datetime.now().isoformat(),
        analyst_score=survivor.get("analyst_score", 0.8),
        liquidity_usd=liq,
        volume_5m=vol,
        bot=bot_name
    )
    state.equity -= size
    return True


def manage_risk_autonomous(state: DeskState):
    to_close = []
    for pid, pos in list(state.open_positions.items()):
        bot_name = getattr(pos, "bot", "MOMENTUM")
        prof = BOT_PROFILES.get(bot_name, BOT_PROFILES["MOMENTUM"])

        liq = getattr(pos, "liquidity_usd", 4500.0)
        vol = getattr(pos, "volume_5m", 1200.0)
        move = realistic_price_move(liquidity_usd=liq, volume_5m=vol)
        current_price = pos.entry_price * (1 + move)
        pnl_pct = (current_price - pos.entry_price) / pos.entry_price
        pos.high_water = max(pos.high_water, current_price)

        exit_reason = ""
        if pnl_pct <= prof["hard_stop"]:
            exit_reason = f"hard stop {int(prof['hard_stop']*100)}%"
        elif pnl_pct >= prof["chatbot_tp"]:
            exit_reason = "chatbot 1.5x TP"
        elif pnl_pct >= prof["trailing_trigger"] and current_price < pos.high_water * 0.94:
            exit_reason = "trailing stop"
        elif random.random() < 0.08:
            exit_reason = "take profit"

        if exit_reason:
            exit_slip = random.uniform(0.01, 0.05)
            exit_fee = 0.01
            adjusted_pnl_pct = pnl_pct * (1 - exit_slip - exit_fee)
            pnl = pos.size * adjusted_pnl_pct

            state.equity += pos.size + pnl
            state.trades.append({
                "symbol": pos.symbol,
                "pnl": round(pnl, 2),
                "pnl_pct": round(adjusted_pnl_pct * 100, 1),
                "reason": exit_reason,
                "entry_price": round(pos.entry_price, 8),
                "exit_price": round(current_price, 8),
                "bot": bot_name,
                "simulated_fees_slippage_applied": True
            })
            to_close.append(pid)
    for pid in to_close:
        state.open_positions.pop(pid, None)


def export_equity_curve(state: DeskState, start_equity: float):
    equity_curve = [start_equity]
    running = start_equity
    for t in state.trades:
        running += t["pnl"]
        equity_curve.append(running)

    with open("equity_curve_autonomous_grok.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "equity_usd", "pnl_cumulative"])
        for i, e in enumerate(equity_curve):
            w.writerow([i, e, round(e - start_equity, 2)])
    print(f"[export] equity_curve_autonomous_grok.csv ({len(equity_curve)} points)")


def run_autonomous_grok_bots(steps: int = 18):
    print(f"\n{'='*60}")
    print(f"{BRAND}")
    print(f"{MODE}")
    print(f"{'='*60}")
    print("STRICT: Zero real trades. All paper. Observation only.\n")

    state = DeskState(equity=START_EQUITY)
    bots = [
        GrokBot("PUMP_CHASER", "pump", conviction=0.68),
        GrokBot("CONVICTION", "conviction", conviction=0.82),
        GrokBot("MOMENTUM", "momentum", conviction=0.72)
    ]

    for step in range(steps):
        state.logs = state.logs[-10:]

        survivors = load_survivors(10)

        for bot in bots:
            for surv in random.sample(survivors, min(5, len(survivors))):
                if bot.decide(surv):
                    if paper_buy(state, surv, bot.name):
                        bot.trades_made += 1
                        break

        manage_risk_autonomous(state)

        is_pump_count = sum(1 for s in survivors if s.get("is_pump"))
        print(f"Step {step+1}/{steps} | Equity ${state.equity:.2f} | "
              f"Open: {len(state.open_positions)} | Bots: {len(bots)} | is_pump: {is_pump_count}")

        if step % 3 == 0 and state.trades:
            last = state.trades[-1]
            print(f"  Last: {last['bot']} {last['symbol']} {last['reason']} PnL {last['pnl']:+.2f}")

        time.sleep(0.4)

    # Exports (pure stdlib)
    if state.trades:
        with open("paper_trades_autonomous_grok.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=state.trades[0].keys())
            w.writeheader()
            w.writerows(state.trades)
        print(f"\n[export] paper_trades_autonomous_grok.csv ({len(state.trades)} trades)")

    export_equity_curve(state, START_EQUITY)

    # Summary
    wins = sum(1 for t in state.trades if t["pnl"] > 0)
    total_pnl = sum(t["pnl"] for t in state.trades)
    one_five_x = sum(1 for t in state.trades if "1.5x" in t["reason"])

    print(f"\n=== AUTONOMOUS GROK BOTS COMPLETE ===")
    print(f"Total paper trades: {len(state.trades)} | Wins: {wins} | Win rate: {wins/len(state.trades)*100:.1f}%" if state.trades else "No trades")
    print(f"Total paper PnL: ${total_pnl:.2f}")
    print(f"Final equity: ${state.equity:.2f} (start ${START_EQUITY})")
    print(f"1.5x TPs: {one_five_x}")

    print("\nPer-bot:")
    for bot in bots:
        bot_trades = [t for t in state.trades if t.get("bot", "").upper().startswith(bot.name[:3].upper())]
        if bot_trades:
            b_wins = sum(1 for t in bot_trades if t["pnl"] > 0)
            print(f"  {bot.name}: {len(bot_trades)} trades | {b_wins/len(bot_trades)*100:.0f}% win | PnL ${sum(t['pnl'] for t in bot_trades):.2f}")

    print("\nAll activity was PAPER ONLY. PATTERN PERSISTS.")
    return state


if __name__ == "__main__":
    steps = 18
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "viable_test":
            steps = 80
            print("=== VIABLE TEST MODE: 80 steps ===")
        else:
            try:
                steps = int(arg)
            except:
                pass
    run_autonomous_grok_bots(steps)
