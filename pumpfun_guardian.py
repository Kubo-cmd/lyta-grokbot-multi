#!/usr/bin/env python3
"""
LYTA pump.fun Grok Desk - Pre-Trade Kill Switch Guardian (Option-C upgrade).

Purpose:
  Turns the Phase-2 paper desk from a "trawl 200+ candidates" engine into the
  99.8%-standard gateway the zostaff desk describes: a candidate is inspected
  against structural kill rules BEFORE any liquidity forms, and is rejected
  on paper only.  No live trades, no real capital, zero API hits in default
  mode.

Guardian rules (derived from the Phase-2 freeze findings + zostaff 2026 news):
  K1 hidden_liquidity : liquidity < LIQ_RATIO x vol24h  -> STANDBY (kill pre-liquidity)
  K2 consensus_quota  : best-pair consensus capped at 7/8 while desk needs 8 (A3b)-> STANDBY
  K3 signal_gate      : |score| < SIGNAL_GATE       -> STAND_DOWN (no trade)
  K4 xray_luck        : 3-question x-ray verdict = "luck"/spoof -> KILL
  K5 dev_watch        : paper proxy for dev-wallet exit flag (env switch only, never live)
                       -> KILL

Paper-only default.  --live refuses unless all of these env keys are set:
  PUMPFUN_API_KEY, DEXSCREENER_API_KEY, GECKO_TERMINAL_API_KEY, BIRDEYE_API_KEY

Output: print + JSON file (<run_id>_guardian_results.json) for the ledger.
"""
from __future__ import annotations

import json
import os
import random
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

# ---- gate thresholds (frozen Phase-2 constants carried into the guardian) ---
QUORUM = 8                    # A3b fixed consensus ceiling the desk requires
CONSENT_CEILING = 7           # observed loose-floor ceiling (V1/V2) -> hard stand-down
SIGNAL_GATE = 0.35            # |score| >= gate to stay alive to fill stage
LIQ_RATIO = 2.0               # liquidity must be >= 2.0 x vol24h else hidden_liquidity
DATA_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass(frozen=True)
class KillRule:
    id: str
    name: str
    active: bool


def _live_safe() -> bool:
    """True only when every required live key is set (paper mode: all unset)."""
    return all(os.environ.get(k) for k in (
        "PUMPFUN_API_KEY", "DEXSCREENER_API_KEY",
        "GECKO_TERMINAL_API_KEY", "BIRDEYE_API_KEY",
    ))


class Guardian:
    def __init__(self, seed: int = 42, live: bool = False):
        self.rng = random.Random(seed)
        self.live = live and _live_safe()
        if self.live and not _live_safe():
            raise SystemExit(
                "[guardian] REFUSED live mode: set PUMPFUN_API_KEY, "
                "DEXSCREENER_API_KEY, GECKO_TERMINAL_API_KEY, BIRDEYE_API_KEY "
                "or run in paper mode (default)."
            )
        self.rules = {
            "K1": KillRule("K1", "hidden_liquidity", True),
            "K2": KillRule("K2", "consensus_quota", True),
            "K3": KillRule("K3", "signal_gate", True),
            "K4": KillRule("K4", "xray_luck", True),
            "K5": KillRule("K5", "dev_watch", True),
        }

    # -- candidate helpers (paper-only synthetic pool; replaces network fetch) --
    @staticmethod
    def _synthetic_candidate(idx: int, seed: int) -> dict:
        """Offline pump.fun-format candidate for demo only.  Zero API."""
        rng = random.Random(seed * 1000 + idx)
        return {
            "name": f"CryptoX{idx:03d}",
            "symbol": f"CTX{idx:03d}",
            "token_address": f"0xdemo{idx:04x}deadbeef",
            "pair": f"CryptoX{idx:03d}/CTX{idx:03d}",
            "price": round(rng.uniform(0.000008, 0.0006), 8),
            "is_pump": True,
            "is_new_launch": True,
            "on_bonding_curve": True,
            "analyst_score": round(rng.uniform(0.5, 0.99), 3),
            "rug_risk": round(rng.uniform(0.05, 0.45), 3),
            "liquidity": round(rng.uniform(200, 12000), 0),
            "liquidity_usd": round(rng.uniform(200, 12000), 0),
            "buys_5m": rng.randint(5, 40),
            "sells_5m": rng.randint(0, 3),
            "buys_total": rng.randint(10, 120),
            "change_5m": round(rng.uniform(-2.0, 6.0), 1),
            "change_1h": round(rng.uniform(-1.0, 3.0), 1),
            "change_6h": round(rng.uniform(-0.5, 2.0), 1),
            "change_24h": round(rng.uniform(-3.0, 8.0), 1),
            "unique_buyers": rng.randint(8, 90),
            "has_metadata": rng.random() < 0.7,
            "vol24h": round(rng.uniform(50, 4000), 0),
            "dev_wallet_exit": False,   # paper proxy; never set in live(simulated) mode
            "xray_verdict": "hold",     # "hold" | "luck" | "still-works"
            "consent": 8,
            "score": round(rng.uniform(-0.6, 0.95), 3),
            "tag": "",
        }

    @staticmethod
    def _rebuild_frozen_candidate(pair: str, consent: int, score: float, tag: str) -> dict:
        """Reconstruct a candidate from the frozen 24-candidate probe log."""
        m = pair.split("/")
        symbol = m[-1]
        return {
            "name": pair,
            "symbol": symbol,
            "token_address": f"0xfrozen-{symbol.lower()}",
            "pair": pair,
            "price": 0.000013,
            "is_pump": True,
            "is_new_launch": True,
            "on_bonding_curve": True,
            "analyst_score": round(min(max(score / 100.0, 0.0), 1.0), 3),
            "rug_risk": 0.25,
            "liquidity": 600.0,
            "liquidity_usd": 600.0,
            "buys_5m": 8,
            "sells_5m": 1,
            "buys_total": 14,
            "change_5m": 0.1,
            "change_1h": 0.4,
            "change_6h": 1.2,
            "change_24h": 3.1,
            "unique_buyers": 11,
            "has_metadata": True,
            "vol24h": 410.0,
            "dev_wallet_exit": False,
            "xray_verdict": "hold",
            "consent": consent,
            "score": score,
            "tag": tag,
        }

    # -- decision engine --
    def judge(self, cand: dict) -> dict:
        """Returns the guardian verdict dict for one candidate."""
        reasons: list[str] = []
        verdict = "KEEPER"
        asset = cand.get("pair") or cand.get("symbol") or cand.get("name", "?")

        if self.rules["K1"].active:
            vol = float(cand.get("vol24h", 0) or 0)
            liq = float(cand.get("liquidity", 0) or 0)
            if vol > 0 and liq < LIQ_RATIO * vol:
                reasons.append("hidden_liquidity (liquidity<2x vol24h)")
                verdict = "STANDBY"

        if self.rules["K2"].active and isinstance(cand.get("consent"), int):
            if cand["consent"] < QUORUM and cand["consent"] <= CONSENT_CEILING:
                reasons.append(f"consent_quota ceiling {cand['consent']}/{QUORUM}")
                verdict = "STANDBY"

        if self.rules["K3"].active:
            score = float(cand.get("score", 0) or 0)
            if abs(score) < SIGNAL_GATE:
                reasons.append(f"signal_gate |score|={abs(score):.3f}<{SIGNAL_GATE}")
                verdict = "STAND_DOWN"

        if self.rules["K4"].active and cand.get("xray_verdict") == "luck":
            reasons.append("xray_luck")
            verdict = "KILL"

        if self.rules["K5"].active and bool(cand.get("dev_wallet_exit")):
            reasons.append("dev_watch exit-flag")
            verdict = "KILL"

        return {
            "asset": asset,
            "pair": cand.get("pair"),
            "verdict": verdict,
            "score": float(cand.get("score", 0) or 0),
            "consent": cand.get("consent"),
            "liquidity": float(cand.get("liquidity", 0) or 0),
            "vol24h": float(cand.get("vol24h", 0) or 0),
            "rug_risk": float(cand.get("rug_risk", 0) or 0),
            "reasons": reasons,
        }

    # -- batch run --
    def run(self, candidates: list[dict], label: str = "paper-pool") -> dict:
        results = []
        for c in candidates:
            r = self.judge(c)
            results.append({**dict(c), **r})
        counts = {"KEEPER": 0, "STANDBY": 0, "STAND_DOWN": 0, "KILL": 0}
        for r in results:
            counts[r["verdict"]] += 1
        return {
            "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "label": label,
            "guardian_version": "v0.1.0-paper-only",
            "seed": args.seed,
            "rules": {k: asdict(v) for k, v in self.rules.items()},
            "counts": counts,
            "candidates": results,
            "summary": {
                "killed_pre_liquidity": counts["STANDBY"] + counts["KILL"],
                "stand_down": counts["STAND_DOWN"],
                "keepers": counts["KEEPER"],
                "paper_only": True,
                "live_mode": self.live,
            },
        }

    def save(self, out: dict, path: str | None = None) -> str:
        if path is None:
            path = f"{DATA_DIR}/pumpfun_guardian_results_{out['run_id']}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        return path


# ---- CLI ----
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="LYTA pump.fun paper kill switch")
    ap.add_argument("--paper", action="store_true", help="paper-only mode (default)")
    ap.add_argument("--live", action="store_true", help="live: requires 4 env keys (refused otherwise)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--count", type=int, default=40,
                    help="new synthetic candidates to build (frozen log rebuilt separately)")
    args = ap.parse_args()

    if args.live and not _live_safe():
        print("[guardian] REFUSED live mode - set the four env keys first; "
              "paper mode is the default and is all this desk runs on.")
        sys.exit(2)
    live = args.live and _live_safe()

    guard = Guardian(seed=args.seed, live=live)
    cands = [guard._synthetic_candidate(i, args.seed) for i in range(args.count)]

    # Frozen probe set: rebuild the 24 candidates from the freeze log (offline).
    frozen_log = os.path.join(DATA_DIR, "p2adapter_ext_20261115_181248.log")
    if os.path.exists(frozen_log):
        rows = []
        for line in open(frozen_log, encoding="utf-8"):
            if "] GATE stand-down" in line:
                parts = line.split()
                try:
                    pair = parts[3]
                    cons_tok = next(p for p in parts if p.startswith("consent="))
                    consent = int(cons_tok.split("=")[1].split("/")[0])
                    score_tok = next(p for p in parts if p.startswith("score="))
                    score = float(score_tok.split("=")[1])
                    tag = next((p.split("=")[1] for p in parts if p.startswith("tag=")), "")
                    rows.append((pair, consent, score, tag))
                except (ValueError, IndexError, StopIteration):
                    rows.append(("PARSE_FAIL", "bad line"))
        for pair, cons, scr, tag in rows:
            if pair != "PARSE_FAIL":
                cands.append(guard._rebuild_frozen_candidate(pair, cons, scr, tag))
        cands.sort(key=lambda c: c["pair"])

    out = guard.run(cands, label="frozen24+seed47-synthetic")
    p = guard.save(out)
    print(json.dumps(out["summary"], indent=2))
    print(f"[guardian] results -> {p}")
    print("[guardian] paper-only? %s | live_mode=%s" % (out["summary"]["paper_only"], out["summary"]["live_mode"]))
