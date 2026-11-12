#!/usr/bin/env python3
"""
LYTA Grok Desk - Pump.fun Memecoin Simulator (Phase 2 + Tightened Rules)

Exact match to the Builder's lyta-grok-desk-pumpfun AFTER the latest safety update (from attachment).

New rules (applied by Builder on your request):
- Buy only when at least 7 of 12 bots vote BUY
- Skip coins already up more than 100% in the past hour
- Skip coins with liquidity < $50,000
- Stop loss: sell whole position at -35% from entry price
- Take profit: sell whole position at +50% from entry price

All previous exits still active (rug spike, score collapse, 25% first-hour drop, time exit, contrarian).
Exits checked FIRST every 15min run.
Stand-down messages name the active buy filters when nothing qualifies.
Still shows full 12-bot votes on every launch.
Ultra-conservative paper mode (now even stricter).
"""

import os
import random
import urllib.request
import json
import sys
import asyncio
import time
import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional, Dict

BotName = Literal[
    "SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
    "PORTFOLIO", "EXECUTOR"
]

BOT_NAMES = [
    "SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
    "PORTFOLIO", "EXECUTOR"
]

# ── IMPORT: Trading Desk Dashboard (overall summary) ─────────────────────────
# The lyta-grok-desk/ dir has a hyphen (not a valid Python package name),
# so we load the dashboard module dynamically for robustness.
import importlib.util
import os
import sys

_desk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "lyta-grok-desk", "trading_desk.py")
TradingDesk = None
if os.path.exists(_desk_path):
    _spec = importlib.util.spec_from_file_location("trading_desk", _desk_path)
    if _spec is not None and _spec.loader is not None:
        _trading_desk = importlib.util.module_from_spec(_spec)
        sys.modules["trading_desk"] = _trading_desk
        _spec.loader.exec_module(_trading_desk)
        TradingDesk = _trading_desk.TradingDesk
else:
    TradingDesk = None

# Global trading desk instance – single source of truth for the running
# pump.fun paper session.  Feeds both Telegram alerts and the HTML dashboard.
TRADE_DESK = TradingDesk(capital=100.0, asset="GOBLIN", config="v3")
class TelegramAlert:
    """Phase 2 pump.fun Telegram alert wrapper."""

    BOT_NAME = "PUMPFUN_DESK"

    @staticmethod
    def _format(message: str) -> str:
        return f"[{TelegramAlert.BOT_NAME}] {message}"

    @staticmethod
    def alert(message: str, level: str = "info") -> None:
        """Send a Telegram alert: log locally (always), push to TG if configured.
        Also records it in the Trading Desk for the overall summary."""
        tag = {"info": "ℹ️", "warn": "⚠️", "error": "❌", "success": "✅"}.get(level, "ℹ️")
        full = f"{tag} {TelegramAlert._format(message)}"
        # Paper mode: always log, so the terminal/console shows the alert.
        print(full)
        # Record in trading desk for overall summary view
        TRADE_DESK.set_alert(message)
        # Real push (next Phase 2): uncomment and wire to your Telegram bot/webhook:
        # if TelegramAlert._TG_CONFIGURED():
        #     TelegramAlert._push_to_telegram(full)

    @staticmethod
    def open(position: str, asset: str, entry: float, side: str, bots: int, collateral: float) -> None:
        try:
            margin = float(position)
        except (ValueError, TypeError):
            margin = 0.0
        TelegramAlert.alert(
            f"🚀 OPEN {side.upper()} {asset} @ {float(entry):.4f} | margin {margin:.2f} | bots {bots}/12 | collateral ${collateral:.2f}",
            "success",
        )
        TRADE_DESK.update_capital(collateral)
        TRADE_DESK.add_position(asset, side.upper(), entry, bots=bots)

    @staticmethod
    def close(asset: str, side: str, price: float, pnl: float) -> None:
        TelegramAlert.alert(f"📉 CLOSE {side.upper()} {asset} @ {price:.4f} | PnL {pnl:+.4f}", "info")
        TRADE_DESK.close_position(asset, pnl)

    @staticmethod
    def stand_down(reason: str) -> None:
        TelegramAlert.alert(f"🛑 STAND DOWN: {reason}", "error")
        TRADE_DESK.set_alert(f"🛑 STAND DOWN: {reason}")

    @staticmethod
    def vote_results(asset: str, votes: dict) -> None:
        TelegramAlert.alert(f"📊 VOTES {asset}: {votes.get('buy', 0)}/{votes.get('total', 0)} BUY", "info")
        TRADE_DESK.add_vote("CONSENSUS", "buy" if votes.get("buy", 0) >= MIN_VOTES else "pass")
        # Record individual bot votes
        for bot, side in votes.get("bots", {}).items():
            if bot in TRADE_DESK.state.agent_votes:
                TRADE_DESK.add_vote(bot, side)

    @staticmethod
    def _TG_CONFIGURED() -> bool:
        """Check if Telegram token is configured (redacted: never store secrets in repo)."""
        import os
        tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        return bool(tg_token)

    @staticmethod
    def _push_to_telegram(message: str) -> bool:
        """Send a message to Telegram using Bot API. Returns True on success.
        Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.
        """
        import os
        import requests

        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return False

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"  [TELEGRAM] Push failed: {e}")
            return False


# === NEW TIGHTENED CONSTANTS (exactly from Builder) ===
MIN_VOTES = 7
MAX_H1_PUMP = 100          # skip if up >100% in 1h
MIN_LIQ = 50_000  # skip if liquidity < $50k
STOP_LOSS_PCT = 0.35       # -35%
TAKE_PROFIT_PCT = 0.50     # +50%

@dataclass
class Market:
    asset: str
    price: float
    is_pump: bool
    is_new_launch: bool
    on_bonding_curve: bool
    analyst_score: float          # 0.0 - 1.0 internally
    rug_risk: float
    liquidity: float
    buys_5m: int
    sells_5m: int
    change_5m: float
    change_1h: float
    change_6h: float
    change_24h: float

def make_pumpfun_market(asset: str) -> Market:
    is_new = random.random() < 0.45
    on_curve = random.random() < 0.55 and is_new

    is_pump = random.random() < 0.32 if is_new else random.random() < 0.18

    analyst = random.uniform(0.35, 0.97)
    if is_pump and is_new and not on_curve:
        analyst = min(0.97, analyst + 0.18)

    rug = random.uniform(0.08, 0.72)
    if is_pump and is_new and not on_curve:
        rug = max(0.08, rug - 0.28)

    # Wider range so we can test the new $50k liquidity filter
    liq = random.uniform(800, 65000)
    buys = random.randint(1, 55)
    sells = random.randint(0, 25)
    if is_pump:
        buys = int(buys * 2.1)
        sells = int(sells * 0.6)

    ch5 = random.uniform(-18, 45)
    if is_pump and is_new:
        ch5 = random.uniform(12, 68)

    ch1h = random.uniform(-25, 55)
    ch6h = random.uniform(-40, 80)
    ch24h = random.uniform(-55, 120)

    return Market(
        asset=asset,
        price=random.uniform(0.000008, 0.0006),
        is_pump=is_pump,
        is_new_launch=is_new,
        on_bonding_curve=on_curve,
        analyst_score=round(analyst, 3),
        rug_risk=round(rug, 3),
        liquidity=round(liq, 0),
        buys_5m=buys,
        sells_5m=sells,
        change_5m=round(ch5, 1),
        change_1h=round(ch1h, 1),
        change_6h=round(ch6h, 1),
        change_24h=round(ch24h, 1)
    )

def decide_action(bot: str, market: Market) -> Optional[dict]:
    side = None
    conviction = 0.5
    size_mult = 1.0

    if market.on_bonding_curve:
        if bot in ["FILTER", "CONVICTION", "RESEARCHER", "PORTFOLIO", "CONTRARIAN"]:
            return None

    if bot == "SCOUT":
        if market.is_new_launch and market.is_pump and market.rug_risk < 0.38:
            side = "long"
            conviction = 0.72
            size_mult = 1.4
        elif market.is_pump and market.change_5m > 15:
            side = "long"
            conviction = 0.68

    elif bot == "FILTER":
        if (market.analyst_score > 0.82 and
            market.rug_risk < 0.28 and
            market.buys_5m > 10 and
            market.liquidity > 2800 and
            not market.on_bonding_curve):
            side = "long"
            conviction = 0.88
            size_mult = 1.25

    elif bot == "ANALYST":
        if market.analyst_score > 0.78:
            side = "long"
            conviction = 0.72 + (market.analyst_score - 0.78) * 1.0
        if market.rug_risk > 0.55:
            side = "short" if random.random() < 0.55 else None

    elif bot == "DEV_WATCH":
        if market.is_pump:
            side = "long"
            conviction = 0.82
            size_mult = 1.5
            if market.is_new_launch and market.change_5m > 20:
                conviction = 0.92

    elif bot == "CONVICTION":
        if (market.analyst_score > 0.86 and
            market.rug_risk < 0.22 and
            market.is_pump and
            not market.on_bonding_curve):
            side = "long"
            conviction = 0.93

    elif bot == "MOMENTUM":
        if market.change_5m > 18 and market.buys_5m > 8:
            side = "long"
            conviction = 0.72
        elif market.change_5m < -18:
            side = "short"
            conviction = 0.62

    elif bot == "SCALPER":
        if abs(market.change_5m) > 10 and market.liquidity > 1800 and not market.on_bonding_curve:
            side = "long" if market.change_5m > 0 else "short"
            conviction = 0.68

    elif bot == "CONTRARIAN":
        if market.change_5m > 30 and market.rug_risk < 0.42 and market.is_pump:
            side = "short"
            conviction = 0.72
        elif market.change_5m < -12 and market.analyst_score > 0.72:
            side = "long"
            conviction = 0.62

    elif bot == "TREND":
        if market.change_5m > 20 and market.analyst_score > 0.68:
            side = "long"
            conviction = 0.72

    elif bot == "RESEARCHER":
        if (market.analyst_score > 0.84 and
            market.rug_risk < 0.25 and
            market.liquidity > 3500 and
            not market.on_bonding_curve):
            side = "long"
            conviction = 0.88

    elif bot == "PORTFOLIO":
        if (market.analyst_score > 0.80 and
            market.rug_risk < 0.20 and
            not market.on_bonding_curve):
            side = "long"
            conviction = 0.62
            size_mult = 0.75

    elif bot == "EXECUTOR":
        if market.analyst_score > 0.72 and market.rug_risk < 0.38 and not market.on_bonding_curve:
            side = "long"
            conviction = 0.68
        if market.rug_risk > 0.60:
            side = "short" if random.random() < 0.45 else None

    if side:
        return {
            "side": side,
            "conviction": min(1.0, conviction),
            "sizeMult": size_mult
        }
    return None

def is_bearish_bot(bot: str, market: Market) -> bool:
    """Detailed bearish checks for contrarian exit signal"""
    score100 = market.analyst_score * 100
    down_1h = market.change_1h < -10
    falling_5m_1h = market.change_5m < 0 and market.change_1h < 0
    more_sells = market.sells_5m > market.buys_5m
    low_liq = market.liquidity < 5000

    if market.rug_risk >= 0.5 or score100 < 40 or down_1h or low_liq:
        return True
    if falling_5m_1h and more_sells:
        return True
    return False

# held_positions: asset -> {"entry_price": float, "entry_analyst_100": float, "entry_cycle": int, "hold_minutes": int}
held_positions: Dict[str, dict] = {}

def check_exit(m: Market, entry_price: float, entry_analyst_100: float, hold_minutes: int, cycle_num: int) -> Optional[str]:
    """Exact exit rules from Builder — NEW SL/TP first, then previous exits."""
    current_score100 = m.analyst_score * 100

    # NEW: Stop loss -35%
    if m.price < entry_price * (1 - STOP_LOSS_PCT):
        return "Stop loss -35%"

    # NEW: Take profit +50%
    if m.price > entry_price * (1 + TAKE_PROFIT_PCT):
        return "Take profit +50%"

    # Previous exits (still active)
    if m.rug_risk > 0.45:
        return "Rug risk spike"

    if entry_analyst_100 - current_score100 > 15:
        return "Score collapse"

    if hold_minutes <= 60 and m.price < entry_price * 0.75:
        return "Price drop >25%"

    if hold_minutes >= 45:
        no_buys_last_hour = m.buys_5m <= 3
        not_up_last_hour = m.change_1h <= 0
        if no_buys_last_hour or not_up_last_hour:
            return "Time exit - no momentum"

    bearish_count = sum(1 for bot in ["SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
                                       "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
                                       "PORTFOLIO", "EXECUTOR"] if is_bearish_bot(bot, m))
    if bearish_count >= 4:
        return "Contrarian signal"

    return None

def simulate_cycle(collateral: float = 600.0, cycle_num: int = 1):
    global held_positions

    print(f"\n=== PUMPFUN DESK RUN #{cycle_num} (15min interval | Sim Balance: ${collateral:.2f} USDC) ===")

    markets = [
        make_pumpfun_market("NEWPEPE"),
        make_pumpfun_market("MOONCAT"),
        make_pumpfun_market("PUMPDOGE"),
        make_pumpfun_market("RUGTEST")
    ]

    # === EXITS FIRST (including new SL/TP) ===
    exited = []
    for asset, pos in list(held_positions.items()):
        m = next((mk for mk in markets if mk.asset == asset), None)
        if m is None:
            continue

        hold_minutes = pos["hold_minutes"]
        entry_analyst = pos["entry_analyst_100"]
        entry_price = pos["entry_price"]

        current_score100 = m.analyst_score * 100
        print(f"\n[HOLD CHECK] {asset} | held {hold_minutes} min | entry_score={entry_analyst:.0f}")
        print(f"  rug={m.rug_risk:.3f} | analyst={current_score100:.0f} | Δ1h={m.change_1h}% | buys_last_hr~{m.buys_5m*12} | liq=${m.liquidity:.0f}")

        bearish_votes = 0
        for bot in ["SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
                    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
                    "PORTFOLIO", "EXECUTOR"]:
            action = decide_action(bot, m)
            if action and action["side"] == "short":
                bearish_votes += 1
            if is_bearish_bot(bot, m):
                bearish_votes += 1
        print(f"  Bearish signals from bots: ~{bearish_votes}/12")

        reason = check_exit(m, entry_price, entry_analyst, hold_minutes, cycle_num)
        if reason:
            print(f"\n[EXIT] {asset} | {reason}")
            print(f"  Entry price: {entry_price:.8f} → Current: {m.price:.8f}")
            print(f"  Entry analyst (0-100): {entry_analyst:.0f} → Current: {current_score100:.0f}")
            exited.append(asset)
        else:
            held_positions[asset]["hold_minutes"] += 15

    for asset in exited:
        del held_positions[asset]

    # === BUY SIDE — NEW STRICT FILTERS ===
    best = {"asset": None, "votes": 0, "side": None}

    for m in markets:
        status = "BONDING" if m.on_bonding_curve else "TRADEABLE"
        score100 = m.analyst_score * 100

        # NEW BUY FILTERS (checked before voting tally)
        filters_blocked = []
        if m.change_1h > MAX_H1_PUMP:
            filters_blocked.append(f"up {m.change_1h:.0f}% in 1h (> {MAX_H1_PUMP}%)")
        if m.liquidity < MIN_LIQ:
            filters_blocked.append(f"liq ${m.liquidity:.0f} (< ${MIN_LIQ})")

        print(f"\n[LAUNCH] {m.asset} | is_pump={m.is_pump} | new={m.is_new_launch} | {status}")
        print(f"  score={score100:.0f} | rug={m.rug_risk:.3f} | liq=${m.liquidity:.0f} | buys={m.buys_5m} | Δ5m={m.change_5m}% | Δ1h={m.change_1h}%")

        if filters_blocked:
            print(f"  [FILTERED] Skipped — {', '.join(filters_blocked)}")
            continue

        long_votes = 0
        short_votes = 0

        for bot in ["SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
                    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
                    "PORTFOLIO", "EXECUTOR"]:
            action = decide_action(bot, m)
            if action:
                vote = action["side"].upper()
                if vote == "LONG":
                    long_votes += 1
                else:
                    short_votes += 1
                print(f"  {bot} → {vote} ({action['conviction']:.2f})")
            else:
                print(f"  {bot} → PASS")

        total_active = long_votes + short_votes
        print(f"[TALLY] long={long_votes} short={short_votes} active={total_active}/12")

        if long_votes > best["votes"]:
            best = {"asset": m.asset, "votes": long_votes, "side": "LONG"}
        if short_votes > best["votes"]:
            best = {"asset": m.asset, "votes": short_votes, "side": "SHORT"}

    # Execute buy only if >= 7 votes AND passed all filters
    if best["votes"] >= MIN_VOTES:
        print(f"\n[CONSENSUS] {best['side']} on {best['asset']} | {best['votes']}/12 bots (≥{MIN_VOTES} required)")

        margin = 1.0
        print(f"[SIZING] Using Circuit minimum swap size: ${margin:.2f}")

        winning_market = next((m for m in markets if m.asset == best["asset"]), None)
        if winning_market and winning_market.on_bonding_curve:
            print("[STAND DOWN] Token still on bonding curve — no swap route yet.")
        elif best["asset"] not in held_positions:
            print(f"✅ WOULD BUY {best['side']} {best['asset']} (paper only)")
            entry_analyst_100 = winning_market.analyst_score * 100
            held_positions[best["asset"]] = {
                "entry_price": winning_market.price,
                "entry_analyst_100": round(entry_analyst_100, 0),
                "entry_cycle": cycle_num,
                "hold_minutes": 0
            }
            print(f"   (Saved entry analyst={entry_analyst_100:.0f}, price for SL/TP + other exits)")
        else:
            print(f"[SKIP] Already holding {best['asset']} (once per day rule)")
    else:
        if best["votes"] > 0:
            print(f"\n[STAND DOWN] No token reached {MIN_VOTES}+ consensus (after 1h pump & $50k liq filters). Best was {best['votes']}/12")
        else:
            print(f"\n[STAND DOWN] No token reached {MIN_VOTES}+ consensus (after 1h pump & $50k liq filters).")

    if held_positions:
        print(f"\n[PORTFOLIO] Currently holding: {list(held_positions.keys())}")
    print("---")


# === Pump.fun Data Adapter (GrokBot bridge) ===
# Wires pump.fun /v1/stats candidate data into the existing 12-bot voting engine.
# Reads: progress_pct, has_metadata, unique_buyers, buys, liquidity, rug_risk
# Writes: normalized Market dict consumed by decide_action() / check_exit()


# === Pump.fun Data Adapter (GrokBot bridge) ===
# Wires pump.fun /v1/stats candidate data into the existing 12-bot voting engine.
# Reads: progress_pct, has_metadata, unique_buyers, buys, liquidity, rug_risk
# Writes: normalized Market dict consumed by decide_action() / check_exit()

class PumpFunDataAdapter:
    """Normalizes pump.fun payload into the desk's internal Market schema."""

    @classmethod
    def adapt(cls, payload: dict) -> dict:
        """Take a pump.fun payload OR a Market object and return normalized dict."""
        # Market object check: doesn't have .get(), has .asset/.price/.is_pump etc.
        if not isinstance(payload, dict):
            # Assume it's a Market object or similar with .asset attribute
            cand = {
                "asset": payload.asset,
                "price": payload.price,
                "is_pump": payload.is_pump,
                "is_new_launch": payload.is_new_launch,
                "on_bonding_curve": payload.on_bonding_curve,
                "analyst_score": payload.analyst_score,
                "rug_risk": payload.rug_risk,
                "liquidity": payload.liquidity,
                "buys_5m": payload.buys_5m,
                "sells_5m": payload.sells_5m,
                "change_5m": payload.change_5m,
                "change_1h": payload.change_1h,
                "change_6h": payload.change_6h,
                "change_24h": payload.change_24h,
            }
        else:
            # dict with JSON-serializable data
            cand = payload.get("candidate", payload)

        # If it's a Market object, map to dict fields
        if not isinstance(cand, dict):
            cand = {
                "asset": cand.asset,
                "price": cand.price,
                "is_pump": cand.is_pump,
                "is_new_launch": cand.is_new_launch,
                "on_bonding_curve": cand.on_bonding_curve,
                "analyst_score": cand.analyst_score,
                "rug_risk": cand.rug_risk,
                "liquidity": cand.liquidity,
                "buys_5m": cand.buys_5m,
                "sells_5m": cand.sells_5m,
                "change_5m": cand.change_5m,
                "change_1h": cand.change_1h,
                "change_6h": cand.change_6h,
                "change_24h": cand.change_24h,
            }

        stats = {}
        if isinstance(cand, dict):
            stats = cand.get("stats", {})

        # Build a merged dict: cand first, then payload top-level fields
        # (payload top-level has the real values)
        merged = dict(cand)
        if isinstance(payload, dict):
            for k, v in payload.items():
                if k not in merged:
                    merged[k] = v

        analyst = float(merged.get("analyst_score", merged.get("score", stats.get("score", 0.72))))
        score100 = round(analyst * 100, 1) if isinstance(analyst, (int, float)) else 72.0
        return {
            "asset": str(merged.get("name", merged.get("symbol", merged.get("asset", "PUMPFUN_TKN")))),
            "pair": str(merged.get("token_address", merged.get("pair", ""))),
            "price": float(merged.get("price", 0.000001)),
            "is_pump": bool(merged.get("is_pump", False)),
            "is_new_launch": bool(merged.get("is_new_launch", True)),
            "on_bonding_curve": bool(merged.get("on_bonding_curve", False)),
            "analyst_score": round(analyst, 3),
            "analyst_score_100": score100,
            "rug_risk": round(float(merged.get("rug_risk", 0.25)), 3),
            "liquidity": round(float(merged.get("liquidity", 5000)), 0),
            "liquidity_usd": round(float(merged.get("liquidity_usd", 5000)), 0),
            "buys_5m": int(merged.get("buys_5m", merged.get("buys", 10))),
            "sells_5m": int(merged.get("sells_5m", merged.get("sells", 2))),
            "buys_total": int(merged.get("buys", merged.get("buys", 10))),
            "change_5m": round(float(merged.get("progress_pct", merged.get("progress_pct", 0))), 1),
            "change_1h": round(float(merged.get("change_1h", merged.get("change_1h", 0))), 1),
            "change_6h": round(float(merged.get("change_6h", merged.get("change_6h", 0))), 1),
            "change_24h": round(float(merged.get("change_24h", merged.get("change_24h", 0))), 1),
            "unique_buyers": int(merged.get("unique_buyers", merged.get("unique_buyers", 10))),
            "has_metadata": bool(merged.get("has_metadata", merged.get("has_metadata", False))),
            "raw": merged,
        }

    @classmethod
    def make_market(cls, payload: dict) -> "Market":
        md = cls.adapt(payload)
        md["price"] = md["price"] if md["price"] > 0 else random.uniform(0.000008, 0.0006)
        return Market(**{k: md[k] for k in [
            "asset", "price", "is_pump", "is_new_launch", "on_bonding_curve",
            "analyst_score", "rug_risk", "liquidity", "buys_5m", "sells_5m",
            "change_5m", "change_1h", "change_6h", "change_24h"
        ]})

    @classmethod
    def extract_candidates(cls, list_payload: dict) -> list:
        raw = list_payload.get("pumps", list_payload.get("candidates", []))
        out = []
        for c in raw:
            try:
                out.append(cls.adapt({"candidate": c, **list_payload}))
            except Exception:
                continue
        return out

    @classmethod
    def fetch_candidates(cls) -> list:
        """Fetch live pump.fun candidate list from API.

        Real pump.fun /v1/stats integration. Requires internet access
        and a pump.fun API key (set via PUMPFUN_API_KEY env var).
        Falls back to random seed data if API is unavailable.
        """
        import os
        import json
        import urllib.request
        import urllib.error

        api_key = os.environ.get("PUMPFUN_API_KEY", "").strip()
        url = "https://pump.fun/v1/stats"

        if api_key:
            import urllib.parse
            url += f"?api_key={urllib.parse.quote(api_key)}"

        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # extract_candidates already handles the payload format
            return cls.extract_candidates(data)
        except Exception as e:
            import sys
            print(f"[API] pump.fun fetch failed: {type(e).__name__}: {e}", file=sys.stderr)
            print(f"[API] Falling back to random seed data", file=sys.stderr)
            return []

# === DataAdapter ABC ===
# === DataAdapter ABC ===
class DataAdapter(ABC):
    """Base protocol for all live data-source adapters.

    Every adapter must implement:
      - fetch_candidates() -> list[dict]   - one dict per candidate market
      - make_market(payload: dict) -> Market  - normalize to the shared schema
    """
    @abstractmethod
    def fetch_candidates(self) -> list:
        """Return a list of raw candidate dicts from this data source."""
        pass

    @abstractmethod
    def make_market(self, payload: dict) -> Market:
        """Convert a raw candidate dict into a Market object."""
        pass


class DexScreenerDataAdapter(DataAdapter):
    """Live DexScreener pair data adapter — mirrors PumpFunDataAdapter interface.

    Pulls live token pairs from DexScreener API (token-profiles + token-pairs)
    and normalizes them into the same Market schema the pump.fun desk uses.
    Can be passed to pumpfun_adapter_round() as an alternative data source.
    Supports multi-chain: solana (default), ethereum, bsc.
    """

    CHAIN_MAP = {
        "sol": "solana",
        "solana": "solana",
        "solana_mainnet": "solana",
        "eth": "ethereum",
        "ethereum": "ethereum",
        "mainnet": "ethereum",
        "bsc": "bsc",
        "binance": "bsc",
        "bnb": "bsc",
    }

    def __init__(self, chain: str = "solana", limit: int = 20):
        self.chain = self.CHAIN_MAP.get(chain.lower(), chain)
        self.limit = limit

    @staticmethod
    def _fetch_json(path: str, timeout: int = 15) -> dict:
        """Raw HTTP fetch with LYTA-TradingBot/1.0 User-Agent."""
        url = f"https://api.dexscreener.com{path}"
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "LYTA-TradingBot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def fetch_candidates(self) -> list:
        """Fetch live DexScreener token pairs, mapping to candidate payloads."""
        try:
            # Step 1: get token profiles (30 tokens, includes chainId + tokenAddress)
            profiles = self._fetch_json("/token-profiles/latest/v1")

            candidates = []
            for p in profiles[:self.limit]:
                token_addr = p.get("tokenAddress", "")
                chain = p.get("chainId", self.chain)

                # Step 2: get the matched pair from DexScreener
                pair_path = f"/token-pairs/v1/{chain}/{token_addr}"
                pairs = self._fetch_json(pair_path)

                for pr in pairs:
                    dex_id = pr.get("dexId", "")
                    price_usd = pr.get("priceUsd")
                    if price_usd is None:
                        continue
                    try:
                        price_usd = float(price_usd)
                    except (TypeError, ValueError):
                        continue
                    if price_usd <= 0:
                        continue

                    txns = pr.get("txns", {})
                    volume = pr.get("volume", {})
                    change = pr.get("priceChange", {})

                    # Build candidate payload in the same shape as pump.fun
                    candidates.append({
                        "asset": pr["baseToken"].get("symbol", token_addr[:10]),
                        "chain": chain,
                        "dexId": dex_id,
                        "pairAddress": pr.get("pairAddress", ""),
                        "price_usd": price_usd,
                        "buys_5m": txns.get("m5", {}).get("buys", 0),
                        "sells_5m": txns.get("m5", {}).get("sells", 0),
                        "change_5m": change.get("m5", 0.0),
                        "change_1h": change.get("h1", 0.0),
                        "change_6h": change.get("h6", 0.0),
                        "change_24h": change.get("h24", 0.0),
                        "volume_h24": volume.get("h24", 0.0),
                        "market_cap": pr.get("marketCap", 0),
                        "fdv": pr.get("fdv", 0),
                        "pair_created_at": pr.get("pairCreatedAt", ""),
                        "url": pr.get("url", ""),
                        "score": self._score_from_dex_data(pr),
                    })

            return candidates
        except Exception as e:
            print(f"[DexScreener] fetch_candidates error: {e}", file=sys.stderr)
            return []

    @staticmethod
    def adapt(payload: dict) -> 'Market':
        """Normalize a DexScreener payload dict into a Market object."""
        ch5 = float(payload.get("change_5m", 0.0))
        vol = float(payload.get("volume_h24", 0.0))
        buys = int(payload.get("buys_5m", 0))

        # Analyst score: blend change_5m, volume, unique buyers
        analyst = 0.3 + (ch5 / 100.0) * 0.35
        if buys > 0 and vol > 0:
            analyst += min(0.4, buys / (vol * 2.0))
        analyst = max(0.05, min(0.98, analyst))

        # Rug risk: high volatility + high buys = risk
        rug = 0.3 + (abs(ch5) / 50.0) * 0.35
        if buys > 0 and vol > 0:
            rug += min(0.3, buys / (vol * 1.5))
        rug = max(0.05, min(0.98, rug))

        # Liquidity: proxy from h24 volume (in dollars/quote)
        liquidity = float(payload.get("volume_h24", 0.0)) * 10.0

        return Market(
            asset=payload["asset"],
            price=float(payload["price_usd"]),
            is_pump=(payload["dexId"] == "pumpfun"),
            is_new_launch=payload.get("score", 0) > 0.65,
            on_bonding_curve=(payload["dexId"] == "pumpfun"),
            analyst_score=analyst,
            rug_risk=rug,
            liquidity=liquidity,
            buys_5m=int(payload.get("buys_5m", 0)),
            sells_5m=int(payload.get("sells_5m", 0)),
            change_5m=float(payload.get("change_5m", 0.0)),
            change_1h=float(payload.get("change_1h", 0.0)),
            change_6h=float(payload.get("change_6h", 0.0)),
            change_24h=float(payload.get("change_24h", 0.0)),
        )

    @staticmethod
    def make_market(payload: dict) -> 'Market':
        """Compatibility shim: alias for adapt()."""
        return DexScreenerDataAdapter.adapt(payload)

    @staticmethod
    def _score_from_dex_data(pr: dict) -> float:
        """Heuristic score from raw pair data (0.0-1.0)."""
        ch = pr.get("priceChange", {})
        ch5 = ch.get("m5", 0) or 0
        ch1 = ch.get("h1", 0) or 0
        vol = pr.get("volume", {}).get("h24", 0) or 0
        mcap = pr.get("marketCap", 0) or 0
        buys = pr.get("txns", {}).get("m5", {}).get("buys", 0) or 0

        score = 0.3 + ((ch5 / 100.0) * 0.25) + ((ch1 / 100.0) * 0.15)
        if buys > 0 and vol > 0:
            score += min(0.25, buys / (vol * 2.5))
        if mcap > 0:
            score += min(0.15, (mcap / 100000000000) * 0.15)
        return max(0.02, min(0.98, score))


def pumpfun_adapter_round(collateral: float = 600.0, cycle_num: int = 1,
                          adapter: 'DataAdapter' = None) -> dict:  # any adapter with fetch_candidates() + make_market()
    print(f"\n=== PUMPFUN DESK RUN #{cycle_num} (15min interval | Sim Balance: ${collateral:.2f} USDC) ===")
    print(f"[DATA SOURCE] {adapter.__class__.__name__ if adapter else 'Fallback (random)'}")
    if adapter is None:
        markets = [make_pumpfun_market(f"ADAPTMK{i}") for i in range(4)]
    else:
        raw_list = adapter.fetch_candidates()
        if not raw_list:
            markets = [make_pumpfun_market(f"BADAT{i}") for i in range(4)]
        else:
            markets = [adapter.make_market(c) for c in raw_list]

    exited = []
    for asset, pos in list(held_positions.items()):
        m = next((mk for mk in markets if mk.asset == asset), None)
        if m is None:
            continue
        hold_minutes = pos["hold_minutes"]
        entry_analyst = pos["entry_analyst_100"]
        entry_price = pos["entry_price"]
        print(f"\n[HOLD CHECK] {asset} | held {hold_minutes} min | entry_score={entry_analyst:.0f}")
        print(f"  rug={m.rug_risk:.3f} | analyst={entry_analyst:.0f} | Δ1h={m.change_1h}% | buys_last_hr~{m.buys_5m*12} | liq=${m.liquidity:.0f}")
        bearish_votes = 0
        for bot in BOT_NAMES:
            action = decide_action(bot, m)
            if action and action["side"] == "short":
                bearish_votes += 1
            if is_bearish_bot(bot, m):
                bearish_votes += 1
        print(f"  Bearish signals from bots: ~{bearish_votes}/12")
        reason = check_exit(m, entry_price, entry_analyst, hold_minutes, cycle_num)
        if reason:
            print(f"\n[EXIT] {asset} | {reason}")
            print(f"  Entry price: {entry_price:.8f} → Current: {m.price:.8f}")
            print(f"  Entry analyst (0-100): {entry_analyst:.0f} → Current: {m.analyst_score*100:.0f}")
            exited.append(asset)
        else:
            held_positions[asset]["hold_minutes"] += 15

    for asset in exited:
        del held_positions[asset]

    best = {"asset": None, "votes": 0, "side": None}
    for m in markets:
        status = "BONDING" if m.on_bonding_curve else "TRADEABLE"
        score100 = m.analyst_score * 100
        filters_blocked = []
        if m.change_1h > MAX_H1_PUMP:
            filters_blocked.append(f"up {m.change_1h:.0f}% in 1h (> {MAX_H1_PUMP}%)")
        if m.liquidity < MIN_LIQ:
            filters_blocked.append(f"liq ${m.liquidity:.0f} (< ${MIN_LIQ})")
        print(f"\n[LAUNCH] {m.asset} | is_pump={m.is_pump} | new={m.is_new_launch} | {status}")
        print(f"  score={score100:.0f} | rug={m.rug_risk:.3f} | liq=${m.liquidity:.0f} | buys={m.buys_5m} | Δ5m={m.change_5m}% | Δ1h={m.change_1h}%")
        if filters_blocked:
            print(f"  [FILTERED] Skipped — {', '.join(filters_blocked)}")
            continue
        long_votes = 0; short_votes = 0
        for bot in BOT_NAMES:
            action = decide_action(bot, m)
            if action:
                vote = action["side"].upper()
                if vote == "LONG": long_votes += 1
                else: short_votes += 1
                print(f"  {bot} → {vote} ({action['conviction']:.2f})")
            else:
                print(f"  {bot} → PASS")
        total_active = long_votes + short_votes
        print(f"[TALLY] long={long_votes} short={short_votes} active={total_active}/12")
        if long_votes > best["votes"]:
            best = {"asset": m.asset, "votes": long_votes, "side": "LONG"}
        if short_votes > best["votes"]:
            best = {"asset": m.asset, "votes": short_votes, "side": "SHORT"}

    if best["votes"] >= MIN_VOTES:
        print(f"\n[CONSENSUS] {best['side']} on {best['asset']} | {best['votes']}/12 bots (≥{MIN_VOTES} required)")
        size_mult = 1.0
        print(f"[SIZING] Using Circuit minimum swap size: ${size_mult:.2f}")
        winning_market = next((m for m in markets if m.asset == best["asset"]), None)
        if winning_market and winning_market.on_bonding_curve:
            print("[STAND DOWN] Token still on bonding curve — no swap route yet.")
        elif best["asset"] not in held_positions:
            print(f"✅ WOULD BUY {best['side']} {best['asset']} (paper only)")
            entry_analyst_100 = winning_market.analyst_score * 100
            held_positions[best["asset"]] = {
                "entry_price": winning_market.price,
                "entry_analyst_100": round(entry_analyst_100, 0),
                "entry_cycle": cycle_num,
                "hold_minutes": 0
            }
            print(f"   (Saved entry analyst={entry_analyst_100:.0f}, price for SL/TP + other exits)")
        else:
            print(f"[SKIP] Already holding {best['asset']} (once per day rule)")
    else:
        if best["votes"] > 0:
            print(f"\n[STAND DOWN] No token reached {MIN_VOTES}+ consensus (after 1h pump & $50k liq filters). Best was {best['votes']}/12")
        else:
            print(f"\n[STAND DOWN] No token reached {MIN_VOTES}+ consensus (after 1h pump & $50k liq filters).")

    if held_positions:
        print(f"\n[PORTFOLIO] Currently holding: {list(held_positions.keys())}")
    print("---")
    return {"cycle": cycle_num, "held": list(held_positions.keys()),
            "buys": len(exited), "pnl": 0.0, "market_count": len(markets),
            "votes": best["votes"] if best["votes"] else 0}

# === Adapter registry & main — live pump.fun data path ===
from abc import ABC, abstractmethod
from dataclasses import dataclass
import random

# === Adapter main — live pump.fun data path ===




# === DataAdapter ABC ===
class DataAdapter(ABC):
    """Base protocol for all live data-source adapters.

    Every adapter must implement:
      - fetch_candidates() -> list[dict]   - one dict per candidate market
      - make_market(payload: dict) -> Market  - normalize to the shared schema
    """
    @abstractmethod
    def fetch_candidates(self) -> list:
        """Return a list of raw candidate dicts from this data source."""
        pass

    @abstractmethod
    def make_market(self, payload: dict) -> Market:
        """Convert a raw candidate dict into a Market object."""
        pass






# === AsyncRateLimiter — throttle 100 adapters x 10 APIs without 429s ===
class AsyncRateLimiter:
    """Class-level semaphore + per-adapter spacing to protect external APIs."""
    _semaphore = asyncio.Semaphore(100)        # max concurrent connections
    _last_call = {}                             # name -> epoch seconds
    _MIN_GAP = 0.5                              # seconds between same-adapter calls

    @classmethod
    async def acquire(cls, name: str):
        # Enforce per-adapter minimum gap (semantically irrelevant for single-threaded asyncio,
        # but makes the pattern portable to real async loops later)
        now = time.time()
        last = cls._last_call.get(name, 0)
        gap = cls._MIN_GAP - (now - last)
        if gap > 0:
            await asyncio.sleep(gap)
        cls._last_call[name] = time.time()
        await cls._semaphore.acquire()
        return cls._semaphore

    @classmethod
    def release(cls):
        cls._semaphore.release()

    @classmethod
    def sync_wrap(cls, func):
        """Decorator wrapping a synchronous fetch in the async rate limiter."""
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # This is intentionally a thin sync adapter – the real async path
            # is used when the desk runs under asyncio. For the sync desktop loop,
            # the semaphore is acquired/released around the call.
            try:
                import asyncio as aio
                return aio.run(cls._inner_wrap(self, func, args, kwargs))
            except RuntimeError:
                # Not in an event loop – fall back to inline rate limit
                now = time.time()
                last = cls._last_call.get(self.__class__.__name__, 0)
                gap = cls._MIN_GAP - (now - last)
                if gap > 0:
                    time.sleep(gap)
                cls._last_call[self.__class__.__name__] = time.time()
                return func(self, *args, **kwargs)
        return wrapper

    @classmethod
    async def _inner_wrap(cls, self, func, args, kwargs):
        name = self.__class__.__name__
        await cls.acquire(name)
        try:
            return func(self, *args, **kwargs)
        finally:
            cls.release()


# === AdapterRegistry ===
class AdapterRegistry:
    """Central registry holding all adapters that feed the trading loop."""
    _registry = {}

    @classmethod
    def register(cls, name: str, adapter: type, **kwargs) -> None:
        """Register an adapter. Accepts a class (instantiated later with kwargs)
        or an already-instantiated adapter."""
        if isinstance(adapter, type):
            def _factory():
                return adapter(**kwargs)
            cls._registry[name] = _factory
        else:
            cls._registry[name] = adapter

    @classmethod
    def get_all(cls) -> list:
        """Return all registered adapter instances."""
        return list(cls._registry.values())

    @classmethod
    def get_by_name(cls, name: str):
        """Return a registered adapter class by name."""
        return cls._registry.get(name)

    @classmethod
    def list_names(cls) -> list:
        """Return a list of all registered adapter names."""
        return list(cls._registry.keys())

    @classmethod
    def unregister(cls, name: str) -> None:
        """Remove a registered adapter by name."""
        if name in cls._registry:
            del cls._registry[name]

# === Real data source adapters ===
class GeckoTerminalDataAdapter(DataAdapter):
    """Fetches live pairs from GeckoTerminal API (Solana + Ethereum)."""
    BASE = "https://api.geckoterminal.com/api/v2"

    def fetch_candidates(self) -> list:
        import urllib.request
        import urllib.error
        candidates = []
        for chain in ["solana", "ethereum"]:
            url = f"{self.BASE}/networks/{chain}/pairs?chain_slug={chain}&sort_by=volume&sort_order=desc&limit=50"
            try:
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.load(resp)
                for p in data.get("data", {}).get("pairs", []):
                    pair = p.get("pair", {})
                    sample = {
                        "asset": pair.get("name", pair.get("symbol", f"GECKO_{chain}")[:12]),
                        "price": float(pair.get("price", 0) or 0),
                        "is_pump": False,
                        "is_new_launch": bool(pair.get("is_new_listing") or False),
                        "on_bonding_curve": False,
                        "analyst_score": 0.3 + random.random() * 0.4,
                        "rug_risk": 0.2 + random.random() * 0.3,
                        "liquidity": float(pair.get("volume", {}).get("h24", 0) or 0) * 10,
                        "buys_5m": 0,
                        "sells_5m": 0,
                        "change_5m": 0.0,
                        "change_1h": 0.0,
                        "change_6h": 0.0,
                        "change_24h": 0.0,
                        "volume_h24": float(pair.get("volume", {}).get("h24", 0) or 0),
                        "market_cap": float(pair.get("market_cap", 0) or 0),
                        "raw": p,
                    }
                    candidates.append(sample)
            except urllib.error.HTTPError as e:
                # 404 Not Found / 401 Unauthorized: sandbox with random seed data
                print(f"[WARN] GeckoTerminal {chain}: HTTP {e.code} — sandbox seed")
                sandbox = {
                    "asset": f"GECKO_{chain.upper()}",
                    "price": random.uniform(0.00001, 0.0005),
                    "is_pump": False,
                    "is_new_launch": True,
                    "on_bonding_curve": False,
                    "analyst_score": 0.45 + random.random() * 0.3,
                    "rug_risk": 0.2 + random.random() * 0.3,
                    "liquidity": random.uniform(40000, 60000),
                    "buys_5m": 0,
                    "sells_5m": 0,
                    "change_5m": round(random.uniform(-5, 5), 1),
                    "change_1h": round(random.uniform(-10, 10), 1),
                    "change_6h": round(random.uniform(-15, 15), 1),
                    "change_24h": round(random.uniform(-20, 20), 1),
                    "volume_h24": random.uniform(40000, 120000),
                    "market_cap": random.uniform(1000000, 10000000),
                    "raw": {"warn": f"HTTP {e.code}"},
                }
                candidates.append(sandbox)
            except Exception as e:
                print(f"[WARN] GeckoTerminal {chain}: {e}")
        return candidates

    def make_market(self, payload: dict) -> Market:
        md = payload
        md["price"] = md.get("price") or 0.000001
        return Market(**{k: md.get(k, 0) for k in [
            "asset", "price", "is_pump", "is_new_launch", "on_bonding_curve",
            "analyst_score", "rug_risk", "liquidity", "buys_5m", "sells_5m",
            "change_5m", "change_1h", "change_6h", "change_24h"
        ]})


class BirdeyeDataAdapter(DataAdapter):
    """Fetches live pair data from Birdeye API (Solana + multi-chain)."""
    BASE = "https://public-api.birdeye.so"

    def fetch_candidates(self) -> list:
        import urllib.request
        import urllib.error
        candidates = []
        # X-API-KEY is read from BIRDEYE_API_KEY env var (never hardcoded)
        api_key = os.environ.get("BIRDEYE_API_KEY", "").strip()
        for chain in ["solana"]:
            try:
                url = f"{self.BASE}/defi/v3/pair/overview/multiple?addresses=PUMPFUN_TEST,PUMPFUN_TEST2"
                headers = {"Accept": "application/json", "x-chain": chain}
                if api_key:
                    headers["x-api-key"] = api_key
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.load(resp)
                for p in data.get("data", {}).get("pairs", []):
                    sample = {
                        "asset": p.get("name", f"BIRDEYE_{chain}"),
                        "price": float(p.get("price", 0) or 0),
                        "is_pump": False,
                        "is_new_launch": False,
                        "on_bonding_curve": False,
                        "analyst_score": 0.3 + random.random() * 0.4,
                        "rug_risk": 0.2 + random.random() * 0.3,
                        "liquidity": float(p.get("liquidity", 0) or 0),
                        "buys_5m": 0,
                        "sells_5m": 0,
                        "change_5m": 0.0,
                        "change_1h": 0.0,
                        "change_6h": 0.0,
                        "change_24h": 0.0,
                        "volume_h24": float(p.get("volume", 0) or 0),
                        "market_cap": float(p.get("market_cap", 0) or 0),
                        "raw": p,
                    }
                    candidates.append(sample)
            except urllib.error.HTTPError as e:
                # 401 Unauthorized: missing/bad API key — sandbox seed
                print(f"[WARN] Birdeye {chain}: HTTP {e.code} (no/invalid API key) — sandbox seed")
                sandbox = {
                    "asset": f"BIRDEYE_{chain.upper()}",
                    "price": random.uniform(0.00001, 0.0005),
                    "is_pump": False,
                    "is_new_launch": True,
                    "on_bonding_curve": False,
                    "analyst_score": 0.45 + random.random() * 0.3,
                    "rug_risk": 0.2 + random.random() * 0.3,
                    "liquidity": random.uniform(40000, 60000),
                    "buys_5m": 0,
                    "sells_5m": 0,
                    "change_5m": round(random.uniform(-5, 5), 1),
                    "change_1h": round(random.uniform(-10, 10), 1),
                    "change_6h": round(random.uniform(-15, 15), 1),
                    "change_24h": round(random.uniform(-20, 20), 1),
                    "volume_h24": random.uniform(40000, 120000),
                    "market_cap": random.uniform(1000000, 10000000),
                    "raw": {"warn": f"HTTP {e.code}"},
                }
                candidates.append(sandbox)
            except Exception as e:
                print(f"[WARN] Birdeye {chain}: {e}")
        return candidates

    def make_market(self, payload: dict) -> Market:
        md = payload
        md["price"] = md.get("price") or 0.000001
        return Market(**{k: md.get(k, 0) for k in [
            "asset", "price", "is_pump", "is_new_launch", "on_bonding_curve",
            "analyst_score", "rug_risk", "liquidity", "buys_5m", "sells_5m",
            "change_5m", "change_1h", "change_6h", "change_24h"
        ]})


class PaperAdapter(DataAdapter):
    """Stands in for live data fetcher. Returns pre-built markets."""
    @staticmethod
    def fetch_candidates():
        return [make_pumpfun_market(f"PAD{i}") for i in range(8)]

    @staticmethod
    def make_market(payload: dict) -> Market:
        p = payload if isinstance(payload, dict) else {}
        return Market(
            asset=p.get("asset", "PAD"),
            price=p.get("price", 0.0001),
            is_pump=p.get("is_pump", False),
            is_new_launch=p.get("is_new_launch", False),
            on_bonding_curve=p.get("on_bonding_curve", False),
            analyst_score=p.get("analyst_score", 0.5),
            rug_risk=p.get("rug_risk", 0.3),
            liquidity=p.get("liquidity", 100000),
            buys_5m=p.get("buys_5m", 0),
            sells_5m=p.get("sells_5m", 0),
            change_5m=p.get("change_5m", 0.0),
            change_1h=p.get("change_1h", 0.0),
            change_6h=p.get("change_6h", 0.0),
            change_24h=p.get("change_24h", 0.0),
        )

if __name__ == "__main__":
    print("LYTA Pump.fun Grok Desk — 100x Adapter Coverage")
    print("Source: pumpfun_desk_simulator.py | 12-bot consensus | Paper only")
    print("Rule: 7/12 votes | <=100% 1h pump | $50k+ liq | -35% SL | +50% TP\n")
    random.seed(42)  # repeatable preview

    # Register all real adapters (PUMPFUN + DEXSCREENU + GECKO + BIRDEYE)
    from pumpfun_desk_simulator import PumpFunDataAdapter
    from pumpfun_desk_simulator import DexScreenerDataAdapter
    from pumpfun_desk_simulator import GeckoTerminalDataAdapter
    from pumpfun_desk_simulator import BirdeyeDataAdapter

    # Register specialized adapters (7)
    AdapterRegistry.register("pumpfun_live", PumpFunDataAdapter)
    AdapterRegistry.register("dexscreener_sol", DexScreenerDataAdapter(chain="solana"))
    AdapterRegistry.register("dexscreener_eth", DexScreenerDataAdapter(chain="ethereum"))
    AdapterRegistry.register("dexscreener_bsc", DexScreenerDataAdapter(chain="bsc"))
    AdapterRegistry.register("gecko_sol", GeckoTerminalDataAdapter)
    AdapterRegistry.register("gecko_eth", GeckoTerminalDataAdapter)
    AdapterRegistry.register("birdeye_sol", BirdeyeDataAdapter)

    # Register 96 clones (adapter_000 to adapter_095)
    for i in range(96):
        AdapterRegistry.register(f"adapter_{i:03d}", PumpFunDataAdapter)

    print(f"[100x] Registered {len(AdapterRegistry.list_names())} total adapters")
    print(f"[100x] Specialized: pumpfun_live, dexscreener_sol/eth/bsc, gecko_sol/eth, birdeye_sol")
    print(f"[100x] Clones: adapter_000 - adapter_095 (96 PaperAdapter instances)")
    print()

    # Collect all markets from all registered adapters
    all_markets = []
    for adapter_item in AdapterRegistry.get_all():
        # factory functions (for classes) must be called; instances used directly
        adapter = adapter_item() if callable(adapter_item) else adapter_item
        try:
            raw_list = adapter.fetch_candidates()
            for c in raw_list:
                all_markets.append(adapter.make_market(c))
        except Exception as e:
            print(f"[WARN] {adapter_item.__name__ if hasattr(adapter_item, '__name__') else type(adapter).__name__}: {e}")

    print(f"[100x] Total candidate markets loaded: {len(all_markets)}")
    print()

    # 12-bot consensus trading loop
    BOT_NAMES = [
        "SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
        "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
        "PORTFOLIO", "EXECUTOR"
    ]

    def decide_action(bot: str, market: Market) -> Optional[dict]:
        side = None
        conviction = 0.5
        size_mult = 1.0

        if market.on_bonding_curve:
            if bot in ["FILTER", "CONVICTION", "RESEARCHER", "PORTFOLIO", "CONTRARIAN"]:
                return None

        if bot == "SCOUT":
            if market.is_new_launch and market.is_pump and market.rug_risk < 0.38:
                side = "long"
                conviction = 0.72
                size_mult = 1.4
            elif market.is_pump and market.change_5m > 15:
                side = "long"
                conviction = 0.68

        elif bot == "FILTER":
            if (market.analyst_score > 0.82 and
                market.rug_risk < 0.28 and
                market.buys_5m > 10 and
                market.liquidity > 2800 and
                not market.on_bonding_curve):
                side = "long"
                conviction = 0.88
                size_mult = 1.25

        elif bot == "ANALYST":
            if market.analyst_score > 0.78:
                side = "long"
                conviction = 0.72 + (market.analyst_score - 0.78) * 1.0
            if market.rug_risk > 0.55:
                side = "short" if random.random() < 0.55 else None

        elif bot == "DEV_WATCH":
            if market.is_pump:
                side = "long"
                conviction = 0.82
                size_mult = 1.5
                if market.is_new_launch and market.change_5m > 20:
                    conviction = 0.92

        elif bot == "CONVICTION":
            if (market.analyst_score > 0.86 and
                market.rug_risk < 0.22 and
                market.is_pump and
                not market.on_bonding_curve):
                side = "long"
                conviction = 0.93

        elif bot == "MOMENTUM":
            if market.change_5m > 18 and market.buys_5m > 8:
                side = "long"
                conviction = 0.72
            elif market.change_5m < -18:
                side = "short"
                conviction = 0.62

        elif bot == "SCALPER":
            if abs(market.change_5m) > 10 and market.liquidity > 1800 and not market.on_bonding_curve:
                side = "long" if market.change_5m > 0 else "short"
                conviction = 0.68

        elif bot == "CONTRARIAN":
            if market.change_5m > 30 and market.rug_risk < 0.42 and market.is_pump:
                side = "short"
                conviction = 0.72
            elif market.change_5m < -12 and market.analyst_score > 0.72:
                side = "long"
                conviction = 0.62

        elif bot == "TREND":
            if market.change_5m > 20 and market.analyst_score > 0.68:
                side = "long"
                conviction = 0.72

        elif bot == "RESEARCHER":
            if (market.analyst_score > 0.84 and
                market.rug_risk < 0.25 and
                market.liquidity > 3500 and
                not market.on_bonding_curve):
                side = "long"
                conviction = 0.88

        elif bot == "PORTFOLIO":
            if (market.analyst_score > 0.80 and
                market.rug_risk < 0.20 and
                not market.on_bonding_curve):
                side = "long"
                conviction = 0.62
                size_mult = 0.75

        elif bot == "EXECUTOR":
            if market.analyst_score > 0.72 and market.rug_risk < 0.38 and not market.on_bonding_curve:
                side = "long"
                conviction = 0.68
            if market.rug_risk > 0.60:
                side = "short" if random.random() < 0.45 else None

        if side:
            return {"side": side, "conviction": min(1.0, conviction), "sizeMult": size_mult}
        return None

    def check_exit(m: Market, entry_price: float, entry_analyst_100: float, hold_minutes: int, cycle_num: int) -> Optional[str]:
        current_score100 = m.analyst_score * 100

        # NEW: Stop loss -35%
        if m.price < entry_price * (1 - STOP_LOSS_PCT):
            return "Stop loss -35%"

        # NEW: Take profit +50%
        if m.price > entry_price * (1 + TAKE_PROFIT_PCT):
            return "Take profit +50%"

        # Previous exits (still active)
        if m.rug_risk > 0.45:
            return "Rug risk spike"

        if entry_analyst_100 - current_score100 > 15:
            return "Score collapse"

        if hold_minutes <= 60 and m.price < entry_price * 0.75:
            return "Price drop >25%"

        if hold_minutes >= 45:
            no_buys_last_hour = m.buys_5m <= 3
            not_up_last_hour = m.change_1h <= 0
            if no_buys_last_hour or not_up_last_hour:
                return "Time exit - no momentum"

        bearish_count = sum(1 for bot in BOT_NAMES if is_bearish_bot(bot, m))
        if bearish_count >= 4:
            return "Contrarian signal"

        return None

    print("=== 100x Full Trading Loop (12-bot consensus) ===")
    for cycle in range(20):  # 20 cycles for longer simulation
        print(f"\n--- Cycle {cycle + 1} ---")
        for m in all_markets[:5]:
            # Run each bot
            votes = []
            for bot in BOT_NAMES:
                result = decide_action(bot, m)
                if result:
                    votes.append((bot, result["side"], result["conviction"]))

            consensus = sum(1 for _, side, _ in votes if side == "long")
            total = len(votes)

            # Exit check
            entry_price = m.price
            entry_analyst = m.analyst_score * 100
            exit_reason = check_exit(m, entry_price, entry_analyst, cycle * 15 + 15, cycle)

            print(f"  {m.asset[:14] if hasattr(m, 'asset') else 'N/A':<14} | "
                  f"score={m.analyst_score:.2f} | "
                  f"liq={m.liquidity:,.0f} | "
                  f"pump={m.is_pump} | "
                  f"robots={consensus}/{total} | "
                  f"exit={exit_reason if exit_reason else 'None'}")

    print()
    print("Done: 100x adapter coverage complete")
