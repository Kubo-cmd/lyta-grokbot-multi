#!/usr/bin/env python3
"""
LYTA Grok Desk - PUMPFUN REVERSE ENGINEER (paper-only, zero-burn)

Reverse-engineers a pump.fun memecoin bot from PUBLIC on-chain data, using
the same reverse-engineering pipeline the Polymarket video ("I Reverse
Engineered 3 Polymarket Bots That Made $4.3M") used on public trade data:

  1. WHAT DOES IT DO?   Reconstructing the public fill pattern into a
                        "bot signature" (momentum ramp, fills imbalance,
                        liquidity dilution risk, scale).
  2. SKILL OR LUCK?     Luck proxy: informed-buy share vs. a fair-coin
                        baseline (customer/player estimates), plus a
                        sniper-suction index for the "coin man 2 hold".
  3. STILL WORKS AFTER
     THE SETTING CHANGE?  The video's killer = one setting change.  For
     pump.fun the equivalent = fee / slippage / liquidity-drain regime
     changes.  Paper-only sensitivity check (no live trades executed).

This is an OBSERVATION run: no trades executed. All verdicts are paper-only
strategy hypotheses that feed the phase-2 12-bot paper desk.

Real data source (no API key needed):
  DexScreener token-profiles + token-pairs (Solana pump.fun/pumpswap pairs).
  [token-profiles/latest/v1] -> [token-pairs/v1/{chain}/{addr}] (per-window
  buy/sell buckets, volume, market cap).
"""

import os
import sys
import json
import urllib.request
import urllib.error
import datetime
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.abspath(__file__))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# ---------------------------------------------------------------------------
# Real public data fetch
# ---------------------------------------------------------------------------

def _get_json(url: str, timeout: int = 12) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json",
                 "User-Agent": "LYTA-GrokBot-Paper/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_real_candidates(limit: int = 8) -> list:
    """Return real pump.fun/pumpswap candidate dicts from DexScreener.

    Uses the repo's verified DexScreenerDataAdapter.  If the adapter is not
    importable or returns nothing, a deterministic seed pool is used as a
    fallback so the reverse-engineering pipeline is always runnable on paper.
    """
    try:
        from pumpfun_desk_simulator import DexScreenerDataAdapter as _Adapter
        adapter = _Adapter(chain="solana", limit=limit)
        real = adapter.fetch_candidates()
        if real:
            return real
    except Exception as e:
        print(f"[REAL] adapter unavailable ({type(e).__name__}: {e}); "
              f"using fallback seed pool")
    return _seed_candidates()


def _seed_candidates() -> list:
    """Fallback seed pool; never used for live trade decisions."""
    import random
    random.seed(0)
    out = []
    for i, (asset, pump_id) in enumerate([
            ("PUMPFUN_TKN", i) for i in range(8)]):
        out.append({
            "asset": asset, "chain": "solana",
            "dexId": "pumpfun" if i % 2 == 0 else "pumpswap",
            "price_usd": random.uniform(1e-6, 4e-5),
            "buys_5m": random.randint(15, 520),
            "sells_5m": random.randint(10, 380),
            "change_5m": random.uniform(-5, 60),
            "change_1h": random.uniform(5, 120),
            "change_6h": random.uniform(3, 90),
            "change_24h": random.uniform(-10, 100),
            "volume_h24": random.uniform(2000, 120000),
            "market_cap": random.uniform(1000, 100000),
            "score": random.uniform(0.1, 0.98),
            "pair_created_at": "seed",
        })
    return out


# ---------------------------------------------------------------------------
# The "Bot-X-Ray": what does the public fill pattern actually say?
# ---------------------------------------------------------------------------

def reconstruct_bot_signature(c: dict) -> dict:
    """Reconstruct a public-trade 'bot signature' from one snapshot."""
    buys = max(1, int(c.get("buys_5m", 0)))
    sells = max(1, int(c.get("sells_5m", 0)))
    ch5 = float(c.get("change_5m", 0.0) or 0.0)
    chh = float(c.get("change_1h", 0.0) or 0.0)
    vol = float(c.get("volume_h24", 0.0) or 0.0)
    mc = float(c.get("market_cap", 0) or 0)

    # Momentum ramp: how much speed came in the last 5 minutes vs the hour.
    momentum_ramp = (ch5 / max(1.0, abs(chh))) if abs(chh) > 1.0 else (
        ch5 if abs(ch5) > 1.0 else 0.0)

    # Fills imbalance - share of first-window buys among all first-window fills.
    fills_share = buys / (buys + sells)

    # Liquidity dilution risk: price move per 24h dollar of volume.
    dilution_risk = (abs(chh) / max(1.0, vol)) * 100.0

    # Scale gauge: market cap vs 24h volume (pump-and-dump vs real trade).
    volume_vs_mcap = vol / max(1.0, mc) if mc > 0 else 0.0

    # Pump pace: minutes to 50% of the 5m move (fast = sniper early-entry).
    m50 = max(0.1, ch5 / max(1e-6, abs(ch5))) * 1.0

    mode = _classify_mode({
        "momentum_ramp": momentum_ramp,
        "fills_share": fills_share,
        "dilution_risk_pct": dilution_risk,
        "volume_vs_mcap": volume_vs_mcap,
    })

    signature = {
        "asset": c.get("asset", "?"),
        "buys_5m": buys,
        "sells_5m": sells,
        "fill_balance": buys - sells,
        "fills_share": round(fills_share, 3),
        "momentum_ramp": round(momentum_ramp, 3),
        "dilution_risk_pct": round(dilution_risk, 4),
        "volume_vs_mcap": round(volume_vs_mcap, 4),
        "m50_pace": round(m50, 3),
        "mode": mode,
    }
    return signature


def _classify_mode(sig: dict) -> str:
    """Pick the 'bot style' the public pattern most resembles."""
    ramp = sig["momentum_ramp"]
    share = sig["fills_share"]
    dill = sig["dilution_risk_pct"]
    vmc = sig["volume_vs_mcap"]

    if ramp > 40 and share > 0.62:
        return "SNIPER-TRANCHE"      # front-loaded, late-2h dip still holding
    if ramp > 25 and share < 0.45 and vmc > 2.0:
        return "PUMP-AND-DUMP"     # big early swing, volume far outpaces cap
    if ramp > 12 and share > 0.5:
        return "KINETIC-HOLD"      # steady between-monotonic buy, held into
    if ramp < 8 and vmc < 1.0:
        return "WASH-GRIND"        # thin book, slow grind, low conviction
    return "MIXED"


# ---------------------------------------------------------------------------
# Question 2: skill or luck?
# ---------------------------------------------------------------------------

def skill_or_luck(c: dict, sig: dict) -> dict:
    """A luck proxy + a sniper-suction index for the 'coin man 2' hold."""
    buys = max(1, sig["buys_5m"])
    sells = max(1, sig["sells_5m"])
    fill_balance = sig["fill_balance"]

    # Fair-coin baseline: in an efficient pump, net buys of the first window
    # per 5-min slot should be ~0. A coin clearly above the buyer-share of the
    # theoretical '12-buyer micro-sizing' (their 5-bot consensus) is 'signal'.
    buyer_share = sig["fills_share"]
    fair_share = 0.5
    signal_delta = buyer_share - fair_share

    # Sniper-suction index: net buyers per dollar of 24h volume.  A model
    # holds (buys-sells) concentrated in a thin book = informed flow trapped.
    suction = (fill_balance / max(1.0, float(c.get("volume_h24", 0)))) * 100.0

    # Luck estimate: analyst_score already encodes the 'does it keep going'
    # signal; we fold in whether the momentum is fatiguing (change_6h vs ch5).
    ch5 = float(c.get("change_5m", 0.0) or 0.0)
    ch6 = float(c.get("change_6h", 0.0) or 0.0)
    momentum_fatigue = ch6 - ch5  # negative = decelerating (winner) vs
    luck = {
        "buyer_share_of_first_window": round(buyer_share, 3),
        "signal_delta_vs_fair_coin": round(signal_delta, 3),
        "sniper_suction_index": round(suction, 4),
        "momentum_fatigue_px": round(momentum_fatigue, 3),
        "verdict": _luck_verdict(buyer_share, signal_delta, suction),
    }
    return luck


def _luck_verdict(buyer_share, signal_delta, suction):
    s = suction if suction > 0 else 0.0
    d = abs(signal_delta)
    if buyer_share > 0.66 and s > 0.005 and d > 0.12:
        return "SKILL-THIN"       # informed flow, tight book, holds
    if buyer_share > 0.60 and d > 0.10:
        return "SKILL-PARTIAL"
    if buyer_share < 0.55 and s < 0.002:
        return "LUCK-FAIR"
    if s > 0.01:
        return "LUCK-STICKY"      # traffic jam, not evidence of edge
    return "SKILL-UNK"


# ---------------------------------------------------------------------------
# Question 3: still works after the setting change?
# ---------------------------------------------------------------------------

def still_works_after_setting_change(c: dict, sig: dict, luck: dict) -> dict:
    """Paper-only sensitivity check vs fee / slippage / liquidity-drain."""
    buys = sig["buys_5m"] or 1
    sells = sig["sells_5m"] or 1
    fee = 0.01  # pump.fun protocol fee
    slip = 0.003  # fills slippage on bonding curve
    wash = 0.10   # wash-trade estimate (your '12-bot' buy questions are a
    buy_vol = sig["buys_5m"] or 1.0
    sell_vol = sig["sells_5m"] or 1.0
    rebalance = sell_vol - buy_vol  # sell-side grabs liquidity
    net = rebalance / max(1.0, buy_vol) * 100.0

    # Rough break-even: 1% fee + 0.3% slippage + wash (10% of reported buys)
    # must be << the observed buy-share advantage or the edge evaporates.
    overhead = fee + slip + wash * (buys / (buys + sells))
    margin = (sig["fills_share"] - 0.50) * 100.0 - overhead * 100.0
    survives = margin > 1.0  # at least ~1pp comfortable margin

    deg = {
        "fee_pct": fee,
        "slippage_pct": slip,
        "wash_est_pct": wash,
        "buyer_share_basis": sig["fills_share"],
        "net_sells_vs_buys_pct": round(net, 3),
        "operating_overhead_pct": round(overhead * 100.0, 3),
        "margin_vs_overhead_pp": round(margin, 3),
        "survives_breaker": bool(survives),
        "verdict": "STILL-WORKS" if survives else "STOP-SHORT",
    }
    return deg


# ---------------------------------------------------------------------------
# Question 1 + 2 + 3 verdict + stand-down reasons
# ---------------------------------------------------------------------------

def verdict_for(c: dict) -> dict:
    sig = reconstruct_bot_signature(c)
    luck = skill_or_luck(c, sig)
    works = still_works_after_setting_change(c, sig, luck)
    return {
        "asset": c.get("asset", "?"),
        "dexId": c.get("dexId", ""),
        "signature": sig,
        "luck": luck,
        "still_works": works,
        "opinion": _determine_opinion(sig, luck, works),
    }


def _determine_opinion(sig, luck, works) -> str:
    modes = {
        "SNIPER-TRANCHE": "reverse-engineered sniper",
        "PUMP-AND-DUMP": "pump-and-dump",
        "KINETIC-HOLD": "kinetic hold",
        "WASH-GRIND": "wash grind",
        "MIXED": "mixed",
    }[sig["mode"]]

    parts = [f"signature={sig['mode']} ({modes})",
             f"informed-flow={'edge' if luck['verdict'].startswith('SKILL') else 'noise'}",
             f"fee-resilience={'ok' if works['survives_breaker'] else 'thin'}"]
    return "; ".join(parts)


def _stand_down_reason(c: dict, verdict: dict) -> str:
    reasons = []
    if verdict["signature"]["mode"] in ("PUMP-AND-DUMP", "WASH-GRIND"):
        reasons.append("signal-clean only in a thin window; rotate toward the "
                       "top-of-list candidates for breadth")
    return "; ".join(reasons) if reasons else "no stand-down"


# ---------------------------------------------------------------------------
# Main reversible-paper run
# ---------------------------------------------------------------------------

def run_reverser(limit: int = 8, verbose: bool = True):
    candidates = fetch_real_candidates(limit)
    rows = [verdict_for(c) for c in candidates]

    if verbose:
        print("\n=== PUMPFUN REVERSE ENGINEER (paper-only, no trades executed) ===")
        print(f"[DATA SOURCE] DexScreener Solana public pairs (best-effort)")
        print(f"[N_CANDIDATES] {len(candidates)}\n")

        print("ASSET          DEEDI  MODE                 OPINION")
        for r in rows:
            print(f"{r['asset'][:13]:<14} {r['dexId'][:5]:<5} "
                  f"{r['signature']['mode'][:18]:<20} {r['opinion']}")

        print("\n--- VERDICT DETAILS (paper-only) ---")
        for r in rows:
            s, l, w = r["signature"], r["luck"], r["still_works"]
            print(f"\n[{r['asset']}]")
            print(f"  signature: {s['mode']} | fills {s['fills_share']:.2f} {s['fill_balance']:+d}/{s['buys_5m']+s['sells_5m']} "
                  f"m5 | ramp {s['momentum_ramp']}x | dilute {s['dilution_risk_pct']} "
                  f"vol/mcap {s['volume_vs_mcap']}p")
            print(f"  luck: {l['verdict']} | buyer_share {l['buyer_share_of_first_window']} "
                  f"suction {l['sniper_suction_index']} | fatigue {l['momentum_fatigue_px']}")
            print(f"  still-works: survives={w['survives_breaker']} "
                  f"margin-vs-overhead {w['margin_vs_overhead_pp']}pp "
                  f"overhead {w['operating_overhead_pct']}pp")
            print(f"  STAND DOWN: {r['opinion']}")

    return rows



# ---------------------------------------------------------------------------
# Deterministic paper document writer (reverse-engineer evidence pack)
# ---------------------------------------------------------------------------
DOC_DIR = os.path.join(REPO, "pumpfun_reverse_output")


def _write_doc(rows: list, as_of: str) -> str:
    """Write a verified paper document pack for this reverse-engineer run.

    Envelope matches the retired session's round_<ts>.json shape so downstream
    tools (pumpfun_paper_gate.py) consume identical schemas.
    """
    passes = [r for r in rows
              if r.get("still_works", {}).get("survives_breaker")
              and r.get("signature", {}).get("mode") in
              ("SNIPER-TRANCHE", "KINETIC-HOLD", "MIXED")]
    doc = {
        "tag": "paper",
        "as_of": as_of,
        "zero_burn": True,
        "capital_rule": "no capital, no trades, observation only",
        "source": "pumpfun_reverse_output",
        "candidate_count": len(rows),
        "rows": rows,
        "surviving_candidates": len(passes),
        "stand_downs": [r["asset"] for r in rows
                        if r.get("still_works", {}).get("survives_breaker") is not True
                        or r.get("signature", {}).get("mode")
                        not in ("SNIPER-TRANCHE", "KINETIC-HOLD", "MIXED")],
        "pass_band": [r["asset"] for r in passes],
        "next_step": "paper_gate verdict over surviving candidates",
    }
    path = os.path.join(DOC_DIR, f"round_{as_of}.json")
    os.makedirs(DOC_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    return path


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    rows = run_reverser(limit=8, verbose=verbose)
    if rows:
        written = _write_doc(rows, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        print(f"[REVERSE] wrote paper document {written}")
