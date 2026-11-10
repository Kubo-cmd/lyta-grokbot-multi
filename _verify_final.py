#!/usr/bin/env python3
import sys, os, importlib, random
from pathlib import Path
base = str(Path(__file__).resolve().parent)
sys.path.insert(0, base)

import paper_desk_simulator as sim
import paper_adapter as pfa
import grokbot_multi as gbm
import paper_desk_simulator as pds

results = []

# Test 1: SpotDataAdapter.adapt() on circuit-paper payload format
data = {
    "name": "ANTS",
    "token_address": "0x123",
    "price": 0.000001,
    "analyst_score": 0.87,
    "rug_risk": 0.12,
    "liquidity": 120000.0,
    "buys": 51,
    "progress_pct": 35.5,
    "has_metadata": True,
}
adapted = sim.SpotDataAdapter.adapt(data)
t1 = (adapted.get('asset') == 'ANTS' and adapted.get('analyst_score') == 0.87 and
      adapted.get('rug_risk') == 0.12 and adapted.get('liquidity') == 120000.0 and adapted.get('change_5m') == 35.5)
results.append(("Test 1 adapt() spot payload", t1))

# Test 2: make_market() - returns Market object
market = sim.SpotDataAdapter.make_market({"name": "ANTS", "analyst_score": 0.87, "rug_risk": 0.12, "liquidity": 120000.0, "change_5m": 35.5, "has_metadata": True})
t2 = (market.asset == 'ANTS' and market.analyst_score == 0.87)
results.append(("Test 2 make_market()", t2))

# Test 3: adapt() with Market object input
class FakeMarket:
    def __init__(self):
        self.asset = "ANTS"
        self.price = 0.000001
        self.is_pump = False
        self.is_new_launch = True
        self.on_bonding_curve = False
        self.analyst_score = 0.89
        self.rug_risk = 0.15
        self.liquidity = 150000.0
        self.buys_5m = 36
        self.sells_5m = 2
        self.change_5m = 42.0
        self.change_1h = 0.0
        self.change_6h = 0.0
        self.change_24h = 0.0

market_obj = FakeMarket()
adapted2 = sim.SpotDataAdapter.adapt(market_obj)
t3 = (adapted2.get('asset') == 'ANTS' and adapted2.get('analyst_score') == 0.89)
results.append(("Test 3 adapt() Market input", t3))

# Test 4: extract_candidates() with single pump
raw = {"pumps": [
    {"name": "ANTS", "team_address": "0x1", "analyst_score": 0.9, "rug_risk": 0.1, "liquidity": 200000.0, "progress_pct": 40.0, "has_metadata": True},
]}
candidates = sim.SpotDataAdapter.extract_candidates(raw)
t4 = len(candidates) == 1 and candidates[0].get('asset') == 'ANTS'
results.append(("Test 4 extract_candidates()", t4))

# Test 5: fetch_candidates() placeholder (static method)
candidates = list(sim.SpotDataAdapter.fetch_candidates())
t5 = isinstance(candidates, list)
results.append(("Test 5 fetch_candidates()", t5))

# Test 6: spot_adapter_round() with PaperAdapter
class PaperAdapter(sim.SpotDataAdapter):
    """Stands in for live paper fetcher."""
    @staticmethod
    def fetch_candidates():
        import paper_desk_simulator as _sim
        return [_sim.make_spot_market(f"PAD{i}") for i in range(3)]

market = sim.SpotDataAdapter.make_market({"name": "ANTS", "analyst_score": 0.8, "rug_risk": 0.2, "liquidity": 200000.0, "progress_pct": 40.0, "has_metadata": True})
result = sim.spot_adapter_round(600.0, 1, PaperAdapter())
t6 = (result is not None)
results.append(("Test 6 spot_adapter_round()", t6))

# Test 7: BOT_NAMES
t7 = len(sim.BOT_NAMES) == 12
results.append(("Test 7 BOT_NAMES", t7))

# Test 8: Full simulator module import
importlib.reload(sim)
t8 = True
results.append(("Test 8 full import", t8))

print("=== VERIFICATION SUITE ===")
all_pass = True
for name, passed in results:
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    print(f"  {name}: {status}")

print(f"\n{'ALL PASSED' if all_pass else 'SOME FAILED'}")
sys.exit(0 if all_pass else 1)
