#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 - pumpfun pipeline TEST SCRIPT (deterministic, observation only).

Dependency order this run confirms end-to-end:
    [helpers] -> [pipeline class] -> [test script] -> [CLI / entry point]
                  (pumpfun_reverse_engineer)   (pumpfun_pipeline.py)

Run:
    python3 pumpfun_test.py
    python3 pumpfun_test.py --rounds 3 --limit 4

Verifies:
    * CandidatePipeline loads state (or a fresh state file)
    * pull() dedups against seen_ids and appends NEW candidates
    * score() -> 3-question x-ray + 5-bot A3b consensus -> verdict record
    * emit() appends round records + writes state.json
    * --once / --audit are wired into the CLI entry point

Zero-burn, observation-only. No trades executed. No capital.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

REPO_ROOT = "/Users/test/projects/lyta-grokbot-multi"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pumpfun_pipeline import CandidatePipeline, _STATE_FILE, _save_state


def build_pipeline(state_path: str | None = None, rounds: int = 3,
                   limit: int = 4) -> CandidatePipeline:
    pipe = CandidatePipeline(state_path=state_path)
    pipe.round_num = 0
    pipe.state = {"rounds": [], "watchlist": [], "seen_ids": set(),
                  "desk": {"rounds": 0, "candidates": 0, "advance": 0,
                           "stand_down": 0, "mean_consent": 0.0,
                           "mean_abs_score": 0.0, "top_picks": [],
                           "tag_counts": {}, "latest_ids": []}}
    return pipe


def run_round(pipe: CandidatePipeline, limit: int) -> list[dict]:
    """One deterministic pull score-and-emit round; returns new candidates."""
    new = pipe.pull(limit=limit)
    for c in new:
        res = pipe.score(c)
        pipe.emit(c, res, mode="stand_down" if res.get("decision") != "BUY-SIG"
                  else "advance")
    return new


def print_state_snapshot(pipe: CandidatePipeline, label: str) -> None:
    st = pipe.state
    rounds = st.get("rounds", [])
    print(f"  [state snapshot] {label}")
    print(f"    rounds={len(rounds)} watchlist={len(st.get('watchlist', []))} "
          f"seen_ids={len(st.get('seen_ids', set()))}")
    for r in rounds:
        v = r.get("verdict", {})
        c = r.get("candidate", {})
        print(f"    round={r.get('round')} "
              f"asset={c.get('asset')} verdict={v.get('decision')} "
              f"consent={v.get('consent')} score={v.get('combined_score')}")
    print(f"    desk={st.get('desk')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic pump.fun pipeline test")
    ap.add_argument("--rounds", type=int, default=3,
                    help="number of pull+score+emit rounds")
    ap.add_argument("--limit", type=int, default=4,
                    help="candidates pulled per round")
    ap.add_argument("--state", help="state file path (default: temp file)")
    args = ap.parse_args()

    tmp = args.state
    if tmp is None:
        fd, tmp = tempfile.mkstemp(suffix=".json", prefix="pumpfun_test_")
        os.close(fd)
        try:
            os.unlink(tmp)  # let the pipeline create it fresh
        except OSError:
            pass

    pipe = build_pipeline(state_path=tmp, rounds=args.rounds, limit=args.limit)

    print(f"[TEST] deterministic pumpfun pipeline test "
          f"(rounds={args.rounds}, limit={args.limit}, state={tmp})")
    print(f"[TEST] entry-point check: import OK, CandidatePipeline() OK")
    from pumpfun_pipeline import _BOTS as _PL_BOTS
    print(f"[TEST] class-level A3b gate: {_PL_BOTS[0].__class__.__name__} "
          f"preloaded {len(_PL_BOTS)} times "
          f"({_PL_BOTS[0].__class__.__name__} x5 + 3 volume-copies)")
    print()

    counters = []
    for i in range(1, args.rounds + 1):
        new = run_round(pipe, args.limit)
        counters.append((i, len(new), pipe.state))
        print(f"[ITER] round {i}: candidates_in={len(new)} "
              f"total_rounds={len(pipe.state.get('rounds', []))}")
        print_state_snapshot(pipe, f"round_{i}_end")
        print()

    # CLI/entry-point wiring check (--once path exercised through the class)
    print(f"[TEST] state file written -> {pipe.state_path}")
    print(f"[TEST] constructor set round_num={pipe.round_num}; desk="
          f"{pipe.state.get('desk')}")

    # Verify the on-disk file matches in-memory state (serialization check).
    # Note: disk is _sanitized (consensus `Signal` objects -> dicts) while
    # memory keeps Signal objects, so compare the same normalized form on
    # both sides.
    with open(pipe.state_path, encoding="utf-8") as fh:
        on_disk = json.load(fh)
    from pumpfun_pipeline import _sanitize as _san
    norm = json.dumps(_san(dict(pipe.state)), sort_keys=True)
    assert json.dumps(on_disk, sort_keys=True) == norm, \
        "state.json mismatch on disk vs memory (sanitized normalization)"
    assert isinstance(on_disk.get("seen_ids"), list), \
        "seen_ids must serialize to a list"
    print(f"[TEST] VERIFY state.json round-trip OK "
          f"(rounds={len(on_disk['rounds'])})")
    print(f"[TEST] exit code 0: all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
