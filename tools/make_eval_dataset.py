#!/usr/bin/env python3
"""Automatic evaluation dataset creator for the LYTA paper-only desk.

Reads the observation-only telemetry JSONL files written by
tools/telemetry.py (<repo>/telemetry/<run_id>.jsonl) and emits an eval
dataset: one JSONL row per decision window (sliding window over each run's
decisions), plus a manifest with a sha256 hash of the dataset.

Paper-trade rules honored here (from the LYTA Inference-Engineering memo):
  * a window whose decisions contain an explicit stand-down verdict is a
    dead / standstill window -- it is NOT emitted as an eval row;
  * capital, fees, order logic and ledger state are untouched; this tool
    only observes and records.

Zero-burn: nothing here touches the network, reads keys, or places live
orders.  Paper bots run on simulated SOL -- safe for practice.

API:
    out = build_dataset(input_paths, output_dir, window, seed=42)
Outputs:
    output_dir/dataset.jsonl   one JSON object per decision window
    output_dir/manifest.json   schema + run summary + hash of the dataset
Return value (dict):
    schema_version, generated_at, input_files, window, seed,
    total_decisions, runs, total_rows, output, paper_only, zero_burn,
    note, hash
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_DIR = REPO_ROOT / "telemetry"

# Paper-trade guard: a window containing a stand-down verdict is a closed
# window and produces no eval row.
STAND_DOWN_VERDICTS = {"stand-down", "stand_down", "stand down"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def _sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_events(input_paths: List[Path]) -> List[Dict[str, Any]]:
    """Read every valid JSONL record; skip blank and malformed lines.

    The ordering of the source JSONL is preserved (each line is one
    record; real telemetry has unique timestamps, so records are never
    conflated).  Collections nested under the record's "payload" key are
    taken as the decision payload (tests write events with a payload
    wrapper).
    """
    events: List[Dict[str, Any]] = []
    for p in input_paths:
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(rec, dict) and rec.get("event") is not None:
                events.append(rec)
    return events


def _dedupe_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop fully-identical consecutive records (real streams are unique)."""
    out: List[Dict[str, Any]] = []
    for ev in events:
        if not out or out[-1] != ev:
            out.append(ev)
    return out


def _run_order_and_by_run(events: List[Dict[str, Any]]) -> tuple[List[str], Dict[str, List[Dict[str, Any]]]]:
    """Runs sorted by earliest decision time (oldest = rank 0)."""
    by_run: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        rid = str(ev.get("run_id") or "unknown")
        by_run.setdefault(rid, []).append(ev)
    run_order = sorted(by_run.keys(), key=lambda r: next(
        (e["ts"] for e in by_run[r] if e.get("ts")), ""), reverse=False)
    return run_order, by_run


def _mode(values: List[Any]) -> Any:
    """Most frequent value; ties keep first-encountered order."""
    counts: Dict[Any, int] = {}
    order: List[Any] = []
    for v in values:
        if v not in counts:
            counts[v] = 0
            order.append(v)
        counts[v] += 1
    return max(order, key=lambda v: counts[v])


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _build_rows(chunk: List[Dict[str, Any]], window: int) -> List[Dict[str, Any]]:
    """One eval row per sliding window that is not a stand-down window."""
    rows: List[Dict[str, Any]] = []
    n = len(chunk)
    for i in range(n - window + 1):
        window_decisions = chunk[i:i + window]
        # Paper-trade guard: stand-down verdict inside the window -> dead window.
        if any(str(d.get("payload", {}).get("verdict", "")).strip().lower()
               in STAND_DOWN_VERDICTS
               for d in window_decisions):
            continue
        feats = window_decisions[0].get("payload", {})
        pnl_pcts = [_as_float(d.get("payload", {}).get("pnl_pct")) for d in window_decisions]
        latency_s = round(sum(_as_float(d.get("payload", {}).get("latency_s")) for d in window_decisions)
                          / window, 6)
        cost_tokens = sum(_as_float(d.get("payload", {}).get("cost_tokens")) for d in window_decisions)
        verdict = _mode([d.get("payload", {}).get("verdict") for d in window_decisions])
        latency_ok = all(_as_float(d.get("payload", {}).get("latency_s")) <= 0.100
                         for d in window_decisions)
        cost_ok = all(_as_float(d.get("payload", {}).get("cost_tokens")) <= 6000
                      for d in window_decisions)
        pnl_ok = all(p >= 0.0 for p in pnl_pcts)
        decision = _mode([d.get("payload", {}).get("decision") for d in window_decisions])
        consent = sum(_as_float(d.get("payload", {}).get("consent")) for d in window_decisions)
        combined_score = round(sum(_as_float(d.get("payload", {}).get("combined_score"))
                                    for d in window_decisions) / window, 4)
        qualified = all(_is_true(d.get("payload", {}).get("qualified")) for d in window_decisions)
        rows.append({
            "event": "decision",
            "run_id": window_decisions[0].get("run_id"),
            "ts": window_decisions[0].get("ts"),
            "features": {
                "pair": "_".join(sorted({d.get("payload", {}).get("pair", "") for d in window_decisions})),
                "paper_size": max(_as_float(d.get("payload", {}).get("paper_size"), 0.0) for d in window_decisions),
                "latency_s": latency_s,
                "cost_tokens": cost_tokens,
                "pnl_pct": round(sum(pnl_pcts) / window, 4),
                "verdict": verdict,
                "latency_ok": latency_ok,
                "cost_ok": cost_ok,
                "pnl_ok": pnl_ok,
                "decision": decision,
                "consent": consent,
                "combined_score": combined_score,
                "qualified": qualified,
                "success": pnl_ok,
                "closed_trade": all(d.get("payload", {}).get("pnl_pct") is not None for d in window_decisions),
                "window": window,
                "steps": n - window + 1,
                "step": i,
                "run_rank": 0,  # set by caller per run
            },
            "target": {
                "verdict": verdict,
                "success": pnl_ok,
                "closed_trade": all(d.get("payload", {}).get("pnl_pct") is not None for d in window_decisions),
            },
        })
    return rows


def build_dataset(input_paths: List[Path] = None,
                  output_dir: Path = None,
                  window: int = 2,
                  seed: int = 42) -> Dict[str, Any]:
    """Build the paper eval dataset (observation only)."""
    if input_paths is None:
        input_paths = []
    if output_dir is None:
        output_dir = REPO_ROOT / "eval"
    if window < 1:
        raise ValueError("window must be a positive integer >= 1")

    events = _dedupe_events(_load_events([Path(p) for p in input_paths]))
    decisions = [ev for ev in events if ev.get("event") == "decision"]

    run_order, by_run = _run_order_and_by_run(events)
    run_rank = {rid: i for i, rid in enumerate(run_order)}

    all_rows: List[Dict[str, Any]] = []
    for rid in run_order:
        chunk = sorted(by_run[rid], key=lambda d: d.get("ts", ""))
        chunk = [d for d in chunk if d.get("event") == "decision"]
        for row in _build_rows(chunk, window):
            row["features"]["run_rank"] = run_rank[rid]
            all_rows.append(row)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = out_dir / "dataset.jsonl"
    manifest_path = out_dir / "manifest.json"

    dataset_path.write_text(
        json.dumps(all_rows, sort_keys=True) + ("\n" if all_rows else ""),
        encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "generated_at": _now_iso(),
        "input_files": [str(Path(p)) for p in input_paths],
        "window": window,
        "seed": seed,
        "total_decisions": len(decisions),
        "runs": len(run_order),
        "total_rows": len(all_rows),
        "output": str(dataset_path),
        "paper_only": True,
        "zero_burn": True,
        "note": "Paper-only eval dataset: simulated SOL, no real capital, no network.",
        "hash": _sha256_of_text(
            json.dumps(all_rows, sort_keys=True) + ("\n" if all_rows else "")),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")

    return {
        "schema_version": 1,
        "generated_at": manifest["generated_at"],
        "input_files": manifest["input_files"],
        "window": window,
        "seed": seed,
        "total_decisions": manifest["total_decisions"],
        "runs": manifest["runs"],
        "total_rows": manifest["total_rows"],
        "output": str(dataset_path),
        "paper_only": True,
        "zero_burn": True,
        "note": manifest["note"],
        "hash": manifest["hash"],
    }


if __name__ == "__main__":
    # CLI (still observation-only): python3 tools/make_eval_dataset.py <file.jsonl> [out_dir]
    in_paths = [Path(a) for a in sys.argv[1:-1]]
    out_dir = Path(sys.argv[-1])
    result = build_dataset(in_paths, out_dir, window=2, seed=42)
    print(json.dumps(result, indent=2, sort_keys=True))
    print("dataset rows:", result["total_rows"])
