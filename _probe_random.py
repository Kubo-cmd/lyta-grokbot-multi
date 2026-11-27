import sys, random
sys.path.insert(0, '/Users/test/projects/lyta-grokbot-multi')
import paper_run as pr

def setup(seed):
    pr.random = random.Random(seed)
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

setup(42)
m1 = pr.generate_market()
s1 = pr.compute_signal(m1)
v1 = {b: pr.run_bot(b, s1) for b in pr.BOT_NAMES}
print("ONE-OFF")
print(" market:", m1['symbol'], m1['trend'], round(m1['change24h'], 2), m1['score'],
      round(m1['rug_risk'], 3), round(m1['liquidity'], 3), round(m1['volume'], 3))
print(" signal:", round(s1['signal'], 3))
print(" votes:", v1)
print(" random state:", pr.random.getstate()[1][0] if len(pr.random.getstate()[1]) else None)

import paper_tune_harness as H
r = H._single_tick(42, verbose=True)
print("HARNESS")
print(" market:", r['symbol'] if 'symbol' in r else '?', r['trend'], r['change24h'], r['score'],
      r['rug_risk'], r['liquidity'], r['volume'])
print(" signal:", r['signal'])
print(" votes:", {k: str(v) for k, v in r.items() if k.endswith('_votes')})
try:
    print(" state:", r['state'] if 'state' in r else '?')
except Exception:
    pass
