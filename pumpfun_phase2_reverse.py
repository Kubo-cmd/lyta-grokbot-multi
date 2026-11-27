#!/usr/bin/env python3
"""
Phase 2 — pump.fun paper-only reverse-engineer run.

Wires the verified 3-question "Bot-X-Ray" (pumpfun_reverse_engineer.py)
into the paper desk so every phase-2 round:
  1. pulls real live pump.fun/pumpswap candidates (DexScreener public pairs),
  2. scores them with the 3-question framework (mode / luck / still-works),
  3. prints a STAND DOWN for any lot that fails, and reports the top-3
     survivors that still pass — before any buy question is ever asked.

Zero-burn, observation-only. NO capital, NO wallet, NO trade execution.

Run:
    python3 pumpfun_phase2_reverse.py          # verbose, prints report
    python3 pumpfun_phase2_reverse.py --json   # write results JSON
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ── Load the verified reverse engineer (paper-only, no-trade) ─────
import pumpfun_reverse_engineer as _rea

# Shop parameters (zero-burn paper desk)
MIN_CAPITAL = 2.0
MAX_CAPITAL = 6.0
CONSENSUS_MIN_BOTS = 5
PASS_BAND_LOW = 0.35
PASS_BAND_HIGH = 0.55


def run_round(tag: str = "paper") -> dict:
    """Execute one phase-2 paper round against live pump.fun candidates."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = {
        "tag": tag,
        "as_of": ts,
        "zero_burn": "observation only, no trades",
        "capital_rule": f"paper only, {MIN_CAPITAL}-{MAX_CAPITAL} micro-sizing",
        "source": "DexScreener public Solana pairs (via pumpfun_reverse_engineer.py)",
    }

    print("\n" + "=" * 66)
    print(" PHASE 2 PUMP.FUN PAPER ROUND — ZERO-BURN, OBSERVATION ONLY")
    print("=" * 66)
    rows = _rea.run_reverser(limit=12, verbose=True)

    # Build the structured payload (same dicts the simulator already emits).
    payload = []
    for r in rows:
        p = dict(r)
        p["round_tag"] = tag
        p["micro_budget_ok"] = MIN_CAPITAL <= p.get("price_usd", 0) <= MAX_CAPITAL
        p["paper_guard"] = "stand_down" if p.get("opinion") == "stand_down" else "watch"
        # luck is a dict {verdict, buyer_share..., ...} in the REA rows.
        _l = p.get("luck")
        p["luck_label"] = _l.get("verdict", "?") if isinstance(_l, dict) else (_l or "?")
        payload.append(p)
        print(f"  [{p['asset']:>10}] {p['signature']['mode'][:28]:<28} "
              f"{p['luck_label'][:14]:<14} still={p['still_works']!s:<5} "
              f"{p['opinion']:<12} micro={p['micro_budget_ok']}")

    summary["candidate_count"] = len(payload)
    summary["rows"] = payload

    # Core 3-question verdicts keyed by asset for the desk's aggregation step.
    # A "watch" lot must still-works (fee+slip+slippage net positive) AND not
    # be a scripted play (PUMP-AND-DUMP / WASH-GRIND).  Everything else is a
    # stand-down lot.
    _SHIP = {"SNIPER-TRANCHE", "KINETIC-HOLD", "MIXED"}
    winners = [p for p in payload
               if p.get("still_works", {}).get("survives_breaker")
               and p.get("signature", {}).get("mode") in _SHIP]
    summary["surviving_candidates"] = winners
    summary["stand_downs"] = [p for p in payload if p not in winners]
    summary["pass_band"] = {
        "low": PASS_BAND_LOW,
        "high": PASS_BAND_HIGH,
        "consensus_min_bots": CONSENSUS_MIN_BOTS,
    }

    # For the paper desk: this round is INFORMATIONAL until the aggregation
    # gate (>= CONSENSUS_MIN_BOTS bots, |score| in pass_band) confirms.
    summary["next_step"] = (
        "desk: aggregate votes, apply 5+ bot consensus gate, then stand down "
        "or advance. NO trade executed."
    )

    # Write JSON for the paper-run loop to consume.
    out_path = os.path.join(REPO_ROOT, "pumpfun_reverse_output", f"round_{ts}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print("")
    print(f"[VERIFY] results written -> {out_path}")
    print(f"[VERIFY] candidates={summary['candidate_count']} "
          f"surviving={len(winners)} "
          f"zero_burn={summary['zero_burn']}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true",
                    help="write round JSON and exit (no pretty print)")
    ap.add_argument("--limit", type=int, default=12,
                    help="candidate pool size")
    args = ap.parse_args()

    if args.json:
        run_round().update({"runner": "json-only"})
        sys.exit(0)

    run_round()
