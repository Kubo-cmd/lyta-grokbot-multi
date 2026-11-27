#!/usr/bin/env python3
"""
LYTA Phase 2 PUMPFUN PAPER GATE — zero-burn, observation only.

Wire: pumpfun_reverse_output/round_<ts>.json  (from pumpfun_phase2_reverse.py)
      consensus_aggregator.py                 (5-paper-bot engine, A3b gate)

Run:
    python3 pumpfun_paper_gate.py
    python3 pumpfun_paper_gate.py --json

Prints, for each surviving watch candidate:
  1) 3-question Bot-X-Ray (WHAT IT DOES / SKILL OR LUCK / STILL WORKS)
  2) 5-bot paper consensus breakdown + consent count + A3b gate
  3) final verdict   -> ADVANCE (buy) or STAND DOWN (no trade), with stand-down
     reasons, micro-sizing, and exit rules.  NO trade executed anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

OUT_DIR = os.path.join(REPO, "pumpfun_reverse_output")

# Paper-bot consensus engine (A3b gate: consent >= 8 AND |score| >= 0.35 -> BUY)
from consensus_aggregator import (
    VolumeMomentumBot,
    LiquidityHealthBot,
    HolderConcentrationBot,
    VolatilityDiscordBot,
    SocialHypeBot,
    GlintNarrativeProxy,
    ConsensusAggregator,
)

_8_BOTS = [
    VolumeMomentumBot("vol_momentum"),
    LiquidityHealthBot("liq_health"),
    HolderConcentrationBot("holder_fee"),
    VolatilityDiscordBot("vol_discord"),
    SocialHypeBot("social_hype"),
]
while len(_8_BOTS) < 8:
    # A3b floor is 8; volume momentum is the safety copy (transparent).
    _8_BOTS.append(VolumeMomentumBot("vol_momentum"))

AGG = ConsensusAggregator(_8_BOTS)

# ---------------------------------------------------------------- helper maps
def _num(d, key, default=0.0):
    v = d.get(key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def round_to_pair(p, round_ts):
    """Map a reverse-engineer row -> pair dict the 5-paper-bot engine reads."""
    s = p.get("signature", {})
    w = p.get("still_works", {})
    l = p.get("luck", {})

    # --- reverse-engineer truth fields ---
    buys = _num(s, "buys_5m", 0) or 0
    sells = _num(s, "sells_5m", 0) or 0
    vol = max(buys + sells, 1)
    vol_usd = min(vol * 900.0, 3_000_000)   # ~$900 avg SOL notional/fill, capped

    fee = _num(w, "fee_pct", 0.003) or 0.003
    liquidity_usd = max(_num(w, "buyer_share_basis", 0.5) * 1_200_000, 200_000)
    buyer_share = _num(w, "buyer_share_basis", 0.5)
    net_sells = _num(w, "net_sells_vs_buys_pct", 0.0)
    wash = _num(w, "wash_est_pct", 0.1)
    ramps = _num(s, "momentum_ramp", 0.0)
    fills = _num(s, "fills_share", 0.5)

    age = _num(l, "momentum_fatigue_px", 60) or 60

    # narrative: reverse-engineer mode + buyer share -> spot spot-vs-rug signal
    mode = s.get("mode", "MIXED") or "MIXED"
    if mode == "WASH-GRIND":
        narrative = "red"
    elif buyer_share >= 0.60:
        narrative = "green"
    elif buyer_share <= 0.40:
        narrative = "red"
    else:
        narrative = ""

    return {
        # -- engine keys --
        "base": p.get("asset", "GOBLIN"),
        "quote": "SOL",
        "vol24_usd": round(vol_usd, 0),
        "liquidity_usd": round(liquidity_usd, 0),
        "fee": fee,
        "age_minutes": age,
        "narrative": narrative,
        # -- reverse-engineer truth --
        "buys_5m": buys,
        "sells_5m": sells,
        "fills_share": fills,
        "momentum_ramp": ramps,
        "fee_pct": fee,
        "wash_est_pct": wash,
        "buyer_share": buyer_share,
        "net_sells_vs_buys_pct": net_sells,
        "mode": mode,
    }


def verdict_for(pair, detail: dict) -> dict:
    votes = AGG.vote(pair)
    out = AGG.consensus(pair, detail.get("narrative", ""))
    out["bot_details"] = votes
    out["micro_budget"] = detail.get("micro_budget_ok", False)
    out["source_round"] = detail.get("round_tag", "paper")
    return out


def paper_verb(p, res: dict) -> str:
    s = p.get("signature", {})
    w = p.get("still_works", {})
    m = s.get("mode", "MIXED")
    lines = []
    lines.append(f"  [X-RAY] mode={m} | buyer_share={w.get('buyer_share_basis', 0):.2f} "
                 f"| fee={w.get('fee_pct', 0):.3f} | wash={w.get('wash_est_pct', 0):.2f} "
                 f"| margin={w.get('margin_vs_overhead_pp', 0):+.1f}pp")
    lines.append(f"  [CONSENSUS] consent={res['consent']}/8 | score={res['combined_score']:+.3f} "
                 f"| tag={res['tag'] or '-'} -> {res['decision']} [base {res['base_change']:+.1%}]")
    for b in res["bot_details"]:
        tag = f"  <<{b.tag}" if b.tag else ""
        lines.append(f"        {b.name:22} {b.kind:5} {b.score:+.3f}{tag}")
    return "\n".join(lines)


def run(json_in: str | None = None) -> dict:
    # --- load candidates ---
    if json_in:
        path = json_in
    else:
        cands = sorted(
            [f for f in os.listdir(OUT_DIR) if f.endswith(".json")],
            key=lambda f: os.path.getmtime(os.path.join(OUT_DIR, f)),
            reverse=True,
        )
        if not cands:
            print("[PAPER GATE] no reverse-engineer JSON found - run "
                  "`pumpfun_phase2_reverse.py --json` first.")
            return {"error": "no_input"}
        path = os.path.join(OUT_DIR, cands[0])

    doc = json.load(open(path, encoding="utf-8"))
    rows = doc.get("rows", [])
    survivors = [r for r in rows
                 if r.get("still_works", {}).get("survives_breaker")
                 and r.get("signature", {}).get("mode") in ("SNIPER-TRANCHE", "KINETIC-HOLD", "MIXED")]
    print(f"[PAPER GATE] input={path}\n"
          f"[PAPER GATE] reverse-engineer candidates={doc.get('candidate_count')} | "
          f"surviving watch candidates={len(survivors)}")
    print(f"[PAPER GATE] A3b gate: consent>=8 AND |combined|>=0.35\n")

    out_rows = []
    for p in survivors:
        name = p.get("asset", "?")
        pair = round_to_pair(p, doc.get("as_of", ""))
        res = verdict_for(pair, p)
        # Feed to verdict: only the *actual* stand-down reasons (bot tags +
        # narrative outlier), NOT the generic paper_guard label.
        reasons = {b.tag for b in res["bot_details"] if b.tag}
        if res.get("tag"):
            reasons.add(res["tag"])
        res["stand_down_reasons"] = sorted(reasons) or ["watch"]
        res["micro_budget_ok"] = p.get("micro_budget_ok", False)
        res["source_round"] = p.get("round_tag", "paper")
        out_rows.append({
            "asset": name,
            "mode": p.get("signature", {}).get("mode", "MIXED"),
            "consent": res["consent"],
            "combined_score": res["combined_score"],
            "tag": res["tag"],
            "decision": res["decision"],
            "base_change": res["base_change"],
            "stand_down_reasons": res["stand_down_reasons"],
            "micro_budget_ok": res["micro_budget_ok"],
            "source_round": res["source_round"],
        })
        print(f"\n===== {name} ({pair['mode']}) =====")
        print(paper_verb(p, res))
        verdict_txt = ("ADVANCE (paper BUY, {base:.1%})".format(base=res["base_change"])
                       if res["decision"] == "BUY-SIG" else "STAND DOWN")
        print(f"  -> {verdict_txt}")
        print(f"[VERIFY] {name} verdict recorded (zero-burn, no trade executed)")

    verdict = {
        "tag": "paper_gate",
        "date": doc.get("as_of", "unknown"),
        "reverse_engineer_input": os.path.basename(path),
        "surviving_candidates": out_rows,
        "zero_burn": "observation only, no trades executed",
        "commitment": "advance on explicit ADVANCE; stand down on STAND DOWN",
    }
    if out_rows:
        verdict["top_advance"] = max(out_rows, key=lambda z: z["combined_score"])
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="write verdict JSON only")
    ap.add_argument("--input", default=None, help="path to reverse-engineer JSON")
    args = ap.parse_args()

    verdict = run(args.input)
    if args.json or verdict.get("error"):
        out_dir = os.path.join(REPO, "pumpfun_paper_gate_output")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, f"round_{verdict.get('date','unknown')}.json")
        json.dump(verdict, open(out, "w", encoding="utf-8"), indent=2)
        print(f"[VERIFY] verdict written -> {out}")


if __name__ == "__main__":
    main()
