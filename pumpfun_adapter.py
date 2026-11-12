"""
LYTA Pump.fun Grok Desk - PumpFunDataAdapter
Wires pump.fun /v1/stats candidate data into the 12-bot voting engine.
"""
import random
from typing import Dict, List

# Fallback Market class if main simulator is not available
class _Market:
    pass

def _get_market_class():
    try:
        from pumpfun_desk_simulator import Market
        return Market
    except ImportError:
        return _Market

# BOT_NAMES is imported at runtime via importlib; set here as fallback
BOT_NAMES = ["SCOUT", "FILTER", "ANALYST", "DEV_WATCH", "CONVICTION",
             "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND", "RESEARCHER",
             "PORTFOLIO", "EXECUTOR"]


class PumpFunDataAdapter:
    """Normalizes pump.fun payload into the desk's internal Market schema."""

    PUMPFUN_FIELDS = {
        "progress_pct": "change_5m",
        "has_metadata": "metadata_ready",
        "unique_buyers": "buys_5m",
        "buys": "buys_total",
        "liquidity": "liquidity",
        "liquidity_usd": "liquidity_usd",
        "rug_risk": "rug_risk",
        "analyst_score": "analyst_score",
        "token_address": "pair",
        "name": "asset",
        "symbol": "asset",
    }

    @classmethod
    def adapt(cls, payload: dict) -> dict:
        """Take a pump.fun payload and return a dict matching Market fields."""
        cand = payload.get("candidate", payload)
        stats = payload.get("stats", {})

        analyst = float(payload.get("analyst_score",
                     payload.get("score", stats.get("score", 0.72))))
        score100 = round(analyst * 100, 1) if isinstance(analyst, (int, float)) else 72.0

        return {
            "asset": str(cand.get("name", cand.get("symbol", "PUMPFUN_TKN"))),
            "pair": str(cand.get("token_address", cand.get("pair", ""))),
            "price": float(payload.get("price", cand.get("price", 0.000001))),
            "is_pump": bool(payload.get("is_pump", cand.get("is_pump", False))),
            "is_new_launch": bool(payload.get("is_new_launch", cand.get("is_new_launch", True))),
            "on_bonding_curve": bool(payload.get("on_bonding_curve", cand.get("on_bonding_curve", False))),
            "analyst_score": round(analyst, 3),
            "analyst_score_100": score100,
            "rug_risk": round(float(payload.get("rug_risk", cand.get("rug_risk", 0.25))), 3),
            "liquidity": round(float(payload.get("liquidity", cand.get("liquidity", 5000))), 0),
            "liquidity_usd": round(float(payload.get("liquidity_usd", cand.get("liquidity_usd", 5000))), 0),
            "buys_5m": int(payload.get("buys_5m", cand.get("buys", 10))),
            "sells_5m": int(payload.get("sells_5m", cand.get("sells", 2))),
            "buys_total": int(payload.get("buys", cand.get("buys", 10))),
            "change_5m": round(float(payload.get("progress_pct", cand.get("progress_pct", 0))), 1),
            "change_1h": round(float(payload.get("change_1h", cand.get("change_1h", 0))), 1),
            "change_6h": round(float(payload.get("change_6h", cand.get("change_6h", 0))), 1),
            "change_24h": round(float(payload.get("change_24h", cand.get("change_24h", 0))), 1),
            "unique_buyers": int(payload.get("unique_buyers", cand.get("unique_buyers", 10))),
            "has_metadata": bool(payload.get("has_metadata", cand.get("has_metadata", False))),
            "raw": payload,
        }

    @classmethod
    def make_market(cls, payload: dict) -> "Market":
        """Convert pump.fun payload into a Market object."""
        md = cls.adapt(payload)
        md["price"] = md["price"] if md["price"] > 0 else random.uniform(0.000008, 0.0006)
        Market = _get_market_class()
        return Market(**{k: md[k] for k in [
            "asset", "price", "is_pump", "is_new_launch", "on_bonding_curve",
            "analyst_score", "rug_risk", "liquidity", "buys_5m", "sells_5m",
            "change_5m", "change_1h", "change_6h", "change_24h"
        ]})

    @classmethod
    def extract_candidates(cls, list_payload: dict) -> list:
        """Extract candidate list from pump.fun /categories/pumps responses."""
        raw = list_payload.get("pumps", list_payload.get("candidates", []))
        out = []
        for c in raw:
            try:
                out.append(cls.adapt({"candidate": c, **list_payload}))
            except Exception:
                continue
        return out
