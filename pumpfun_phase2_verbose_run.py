"""Phase 2 paper-only pump.fun scanner — VERBOSE edition (observation only).

Replaces the aggregate-only output of `pumpfun_phase2_paper_run.py`:

  OLD (aggregate):  symbol  consent  |score|  tag        decision
  NEW (verbose):    per-pair rollup of EVERY bot's vote,
                    then one stand-down reason PER pair.

Design:
  * Read-only, zero-burn: NO trades executed anywhere.
  * Sources: RealTradeFeed (verified live DEX data, read-only).
  * Gate: consensus_aggregator multi-bot A3b gate (5 heuristic bots +
    3 volume copies = 8 votes, floor of 8).
  * Fallback: deterministic simulated candidate table so the demo runs
    offline with ZERO live credentials, zero API keys, zero burn.
  * Exit code is always 0. Observation only — never fails.

Run from the repo root:
  python3 pumpfun_phase2_verbose_run.py
"""
from __future__ import annotations

import sys

REPO_ROOT = "/Users/test/projects/lyta-grokbot-multi"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from real_trade_feed import RealTradeFeed  # noqa: E402
from consensus_aggregator import (  # noqa: E402
    ConsensusAggregator,
    SignalSource,
    VolumeMomentumBot,
    CONSENSUS_MIN,
    SIGNAL_GATE,
)

# --- The 8-vote A3b roster (same composition as the aggregator demo) ------
BASE_VOTERS = [
    ("VolumeMomentumBot", SignalSource.__subclasses__()[0]),
    ("LiquidityHealthBot", SignalSource.__subclasses__()[1]),
    ("HolderConcentrationBot", SignalSource.__subclasses__()[2]),
    ("VolatilityDiscordBot", SignalSource.__subclasses__()[3]),
    ("SocialHypeBot", SignalSource.__subclasses__()[4]),
]


class _BaseVolumeBot(SignalSource):
    """Sub-class of SignalSource with a minimal __init__ that registers itself."""

    def __init__(self, name: str):
        super().__init__(name)


def build_voters():
    """Fresh signal-source instances: 5 heuristic bots + 3 VolumeMomentumBot copies."""
    bots = [(name, cls(name)) for name, cls in BASE_VOTERS]
    for i in (1, 2, 3):
        bots.append(("VolumeMomentumBot#%d" % i,
                     VolumeMomentumBot("VolumeMomentumBot#%d" % i)))
    return bots


# --- Deterministic simulated candidates (zero-burn offline fallback) ------
# Shapes match RealTradeFeed.fetch() dict keys so the gate sees identical data.

SIM_PAIRS = [
    # (chain, dex, base, quote, liquidity_usd, vol24_usd, fee, age_min, narrative)
    ("solana", "pump", "GOBLIN", "SOL", 3_200_000, 2_400_000, 0.003, 5, ""),            # mid-strong, no narrative
    ("solana", "pump", "JADECLAW", "SOL", 4_100_000, 3_800_000, 0.002, 60, "green"),       # strong + green spot
    ("solana", "pump", "RUGGY", "SOL", 2_900_000, 3_500_000, 0.003, 60, "red"),            # strong + red trap
    ("solana", "pump", "THIN", "SOL", 600_000, 450_000, 0.003, 10, ""),                      # thin volume/fee
    ("solana", "pump", "DRY", "SOL", 150_000, 5_000, 0.003, 5, ""),                          # no liquidity
    ("solana", "pump", "NEWFEE", "SOL", 2_500_000, 2_000_000, 0.012, 60, ""),                # high-fee dump
]


def _sim_to_pair(chain, dex, base, quote, liq, vol24, fee, age, narr):
    return {
        "chain": chain,
        "dex": dex,
        "base": base,
        "quote": quote,
        "liquidity_usd": liq,
        "vol24_usd": vol24,
        "fee": fee,
        "age_minutes": age,
        "narrative": narr,
    }


def fetch_pairs(feed, limit=20, retries=3):
    """Live fetch from verified read-only sources; fall back to simulated pairs."""
    pairs = None
    for _ in range(retries):
        try:
            pairs = feed.fetch(query="pump", limit=limit)
            if pairs:
                return pairs
        except Exception as exc:  # noqa: BLE001
            pairs = None
            print(f"[feed] live fetch attempt failed ({exc}); falling back to "
                  f"simulated observation pairs (zero-burn).")
    return [_sim_to_pair(*row) for row in SIM_PAIRS]


# --- Verbose per-pair reporting ------------------------------------------

def verbose_pair(idx, total, pair, voters):
    """Print one pair: per-bot votes, gate rollup, then stand-down reason."""
    print("=" * 72)
    print(f"PAIR {idx}/{total}   {pair['base']}/{pair['quote']}"
          f"  ({pair.get('dex', '?')}/{pair.get('chain', '?')})")
    print(f"   liquidity ${pair.get('liquidity_usd', 0):,}   vol24 ${pair.get('vol24_usd', 0):,}")
    print(f"   fee {pair.get('fee', 0):.3f}   age {pair.get('age_minutes', 0)}m"
          f"   narrative={pair.get('narrative') or '-'}")
    print("-" * 72)
    print("PER-BOT VERBOSE VOTES (A3b gate, 8 votes):")
    agg = ConsensusAggregator([inst for _, inst in voters])
    votes = agg.vote(pair)
    for s in votes:
        tag = f"  << {s.tag}" if s.tag else ""
        print(f"   [{s.name:24s}] {s.kind:5s} {s.score:+.3f}{tag}")
    r = agg.consensus(pair, narrative=pair.get("narrative", ""))
    print("-" * 72)
    print(f"GATE ROLLUP: consent {r['consent']}/{CONSENSUS_MIN}"
          f"   |combined| {abs(r['combined_score']):.3f}"
          f"   tag={r['tag'] or '-'}   decision={r['decision']}")
    reasons = []
    if r["qualified"]:
        print("RESULT: QUALIFIED (gate opens)")
    else:
        if r["consent"] < CONSENSUS_MIN:
            reasons.append(f"consensus_min {r['consent']}/{CONSENSUS_MIN}")
        if abs(r["combined_score"]) < SIGNAL_GATE:
            reasons.append(f"signal_gate {r['combined_score']:+.3f} < {SIGNAL_GATE}")
        if r["tag"]:
            reasons.append(f"tag {r['tag']}")
        print("STAND DOWN — " + "; ".join(reasons) + ".")
    return r


def main() -> int:
    print("=" * 72)
    print(" PHASE 2 PAPER DEMO — pump.fun MEMECOIN SCANNER (VERBOSE)")
    print(" THIS RUN IS OBSERVATION ONLY. NO TRADES EXECUTED.")
    print("=" * 72)
    print("sources: RealTradeFeed (read-only verified DEX data) + multi-bot A3b gate")
    print()

    feed = RealTradeFeed()
    pairs = fetch_pairs(feed, limit=20)

    print(f"observation pairs in scope: {len(pairs)}\n")

    voters = build_voters()
    results = []
    for i, p in enumerate(pairs, start=1):
        r = verbose_pair(i, len(pairs), p, voters)
        results.append(r)

    qualifying = [r for r in results if r["qualified"]]
    print("=" * 72)
    print(f"OBSERVATION SUMMARY: {len(results)} pairs scanned, "
          f"{len(qualifying)} qualified, {len(results) - len(qualifying)} stand down")
    for r in results:
        if not r["qualified"]:
            print(f"   stand-down: {r['decision']}")
    print("ZERO TRADES EXECUTED — this is paper-only observation.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
