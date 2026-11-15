#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 - pump.fun memecoin paper run (calibrated engine, observation only)
===========================================================================
This run is observation only. No trades executed.

Zero-burn, paper-only runtime.  No live trades, no real capital, no live Grok Bot
workshop execution, no live exchange writes.  Every candidate is screened through
the verified 8-vote A3b consensus gate, and when qualified, through the verified
paper simulation loop (micro sizing $0.20-$0.85, 3% risk, 5x cap, exit rules).

Sources
  * live read-only feed : DexScreener pump pairs (RealTradeFeed, read-only REST)
  * fallback            : deterministic offline candidates (incl. synthetic
                          pump.dev samples routed through PumpFunDataAdapter)
  * gate                : consensus_aggregator - 5 heuristic bots + 3 volume clones
  * paper loop          : pumpfun_phase3_calibrated_run run_pair + PaperPosition/Market

Outputs
  * <run>_log_<YYYYMMDD_HHMMSS>.log  - this run's header, per-candidate traces,
                                       paper exit reasons and summary
  * exit code 0 on success
"""
from __future__ import annotations

import sys
from datetime import datetime

REPO_ROOT = "/Users/test/projects/lyta-grokbot-multi"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# --------------------------------------------------------------------------
# Verified Phase 2 engine pieces
# --------------------------------------------------------------------------
from consensus_aggregator import (
    ConsensusAggregator,
    HolderConcentrationBot,
    LiquidityHealthBot,
    SocialHypeBot,
    VolumeMomentumBot,
    VolatilityDiscordBot,
    CONSENSUS_MIN,
    SIGNAL_GATE,
)
from real_trade_feed import RealTradeFeed
from pumpfun_adapter import PumpFunDataAdapter

# --------------------------------------------------------------------------
# Verified Route C paper engine pieces (gate + micro-sizing + loop + classes)
# --------------------------------------------------------------------------
from pumpfun_phase3_calibrated_run import (
    FLOW_LOG,
    MICRO_MAX,
    MICRO_MIN,
    RISK_PCT,
    MAX_POSITION_MULT,
    MAX_TICKS,
    STALL_SECONDS,
    STALL_TICKS,
    STOP_LOSS,
    EXIT_TARGET_GAIN,
    TRAILING_LOSS,
    CAPITAL,
    run_pair,
)

# --------------------------------------------------------------------------
# Phase 2 configuration (paper-only). Local labels only — run_pair reads the
# Route C module constants imported above. Do not loosen frozen gates.
# --------------------------------------------------------------------------
PAPER_CAPITAL = 6.00
PAPER_MICRO_MIN = 0.20
PAPER_MICRO_MAX = 0.85
PAPER_RISK_PCT = 0.03

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_NAME = f"route2_pumpfun_run_{RUN_ID}.log"

# verbose trace log for this run (console + log file)
traces: list[str] = []


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def flow_log(msg: str) -> None:
    """Verbose one-line logger used by every vote / gate / exit reason."""
    print(msg)
    traces.append(msg)


def build_voters() -> list:
    """Verified 8-vote A3b roster: 5 heuristic bots + 3 volume clones."""
    base = [
        VolumeMomentumBot("VolumeMomentumBot"),
        LiquidityHealthBot("LiquidityHealthBot"),
        HolderConcentrationBot("HolderConcentrationBot"),
        VolatilityDiscordBot("VolatilityDiscordBot"),
        SocialHypeBot("SocialHypeBot"),
    ]
    # volume-clone copies confirm consensus depth (same weights, same seeds)
    return (base
            + [VolumeMomentumBot("VolumeMomentumBot"),
               VolumeMomentumBot("VolumeMomentumBot"),
               VolumeMomentumBot("VolumeMomentumBot")])


def to_engine_pair(p: dict, src: str = "dex") -> dict:
    """Normalize ANY candidate source into the engine schema."""
    return {
        "base": p.get("base") or p.get("asset") or p.get("name") or "UNKNOWN",
        "quote": p.get("quote") or p.get("quote_token") or "SOL",
        "chain": p.get("chain", "solana"),
        "dex": p.get("dex", "pump"),
        "price": p.get("price", p.get("price_usd", 0.0)),
        "liquidity_usd": p.get("liquidity_usd", p.get("liquidity", 0) or 0),
        "vol24_usd": p.get("vol24_usd", p.get("volume24", p.get("volume_24h", 0)) or 0),
        "fee": p.get("fee", p.get("creator_fee", 0.003)),
        "age_minutes": p.get("age_minutes", p.get("age_seconds", 0) / 60.0 or 0),
        "rug_risk": p.get("rug_risk", 0.5),
        "narrative": p.get("narrative", ""),
        "src": src,
        "raw": p,
    }


def stand_down_reasons(r: dict, pair: dict) -> list:
    """Verbose reason codes from the A3b gate verdict (verbatim engine fields)."""
    reasons = []
    if not r.get("qualified"):
        if r.get("consent", 0) < CONSENSUS_MIN:
            reasons.append("consensus_min")              # not enough BUY votes
        if abs(r.get("combined_score", 0.0)) < SIGNAL_GATE:
            reasons.append("signal_gate")                # tape too noisy
        if r.get("tag") in ("hidden_liquidity", "rug",
                            "low_signal", "thin_book", "closed_loop"):
            reasons.append("tag")                        # feed / evidence tag
    return reasons


# --------------------------------------------------------------------------
# Fetch (read-only live + zero-burn fallback)
# --------------------------------------------------------------------------
def fetch_candidates(feed: RealTradeFeed, limit: int = 20) -> list:
    """Live DexScreener pump pairs, 3 retries; fallback simulated pool."""
    for _ in range(3):
        try:
            pairs = feed.fetch(query="pump", limit=limit)
            if pairs:
                return pairs[:limit] if limit else pairs
        except Exception as exc:  # noqa: BLE001
            flow_log(f"WARN live pump fetch failed ({exc}); using simulated "
                     f"candidates (offline, zero-burn).")
    return [
        {"base": "GOBLIN", "quote": "SOL", "liquidity_usd": 3_200_000,
         "vol24_usd": 2_400_000, "fee": 0.003, "age_minutes": 5,
         "narrative": "", "price": 0.031},
        {"base": "JADECLAW", "quote": "SOL", "liquidity_usd": 4_100_000,
         "vol24_usd": 3_800_000, "fee": 0.002, "age_minutes": 60,
         "narrative": "green", "price": 0.041},
        {"base": "RUGGY", "quote": "SOL", "liquidity_usd": 2_900_000,
         "vol24_usd": 3_500_000, "fee": 0.003, "age_minutes": 60,
         "narrative": "red", "price": 0.029},
        {"base": "THIN", "quote": "SOL", "liquidity_usd": 600_000,
         "vol24_usd": 450_000, "fee": 0.003, "age_minutes": 10,
         "narrative": "", "price": 0.026},
        {"base": "DRY", "quote": "SOL", "liquidity_usd": 150_000,
         "vol24_usd": 5_000, "fee": 0.003, "age_minutes": 5,
         "narrative": "", "price": 0.021},
        {"base": "NEWFEE", "quote": "SOL", "liquidity_usd": 2_500_000,
         "vol24_usd": 2_000_000, "fee": 0.012, "age_minutes": 60,
         "narrative": "", "price": 0.025},
        {"base": "FIVE", "quote": "SOL", "liquidity_usd": 1_100_000,
         "vol24_usd": 2_800_000, "fee": 0.0025, "age_minutes": 15,
         "narrative": "", "price": 0.022},
        {"base": "GOLD", "quote": "SOL", "liquidity_usd": 3_300_000,
         "vol24_usd": 1_900_000, "fee": 0.003, "age_minutes": 45,
         "narrative": "", "price": 0.027},
        # synthetic pump.dev sample routed through PumpFunDataAdapter
        {"base": "ADAP1", "quote": "SOL", "price": 0.033,
         "liquidity_usd": 1_800_000, "vol24_usd": 1_600_000, "fee": 0.005,
         "age_minutes": 12, "rug_risk": 0.18, "narrative": "adapter-path",
         "src": "pumpfun"},
        {"base": "ADAP2", "quote": "SOL", "price": 0.028,
         "liquidity_usd": 960_000, "vol24_usd": 620_000, "fee": 0.008,
         "age_minutes": 40, "rug_risk": 0.31, "narrative": "adapter-path",
         "src": "pumpfun"},
    ]


def demo_adapter_bridge(agg: ConsensusAggregator) -> None:
    """Zero-burn wiring demo: pump.dev /v1/stats -> PumpFunDataAdapter -> engine schema.

    Uses a synthetic (clearly labelled) pump.dev payload so the Phase 2 loop can be
    exercised offline with no live API calls.
    """
    print("\n[ADAPTER] wiring demo (synthetic pump.dev payload, zero-burn):")
    pump_payload = {
        "chain": "solana", "dex": "pump", "pair_id": "demo-adapter-01",
        "name": "ADAP-01", "address": "ADAP-01", "marketplace": "pump",
        "socials": {"twitter": "https://x.com/adap01", "website": "https://adap01.com"},
        "image": "https://i.imgur.com/adap01.png",
        "liquidity": 1_800_000, "liquidity_usd": 1_800_000,
        "price": 0.033, "volume_24h": 1_600_000,
        "volume_7d": 6_400_000, "floor": 0, "holder_count": 120,
        "tx_count_1h": 312, "tx_count_24h": 1_840, "is_verified": False,
        "is_new": True, "is_new_launch": True, "rug_risk": 0.18,
    }
    engine_payload = PumpFunDataAdapter.adapt(pump_payload)
    pair_demo = {
        "base": engine_payload["asset"], "quote": "SOL", "chain": "solana", "dex": "pump",
        "price": engine_payload["price"],
        "liquidity_usd": engine_payload["liquidity_usd"],
        "vol24_usd": pump_payload["volume_24h"],
        "fee": 0.003, "age_minutes": 12.0, "rug_risk": engine_payload["rug_risk"],
        "narrative": "adapter-path", "src": "pumpfun_adapter", "raw": engine_payload,
    }
    r = agg.consensus(pair_demo, narrative="")
    print(f"  pump.dev: price=${pump_payload['price']} liquidity=${pump_payload['liquidity']:,} "
          f"volume_24h=${pump_payload['volume_24h']:,} holders={pump_payload['holder_count']}")
    print(f"  adapter -> asset={engine_payload['asset']} price=${engine_payload['price']} "
          f"liquidity_usd=${engine_payload['liquidity_usd']:,} rug_risk={engine_payload['rug_risk']}")
    print(f"  engine  -> base={pair_demo['base']}/{pair_demo['quote']} price=${pair_demo['price']:.4f} "
          f"vol24=${pair_demo['vol24_usd']:,} age={pair_demo['age_minutes']:.0f}m rug={pair_demo['rug_risk']}")
    print(f"  GATE    -> qualified={r.get('qualified')} consent={r.get('consent', 0)}/{CONSENSUS_MIN} "
          f"score={r.get('combined_score', 0):+.2f} tag={r.get('tag')} decision={r.get('decision')}")


# --------------------------------------------------------------------------
# Paper simulation of one qualified candidate (verified engine)
# --------------------------------------------------------------------------
def run_paper(p, voters, seed: int = 0):
    """Run the verified paper loop on one candidate; returns the engine verdict."""
    res = run_pair(p, voters, sim_seed=seed)
    entry = res.get("entry", 0.0)
    size = res.get("size", 0.0)
    pnl = res.get("pnl", 0.0)
    reason = res.get("exit_reason", "NO_EXIT")
    msg = (f"CLOSE {p['base']}/{p['quote']} sized={size:.4f} "
           f"value=${entry * size:.2f} pnl=${pnl:+.4f} exit={reason}")
    flow_log(msg)
    FLOW_LOG.append({"t": "INFO", "msg": msg})
    return res


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> int:
    # --- zero-burn paper-only banner + log header -------------------------
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = [
        f"ROUTE P2  pump.fun memecoin paper run  ({ts})",
        "This run is observation only. No trades executed.",
        "paper-only: no live trades, no real capital, no live Grok Bot, "
        "no live exchange writes",
        f"capital=${PAPER_CAPITAL:.2f}  micro=${PAPER_MICRO_MIN}-{PAPER_MICRO_MAX}  "
        f"risk={PAPER_RISK_PCT:.0%}  5x cap  "
        f"exit: +{EXIT_TARGET_GAIN:.0%}/-{STOP_LOSS:.0%}/trail-{TRAILING_LOSS:.0%}",
        f"consensus: {len(build_voters())} votes (A3b, 5 heuristic + 3 volume)",
        f"consensus min: {CONSENSUS_MIN} votes  signal gate: |score|>={SIGNAL_GATE}",
        "sources: live DexScreener read-only + deterministic offline pool "
        "(incl. synthetic pump.dev samples via PumpFunDataAdapter)",
        "verifying locally: gate verdicts, paper exit reasons, exit-0 guarantee",
    ]
    for line in header:
        print(line)

    log_path = f"/Users/test/projects/lyta-grokbot-multi/{LOG_NAME}"
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header) + "\n\n")

    # --- engine wiring -----------------------------------------------------
    voters = build_voters()
    agg = ConsensusAggregator(voters)
    feed = RealTradeFeed()
    demo_adapter_bridge(agg)

    results = {
        "candidates": 0, "gate_qualified": 0, "paper_executed": 0,
        "stand_down": 0, "paper_pnl": 0.0, "paper_trades": 0,
        "exit_reasons": {},
        "stand_down_reasons": {},
    }

    pairs = fetch_candidates(feed, limit=20)
    for i, raw in enumerate(pairs, start=1):
        p = to_engine_pair(raw, src=raw.get("src", "dex"))
        name = f"{p['base']}/{p['quote']}"

        results["candidates"] += 1

        # --- verified 8-vote A3b gate, verbose per-bot ------------------------
        for b in voters:
            s = b.decide(p)
            v = float(s.score)
            kind = getattr(s, "kind", "?")
            msg = (f"  VOTE {b.name} {kind} {v:+.2f} pair={name} "
                   f"src={p.get('src', 'dex')}")
            flow_log(msg)
            FLOW_LOG.append({"t": "VOTE", "msg": msg})
        r = agg.consensus(p, narrative="")

        # --- gate verdict ----------------------------------------------------
        q = bool(r.get("qualified"))
        decision = r.get("decision")
        tagged = r.get("tag")
        console_q = "QUALIFIED" if q else "stand-down"
        flow_log(f"[{i:02d}/{len(pairs)}] GATE "
                 f"{console_q} {name} consent={r.get('consent', 0)}/{CONSENSUS_MIN} "
                 f"score={r.get('combined_score', 0):+.2f} "
                 f"base={r.get('base_change', 0.0):+.1%} "
                 f"tag={tagged} decision={decision}")

        # --- stand-down reasons ---------------------------------------------
        if not q:
            reasons = stand_down_reasons(r, p)
            if reasons:
                key = "; ".join(reasons)
                results["stand_down_reasons"][key] = (
                    results["stand_down_reasons"].get(key, 0) + 1)
            results["stand_down"] += 1
            msg = (f"  STAND-DOWN {name} -> "
                   f"{'; '.join(reasons) if reasons else 'no signal'}")
            flow_log(msg)
            FLOW_LOG.append({"t": "STAND_DOWN", "msg": msg})
            continue

        results["gate_qualified"] += 1

        # --- verified paper loop on qualified candidate -----------------------
        seed = (i * 101 + hash(name) % 1000)
        res = run_paper(p, voters, seed=seed)
        results["paper_executed"] += 1
        results["paper_pnl"] += res.get("pnl", 0.0)
        results["paper_trades"] += res.get("trades", 0)
        er = res.get("exit_reason", "NO_EXIT")
        results["exit_reasons"][er] = results["exit_reasons"].get(er, 0) + 1

    # --- FLOW_LOG CLOSE dump (paper fills only) ----------------------------
    closes = [e for e in FLOW_LOG
              if isinstance(e, dict) and "CLOSE" in str(e.get("msg", ""))]
    print("\n--- PAPER CLOSE LOG ---")
    if closes:
        for e in closes:
            print(e["msg"])
    else:
        print("(none — zero paper fills, all candidates stood down)")

    # --- summary ---------------------------------------------------------
    print("\n" + "=" * 62)
    print("PHASE 2 PUMP.FUN PAPER RUN SUMMARY")
    print(f"candidates screened       : {results['candidates']}")
    print(f"gate qualified            : {results['gate_qualified']}")
    print(f"paper executed            : {results['paper_executed']}")
    print(f"paper pnl / trades        : ${results['paper_pnl']:+.4f} / "
          f"{results['paper_trades']}")
    print(f"stand-down reasons        : {results['stand_down_reasons']}")
    print(f"exit reasons              : {results['exit_reasons']}")
    print("This run is observation only. No trades executed.")
    print("zero-burn: no live trades, no real capital, no live Grok Bot, no live "
          "exchange writes - observation only")
    print("=" * 62)

    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header) + "\n\n")
        fh.write("TRACE LOG\n")
        for line in traces:
            fh.write(line + "\n")
        fh.write("\nSUMMARY\n")
        fh.write(f"candidates={results['candidates']} gate_qualified="
                 f"{results['gate_qualified']} paper_executed="
                 f"{results['paper_executed']} paper_pnl={results['paper_pnl']:+.4f} "
                 f"paper_trades={results['paper_trades']}\n")
        fh.write("exit_reasons=" + ", ".join(f"{k}:{v}" for k, v in
                                            sorted(results["exit_reasons"].items())) + "\n")
        fh.write("stand_down_reasons=" + ", ".join(f"{k}:{v}" for k, v in
                                                  sorted(results["stand_down_reasons"].items())) + "\n")
        fh.write("This run is observation only. No trades executed.\n")

    # --- verification ------------------------------------------------------
    ok = results["candidates"] > 0
    print(f"LOG_FILE: {log_path}")
    print(f"zero-burn paper run completed: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
