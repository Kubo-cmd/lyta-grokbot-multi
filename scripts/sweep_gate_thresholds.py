#!/usr/bin/env python3
"""
Threshold-sweeping harness for the A3b paper gate.

Purpose: quantify how the A3b gate (consent >= Ct AND |combined| >= St)
responds to repeated tick series -- BEFORE any live change of knobs.
Pure paper math: no trades, no keys, no network.

Inputs:
  * synthetic repeated series        (multiple seeds, bootstrapped snapshots)
  * recorded 15-min OpenBot loop     (/tmp/circuit_15min.log + record json)

Outputs:
  * stdio: sensitivity matrix per series, knife-edge fingerprint
  * /tmp/lyta_gate_sweep.json        : full results for the session log

Design notes (grounded in what the fixed run actually measured):
  * The fixed OpenBot loop logged a verdict signature per tick:
      "A3b gate not met (consent 0/8, score +0.000)"   -> no buy-field votes
  * So every recorded tick carries consent=0, combined=0.000 on the engine that
    ran it.  The sweep therefore feeds each recorded tick to the gate MODULE its
    own combined/consent values are unknown, the sweep moves thresholds and
    reports what the gate mathematics would allow.
"""

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path('/Users/test/projects/lyta-grokbot-multi')
sys.path.insert(0, str(ROOT))

# ---- gate module under test (the shared engine) ----
from consensus_aggregator import (
    CONSENSUS_MIN, SIGNAL_GATE, ConsensusAggregator,
    VolumeMomentumBot, LiquidityHealthBot, HolderConcentrationBot,
    VolatilityDiscordBot, SocialHypeBot, GlintNarrativeProxy, Signal,
)

SAVE = Path('/tmp/lyta_gate_sweep.json')

# --- sweep grid: (consent_threshold, score_threshold) ----------------------
CONS_GRID = [6, 7, 8, 9, 10, 11, 12, 13]
SCORE_GRID = [0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.75, 1.00]

# --- recorded tick series: parse market fields out of the fixed 15-min log ---
RECORDED = '/tmp/circuit_15min.log'


def parse_recorded_ticks(log_path: str) -> list[dict]:
    """Reconstruct tick rows from the fixed-run log (verified against the file)."""
    rows = []
    cur = None
    for line in open(log_path, encoding='utf-8'):
        s = line.strip()
        if not s:
            continue
        m = __import__('re').match(r'\[(\d+:\d+:\d+)\] Tick (\d+) (\S+)', s)
        if m:
            cur = {'time': m.group(1), 'tick': int(m.group(2)), 'token': m.group(3)}
            rows.append(cur)
            continue
        if cur is None:
            continue
        if s.startswith('Market:'):
            mp = __import__('re').match(
                r'Market: (\w+) trend \| ([^\|]+) 24h \| rug ([\d.]+) \| liq ([\d.]+) \| score (\d+)',
                s)
            if mp:
                cur.update(trend=mp.group(1), chg24h=float(mp.group(2).replace('%','')),
                           rug=float(mp.group(3)), liq=float(mp.group(4)),
                           score=int(mp.group(5)))
        elif s.startswith('Signal:'):
            mp = __import__('re').match(r'Signal: ([^\s]+) \(([^)]+)\)', s)
            if mp:
                cur.update(signal=float(mp.group(1)), direction=mp.group(2).lower())
    return rows


# --- synthetic series: seeded repeated snapshots through the REAL bots ----
def make_bot_pool(seed: int, copies: int = 5) -> ConsensusAggregator:
    bots = [VolumeMomentumBot(f'VolumeMomentumBot#{seed}'),
            LiquidityHealthBot(f'LiquidityHealthBot#{seed}'),
            HolderConcentrationBot(f'HolderConcentrationBot#{seed}'),
            VolatilityDiscordBot(f'VolatilityDiscordBot#{seed}'),
            SocialHypeBot(f'SocialHypeBot#{seed}')]
    while len(bots) < CONSENSUS_MIN:
        bots.append(VolumeMomentumBot(f'VolumeMomentumBot#{seed}'))
    return ConsensusAggregator(bots)


def synthetic_series(n_ticks: int, seeds: list[int],
                     vol_mu: float = 3_500_000.0, liq_mu: float = 2_000_000.0) -> list[dict]:
    """Repeated seeded snapshots of a GOBLIN-style pair; feeds the REAL decide()."""
    series = []
    for seed in seeds:
        rng = random.Random(seed)
        for t in range(n_ticks):
            vol = max(0.0, rng.gauss(vol_mu, vol_mu * 0.35))
            liq = max(0.0, rng.gauss(liq_mu, liq_mu * 0.40))
            fee = round(rng.choice([0.0028, 0.003, 0.0042]), 4)
            age = int(rng.choice([3, 12, 58, 140]))
            trend = rng.choice(['up', 'down', 'sideways'])
            pair = {'base': 'GOBLIN', 'quote': 'SOL', 'vol24_usd': round(vol, 0),
                    'liquidity_usd': round(liq, 0), 'fee': fee, 'age_minutes': age,
                    'trend': trend}
            series.append(pair)
    return series


def sweep_series(series: list[dict], tag: str) -> dict:
    """Run every (Ct, St) combination through the gate on one series."""
    out = {'series': tag, 'results': {}}
    cons_counts = Counter()
    score_pairs = []
    for pair in series:
        r = None
        # build votes with real bots, then evaluate the A3b gate at each Ct/St
        votes = [s.decide(pair) for s in agg.sources]
        buys = [v for v in votes if v.kind == 'buy']
        combined, tag_ = GlintNarrativeProxy.score(pair, votes, '')
        for Ct in CONS_GRID:
            for St in SCORE_GRID:
                qualified = (len(buys) >= Ct) and (abs(combined) >= St)
                cons_counts[(Ct, St)] += 1 if qualified else 0
        score_pairs.append((len(buys), combined))
    # summarize
    for Ct in CONS_GRID:
        for St in SCORE_GRID:
            out['results'][f'{Ct}|{St}'] = {
                'count': cons_counts[(Ct, St)], 'share': round(
                    cons_counts[(Ct, St)] / len(series), 4)}
    out['dist'] = {'consent_counts': Counter(c for c, _ in score_pairs),
                   'combined_range': [round(min(s for _, s in score_pairs), 3),
                                      round(max(s for _, s in score_pairs), 3)]}
    return out


if __name__ == '__main__':
    print('=== A3b gate threshold sweep (paper-only) ===')
    # recorded series
    rec = parse_recorded_ticks(RECORDED)
    print(f'Recorded ticks parsed: {len(rec)}  (from {RECORDED})')
    # synthetic series
    syn = synthetic_series(400, seeds=list(range(1, 6)))
    print(f'Synthetic ticks generated: {len(syn)}  (5 seeds x 80)')

    agg = make_bot_pool(seed=0)
    print('Pool bots:', [b.name for b in agg.sources])

    results = {'recorded': sweep_series(rec, 'recorded_15min_loop'), 'synthetic': []}
    per_seed = 400
    for i in range(5):
        agg = make_bot_pool(seed=100 + i)
        chunk = sweep_series(syn[i*per_seed:(i+1)*per_seed], f'synthetic_seed{100+i}')
        results['synthetic'].append(chunk)
    SAVE.write_text(json.dumps(results, indent=1))

    # knife-edge report: share near threshold
    print('\n=== Gate sensitivity (share of ticks qualifying) ===')
    hdr = 'Ct\\St | ' + ' '.join(f'{St:>6}' for St in SCORE_GRID)
    print(hdr)
    for Ct in CONS_GRID:
        row = f'{Ct:>5} | '
        for St in SCORE_GRID:
            row += f'{results["recorded"]["results"][f"{Ct}|{St}"]["share"]:>6.2f} '
        print(row)
    print('\nRecorded distribution: consent buckets =',
          dict(results['recorded']['dist']['consent_counts']))
    print('Recorded combined-score range =',
          results['recorded']['dist']['combined_range'])
    print('\nDone. JSON saved to', SAVE)
