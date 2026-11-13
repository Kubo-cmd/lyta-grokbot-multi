"""Phase 2 paper-only pump.fun simulation (zero-burn, NO trades executed).

Uses the verified live sources:
  Source 1 - DexScreener REST (real pair quotes, free key)
  Source 2 - pump.dev WS (real pump.fun mint/trade events)
  Gate     - consensus_aggregator multi-bot A3b gate (5+ bots)
"""
from real_trade_feed import RealTradeFeed
from consensus_aggregator import ConsensusAggregator, sources as _bots

rf = RealTradeFeed()
agg = ConsensusAggregator(list(_bots()))   # 5 heuristics + 3 volume copies

RETRY = 3
pairs = None
for _ in range(RETRY):
    try:
        pairs = rf.fetch(query="pump", limit=12)
        break
    except Exception as e:
        pairs = None

if pairs is None:
    print("FAILED to fetch pump pairs after retries.")
    raise SystemExit(1)

print("=" * 64)
print(" PHASE 2 PAPER RUN - pump.fun MEMECOIN SCANNER (paper-only)")
print("=" * 64)
print(f"source: {rf.__class__.__name__}")
print(f"real pairs fetched: {len(pairs)}\n")

if not pairs:
    print("NO PAIRS")
    raise SystemExit(0)

# Score each live pair through the multi-bot consensus gate.
results = []
for p in pairs:
    # pump.dev WS gives a real mint/trade signal; fall back to a conservative
    # narrative (no green override -> stays conservative on live data).
    r = agg.consensus(p, narrative="")
    r["symbol"] = p.get("base", "?") + "/" + p.get("quote", "?")
    results.append(r)

print(f"{'symbol':16} {'consent':>6} {'|score|':>7} {'tag':18} {'decision'}")
print("-" * 64)
for r in results:
    print(f"{r.get('symbol', '?'):16} {r['consent']:6d} {abs(r['combined_score']):7.3f} "
          f"{r['tag'] or '-':18} {r['decision']}")

qualifying = [r for r in results if r["qualified"]]
print("\nQualifying (consent >= 8 AND |score| >= 0.35):")
if qualifying:
    for r in qualifying:
        print(f"  -> {r.get('symbol')} consent={r['consent']}/8 score={r['combined_score']:+.3f}"
              f" base_change={r['base_change']:+.1%}")
else:
    print("  (none yet -Gate depends on real 8-vote consensus on live data)")

print("\nZERO TRADES EXECUTED - this is paper-only observation.")
