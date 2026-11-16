#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phase2_local_simulator.py
=========================
Phase 2 paper-window simulator — observation only, zero-burn.

Everything here is local, deterministic, and read-only:
  * read-only, frozen 60-candidate pump.dev-format pool (frozen adapter spec
    pumpfun_phase2_adapter_ext_run.py, commit 084334d freeze-locked);
  * verified multi-bot consensus engine (consensus_aggregator.py) under the
    verified fixed engine gate:
        qualified <=> (buy votes >= CONSENSUS_MIN) AND (|combined_score| >= SIGNAL_GATE)
        green narrative clears the liquidity tag;
        non-green narrative with liq < vol*2 carries hidden_liquidity x0.5 tag;
  * derived filter variants, reproduced from the frozen round-12 paper log:
        V0  baseline engine (frozen evidence)   CONSENSUS_MIN=8  SIGNAL_GATE=0.35
        V1  loose floor                         CONSENSUS_MIN=7  SIGNAL_GATE=0.25
        V2  looser floor                        CONSENSUS_MIN=6  SIGNAL_GATE=0.20   <- derived floor
        V3  tight gate                          CONSENSUS_MIN=8  SIGNAL_GATE=0.50
  * per-position verbose log per candidate: consent (yes votes),
    combined score, verdict, stand-down reason, risk tag.

Run
===
  python3 phase2_local_simulator.py --probe         # full 4-section probe log
  python3 phase2_local_simulator.py --v0            # frozen baseline section
  python3 phase2_local_simulator.py --v2            # derived loose-floor paper log
  python3 phase2_local_simulator.py --v1 --v3       # combined sections
  python3 phase2_local_simulator.py --json          # JSON summary of V2 verdicts
  python3 phase2_local_simulator.py --probe --out round12_v2_20261115.log
                                                  # byte-check against frozen log

No git changes, no live data, no trades, no capital, no exchange writes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys

HERE = "/Users/test/projects/lyta-grokbot-multi"
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# --- frozen adapter spec (read-only pool + engine wiring) -------------------
def load_frozen_adapter(adapter_path: str):
    """Load the freeze-locked adapter module from disk (read-only overlay)."""
    spec = importlib.util.spec_from_file_location("frozen_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load adapter spec: {adapter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ADAPTER = load_frozen_adapter(HERE + "/pumpfun_phase2_adapter_ext_run.py")
POOL = _ADAPTER.pumpfun_candidate_pool()          # frozen 60-candidate pool
_VOTERS = _ADAPTER.build_voters()                 # frozen 5-voter + 3 clone wiring

import consensus_aggregator as agg_mod
from consensus_aggregator import ConsensusAggregator


def engine_path(p):
    """Exact call path of the frozen round-12 probe log."""
    return _ADAPTER.to_engine_pair(p)


# ---- variant floors (engine gate knobs, identical to probe generator) -----
VARIANTS = [
    ("V0  baseline engine (frozen evidence)", 8, 0.35),
    ("V1  loose floor",                        7, 0.25),
    ("V2  looser floor",                       6, 0.20),
    ("V3  tight gate",                         8, 0.50),
]


def verdicts_for(cons, gate):
    """Deterministic per-candidate verdicts under one gate floor."""
    agg_mod.CONSENSUS_MIN = cons
    agg_mod.SIGNAL_GATE = gate
    agg = ConsensusAggregator(_VOTERS)
    rows = []
    for p in POOL:
        r = agg.consensus(engine_path(p), narrative="")
        rows.append({
            "name": p["name"],
            "consent": int(r.get("consent", 0) or 0),
            "score": float(r.get("combined_score", 0.0) or 0.0),
            "tag": r.get("tag", ""),
            "qualified": bool(r.get("qualified", False)),
            "decision": r.get("decision", "standby"),
        })
    return rows


def section(label, cons, gate, rows):
    qualified = [r for r in rows if r["qualified"]]
    stand = [r for r in rows if not r["qualified"]]
    lines = [
        f"== {label} ==  CONSENSUS_MIN={cons}, SIGNAL_GATE={gate}",
        f"   candidates screened : {len(rows)}   gate_qualified : {len(qualified)}   stand-down: {len(stand)}",
    ]
    if stand:
        lines += [f"     stand-down  {r['name']:14} consent={r['consent']}/{cons} score={r['score']:+.3f} tag={r['tag']}" for r in stand]
    if qualified:
        lines += [f"     >>> qualified {r['name']:14} consent={r['consent']}/{cons} score={r['score']:+.3f} tag={r['tag']}" for r in qualified]
    return lines


def run_probe():
    """Full frozen round-12 probe log, byte-for-byte identical format."""
    out = [f"FILTER-SENSITIVITY PROBE (observation only, zero-burn): {len(POOL)} deterministic pump.dev-format candidates (offline)", ""]
    for label, cons, gate in VARIANTS:
        out += section(label, cons, gate, verdicts_for(cons, gate))
        out.append("")
    return out


def build_parser():
    p = argparse.ArgumentParser(prog="phase2_local_simulator.py",
                                description="Phase 2 paper-window simulator (observation only, zero-burn)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--v0", action="store_true", help="frozen baseline evidence section (8/0.35)")
    g.add_argument("--v1", action="store_true", help="loose floor section (7/0.25)")
    g.add_argument("--v2", action="store_true", help="derived loose-floor paper log (6/0.20)")
    g.add_argument("--v3", action="store_true", help="tight gate section (8/0.50)")
    g.add_argument("--probe", action="store_true", help="full frozen round-12 probe log (V0+V1+V2+V3 sections)")
    g.add_argument("--json", action="store_true", help="JSON summary (V2 verdicts) for the desk")
    p.add_argument("--pool", type=int, default=None, help="candidate pool index (unused: frozen pool kept read-only)")
    p.add_argument("--out", metavar="PATH", help="write the probe log to PATH")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.json:
        rows = verdicts_for(6, 0.20)
        doc = {
            "run": "phase2_local_simulator.py --json",
            "note": "observation only, zero-burn; no trades, no live capital, no exchange writes",
            "pool": f"{len(POOL)} deterministic pump.dev-format candidates (frozen adapter pool)",
            "floor": "V2 derived: CONSENSUS_MIN=6, SIGNAL_GATE=0.20",
            "engine": "ConsensusAggregator (5 bots + 3 volume-momentum clones), "
                      "qualified <=> (consent >= CONSENSUS_MIN) AND (|combined_score| >= SIGNAL_GATE)",
            "verdicts": [
                {
                    "name": r["name"],
                    "consent": r["consent"],
                    "consent_floor": 6,
                    "score": r["score"],
                    "signal_gate": 0.20,
                    "qualified": r["qualified"],
                    "tag": r["tag"],
                    "decision": r["decision"],
                } for r in rows
            ],
        }
        print(json.dumps(doc, indent=2))
        return 0

    if args.probe:
        text = "\n".join(run_probe())
        if args.out:
            with open(args.out, "w") as fh:
                fh.write(text)
        print(text)
        return 0

    if args.v2:
        for line in section("V2  looser floor", 6, 0.20, verdicts_for(6, 0.20)):
            print(line)
        return 0

    if args.v0:
        for line in section("V0  baseline engine (frozen evidence)", 8, 0.35, verdicts_for(8, 0.35)):
            print(line)
        return 0

    if args.v1:
        for line in section("V1  loose floor", 7, 0.25, verdicts_for(7, 0.25)):
            print(line)
        return 0

    if args.v3:
        for line in section("V3  tight gate", 8, 0.50, verdicts_for(8, 0.50)):
            print(line)
        return 0

    build_parser().print_help()
    return 0


if __name__ == "__main__":
    main()
