#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2b - freeze re-open: filter-sensitivity probe (observation only).
Zero-burn. No trades, no live capital, no live Grok Bot, no exchange writes.

Re-runs the SAME deterministic pump.dev-format pool (24 candidates, frozen
lane-2 evidence) through the verified consensus engine under deliberately
DIFFERENT gate floors, to learn whether the 100% stand-down is structural
(data-level) or an artifact of the floor parameters.

Variants (engine gate knobs only; narrative pass-through fixed to "" as in the
frozen adapter run):
  V0  baseline engine   : CONSENSUS_MIN=8  SIGNAL_GATE=0.35   (frozen evidence)
  V1  loose floor       : CONSENSUS_MIN=7  SIGNAL_GATE=0.25
  V2  looser floor      : CONSENSUS_MIN=6  SIGNAL_GATE=0.20
  V3  tight gate        : CONSENSUS_MIN=8  SIGNAL_GATE=0.50
"""
from __future__ import annotations
import sys
sys.path.insert(0, "/Users/test/projects/lyta-grokbot-multi")

import consensus_aggregator as ca
from consensus_aggregator import ConsensusAggregator
import pumpfun_phase2_adapter_ext_run as adapter

POOL = adapter.pumpfun_candidate_pool()
print(f"FILTER-SENSITIVITY PROBE (observation only, zero-burn): "
      f"{len(POOL)} deterministic pump.dev-format candidates (offline)\n")

VARIANTS = [
    ("V0  baseline engine (frozen evidence)",   8,  0.35),
    ("V1  loose floor",                         7,  0.25),
    ("V2  looser floor",                        6,  0.20),
    ("V3  tight gate",                          8,  0.50),
]


def verdicts_for(cons, gate):
    ca.CONSENSUS_MIN = cons
    ca.SIGNAL_GATE = gate
    agg = ConsensusAggregator(adapter.build_voters())
    out = []
    for p in POOL:
        r = agg.consensus(adapter.to_engine_pair(p), narrative="")
        out.append({
            "name": p["name"],
            "consent": r.get("consent", 0),
            "score": r.get("combined_score", 0.0),
            "tag": r.get("tag", ""),
            "qualified": r.get("qualified", False),
            "decision": r.get("decision", "standby"),
        })
    return out


for label, cons, gate in VARIANTS:
    rows = verdicts_for(cons, gate)
    qualified = [r for r in rows if r["qualified"]]
    stand = [r for r in rows if not r["qualified"]]
    print(f"== {label} ==  CONSENSUS_MIN={cons}, SIGNAL_GATE={gate}")
    print(f"   candidates screened : {len(rows)}   gate_qualified : {len(qualified)}   stand-down: {len(stand)}")
    if stand:
        for r in stand:
            print(f"     stand-down  {r['name']:14} consent={r['consent']}/{cons} score={r['score']:+.3f} tag={r['tag']}")
    if qualified:
        for r in qualified:
            print(f"     >>> qualified {r['name']:14} consent={r['consent']}/{cons} score={r['score']:+.3f} tag={r['tag']}")
    print()
