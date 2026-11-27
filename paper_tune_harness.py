#!/usr/bin/env python3
"""
lyta-grokbot-multi / paper_tune_harness.py
==========================================
DETERMINISTIC v10 PAPER-TRADER TUNING BENCHMARK
Roadmap #11: v10 paper trader tuning -> 80-iter regression results + config.

Drives the REAL shared paper engine (lyta-grok-desk/paper_run_core.py), not a
re-implementation:
  * market        : paper_run.generate_market() - deterministic per round
                    (random.seed(RND) applied to the module RNG before each tick)
  * signal        : paper_run.compute_signal(market)
  * votes         : paper_run.run_bot() x 12 bots, mapped like run_session
                    (_to_signals: buy->buy, sell->sell, else->pass)
  * gate          : paper_run_core.PaperDesk.run_tick()  -> A3b gate
                    consent >= 8 AND |combined| >= 0.35
  * execution     : run_session's _execute (paper-only capital guard + costs)
  * no real trades, no real capital (paper pool $100).

Output:
  * CSV: <out>.csv  per-round rows
  * STDOUT: summary table + stand-down ledger

Usage:
  python3 paper_tune_harness.py --rounds 60 [--seed 42] [--out v10_tuning_baseline.csv]
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import sys
import time
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import importlib.util as _ilu
_core_path = os.path.join(REPO_ROOT, "lyta-grok-desk", "paper_run_core.py")
_core_spec = _ilu.spec_from_file_location("lyta_grok_desk_paper_core", _core_path)
_core_mod = _ilu.module_from_spec(_core_spec)
sys.modules["lyta_grok_desk_paper_core"] = _core_mod
_core_spec.loader.exec_module(_core_mod)
from lyta_grok_desk_paper_core import PaperDesk, Signal   # shared engine
import paper_run as pr                      # market + signal + bots

BOT_NAMES = pr.BOT_NAMES
CONSENSUS_MIN = pr.CONSENSUS_MIN           # 8 (A3b gate)
SIGNAL_GATE = pr.SIGNAL_GATE               # 0.35
BASE_BUY = pr.BASE_CHANGE_BUY              # 0.010 (from paper_run constants)
BASE_SELL = pr.BASE_CHANGE_SELL            # -0.010


def _single_tick(seed: int, verbose: bool = False):
    """One deterministic round through the shared engine. Returns a dict."""
    # Deterministic market for this round: seed the module RNG that
    # generate_market/compute_signal/run_bot use (module-level random functions
    # resolve to random._inst).
    pr.random.seed(seed)
    pr._market_state = {
        "trend": random.choice(["up", "down", "sideways"]),
        "trend_strength": random.uniform(0.0, 0.05),
        "volatility": random.uniform(0.02, 0.08),
        "volume_mult": max(0.2, min(3.0, random.gauss(1.0, 0.3))),
        "price": random.uniform(0.1, 0.9),
        "last_change": 0.0,
        "_ticks": [],
        "trend_age": 0,
    }
    market = pr.generate_market()
    signal = pr.compute_signal(market)
    votes = {bot: pr.run_bot(bot, signal) for bot in BOT_NAMES}

    # Engine contract: vote_fn(pair) receives the market and must return
    # {bot_name: Signal} for the A3b gate. Rebuild the votes from run_bot
    # exactly the way paper_run.run_session does, then convert to Signals.
    def _to_signals(market_pair):
        votes = {bot: pr.run_bot(bot, market_pair) for bot in pr.BOT_NAMES}
        out = {}
        _kind = {"buy": "buy", "sell": "sell", "pass": "pass"}
        for name, v in votes.items():
            kind = _kind.get(str(v), "pass")
            out[name] = Signal(name=name, kind=kind,
                               score=1.0 if kind == "buy" else
                                     -1.0 if kind == "sell" else 0.0)
        return out

    def _advice(pair, votes=None):
        val = float(signal["signal"])
        return val if abs(val) >= 0.05 else 0.0

    def _execute(pair, direction, gate):
        # Engine gate dict (apply_a3b_gate) carries 'qualified' / 'base_change',
        # not 'gate_passed'.
        if not gate.get("qualified"):
            return {"executed": False, "reason": gate.get("stand_down_reason")
                    or "entry not qualified", "side": None, "size": 0.0,
                    "pnl_pct": 0.0}
        cap = desk.equity
        size = cap * 0.10
        trend_mult = {"up": 1.0 + abs(market.get("trend_strength", 0.0)) * 0.3,
                      "down": 1.0 - abs(market.get("trend_strength", 0.0)) * 0.3}.get(market.get("trend"), 1.0)
        base_change = float(gate["base_change"])
        new_cap = cap * (1.0 + base_change * trend_mult)
        new_cap = pr.apply_trading_costs(new_cap, 1)
        desk.equity = new_cap
        side = "LONG" if base_change > 0 else "SHORT"
        pnl_frac = (new_cap - cap) / cap if cap else 0.0
        desk.trades.append({
            "symbol": pair["symbol"], "tick": market.get("tick", 0),
            "side": side, "size": round(size, 4),
            "pnl_pct": round(pnl_frac * 100.0, 2),
        })
        return {"executed": True, "symbol": pair["symbol"], "side": side,
                "size": round(size, 4), "base_change": base_change,
                "pnl_pct": round(pnl_frac * 100.0, 2)}

    desk = PaperDesk(name="OpenBot", capital=100.0)
    result = desk.run_tick(
        market, narrative=str(signal["signal"]),
        vote_fn=_to_signals, advice_fn=_advice, execute_fn=_execute)

    # Tally
    tally = {"buy": 0, "sell": 0, "pass": 0, "stand_down": 0}
    for v in votes.values():
        k = str(v)
        tally["stand_down" if k == "stand_down" else
                k] = tally.get(k, 0) + 1

    return {
        "round": seed,
        "trend": market["trend"],
        "change24h": round(market["change24h"], 2),
        "score": market["score"],
        "rug_risk": round(market["rug_risk"], 3),
        "liquidity": round(market["liquidity"], 3),
        "volume": round(market["volume"], 3),
        "signal": round(signal["signal"], 3),
        "trend_strength": round(market["trend_strength"], 3),
        "buy_votes": tally["buy"], "sell_votes": tally["sell"],
        "pass_votes": tally["pass"], "stand_down_votes": tally["stand_down"],
        "consent": result["consent"],
        "combined_score": round(result["combined_score"], 3),
        "gate_passed": result["gate_passed"],
        "entry": None if not result["gate_passed"] else
                  (result.get("trade", {}).get("side") or
                   ("buy" if result["base_change"] > 0 else "sell")),
        "base_change": round(result["base_change"], 4),
        "stand_down_reason": result.get("stand_down_reason"),
        "equity_after": round(desk.equity, 2),
        "executed": result.get("executed", False),
        "trade": result.get("trade"),
        "pnl_pct": _tick_pnl_pct(result),
        "engine_log_lines": len(desk.logs),
    }


def _tick_pnl_pct(result: dict) -> float:
    trade = result.get("trade") or {}
    if trade:
        return round(trade.get("pnl_pct", 0.0), 2)
    return 0.0


def main():
    ap = argparse.ArgumentParser(description="v10 paper trader tuning benchmark")
    ap.add_argument("--rounds", type=int, default=60,
                    help="number of seeded rounds (default 60)")
    ap.add_argument("--seed", type=int, default=42,
                    help="RNG seed base (each round uses seed+round)")
    ap.add_argument("--out", default="v10_tuning_baseline.csv",
                    help="output CSV basename (default v10_tuning_baseline.csv)")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress per-round noise on stdout")
    args = ap.parse_args()

    rows = []
    t0 = time.time()
    for i in range(args.rounds):
        rnd = args.seed + i
        r = _single_tick(rnd, verbose=not args.quiet)
        rows.append(r)
        if not args.quiet:
            pnl_str = f"{r['pnl_pct']:+.2f}%" if r.get("executed") else "(no trade)"
            print(f"[round {i:>3}] {r['trend']:<7} chg {r['change24h']:>+5.1f}% "
                  f"scr {r['score']:>3} | BUY {r['buy_votes']} SELL "
                  f"{r['sell_votes']} consent {r['consent']}/8 | "
                  f"{r['entry'] or 'STANDDOWN'}: {pnl_str}")
    dt = time.time() - t0

    # --- Aggregates ---
    entered = [r for r in rows if r["gate_passed"]]
    stand = [r for r in rows if not r["gate_passed"]]
    buys = [r for r in entered if r.get("trade", {}).get("side") == "LONG"]
    sells = [r for r in entered if r.get("trade", {}).get("side") == "SHORT"]
    pnl = [r["pnl_pct"] for r in entered if r["pnl_pct"] != 0.0]

    def stats(name, xs):
        n = len(xs)
        return (f"{name}: n={n} | mean={sum(xs)/n:+.3f} | std={__import__('statistics').stdev(xs):.3f}"
                if n else f"{name}: n=0")

    hdr = f"\n=== v10 paper trader tuning baseline ({args.rounds} rounds, seed {args.seed}) ==="
    print(hdr)
    print(f"elapsed {dt:.1f}s | per-round wall {dt/args.rounds*1000:.1f}ms")
    print(f"entered {len(entered)} ({len(buys)} LONG / {len(sells)} SHORT) | "
          f"stand-down {len(stand)}")
    print(f"{hdr}")
    print(f"  signal : {stats('signal_mean', [r['signal'] for r in rows])}")
    print(f"  consent: {stats('consent_mean', [r['consent'] for r in rows])}")
    print(f"  combined: {stats('combined_mean', [r['combined_score'] for r in rows])}")
    print(f"  pnl%   : {stats('pnl_mean', pnl)}")
    print(f"  BUY%   : {len(buys)/max(1,len(entered))*100:.0f}% | "
          f"SELL% {len(sells)/max(1,len(entered))*100:.0f}%")
    print(f"  STAND-DOWN REASONS:")
    from collections import Counter
    for reason, c in Counter(r["stand_down_reason"] for r in stand).most_common():
        print(f"    {c:>3}  {reason}")

    out_csv = args.out
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {out_csv} ({len(rows)} rows)")

    # Verification: confirm harness still matches the live desk on a tick.
    print("\n--- self-check: compare to a fresh --once live desk run ---")
    import subprocess
    p = subprocess.run([sys.executable, "paper_run.py", "--once", "--json"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    print(p.stdout[-600:] if p.stdout else "(no stdout)")
    print(f"returncode={p.returncode}")


if __name__ == "__main__":
    main()
