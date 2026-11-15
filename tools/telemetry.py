#!/usr/bin/env python3
"""Zero-burn telemetry for the LYTA paper desk.

Every event is written as newline-delimited JSON to a local file
(<repo>/telemetry/<run_id>.jsonl). Nothing here:

  * touches the network,
  * reads any API key / wallet / secret,
  * places a live order or executes anything,
  * writes outside the repo's telemetry/ directory.

It only observes the paper run: gate verdicts, latency, cost, P&L and
ledger snapshots, so downstream tooling (e.g. tools/make_eval_dataset.py)
can build an automatic evaluation dataset without any extra bookkeeping
by the trader.

Events:
  run_start | decision | stand_down | ledger_snapshot | error | run_end

API (module level, one active run at a time):
    run_id = init_run(tag="...")                      # opens the JSONL
    finish_run(run_id=run_id)                         # closes the JSONL
    record(level, event, **payload)                   # raw append
    decision(pair, latency_s, cost_tokens, pnl_pct, verdict, ...)   # convenience
    stand_down(pair, latency_s, reason=..., **kw)     # convenience
    ledger_snapshot(decisions, avg_latency_s, avg_cost_tokens, avg_pnl_pct, ...)  # convenience
    paper_state(capital, positions, paper_size)       # convenience
    error(exc)                                        # convenience
    trace(name) -> context manager                    # span timer
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")

# Module-level state for the single active run (tests may init/finish
# explicitly; atexit is not relied upon for correctness of output).
_state: Dict[str, Any] = {
    "run_id": None,
    "tag": None,
    "path": None,
    "f": None,
    "start": None,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def _run_id(tag: str) -> str:
    """Deterministic, secret-free run id: 9 hex chars of sha1(tag|now)."""
    salt = f"{tag}|{_now_iso()}"
    return "r-" + hashlib.sha1(salt.encode("utf-8")).hexdigest()[:8]


def _ensure_run() -> None:
    if _state["f"] is not None:
        return
    run_dir = REPO_ROOT / "telemetry"
    run_dir.mkdir(parents=True, exist_ok=True)
    _state["path"] = run_dir / f"{_state['run_id']}.jsonl"
    _state["f"] = open(_state["path"], "a", encoding="utf-8")


def _append(level: str, event: str, **payload: Any) -> None:
    if _state["f"] is None:
        return
    line = {
        "ts": _now_iso(),
        "run_id": _state["run_id"],
        "level": level.upper(),
        "event": event,
        "payload": payload,
    }
    _state["f"].write(json.dumps(line, sort_keys=True) + "\n")
    _state["f"].flush()


# ── public API ──────────────────────────────────────────────────────────────

def init_run(tag: str = "") -> str:
    """Start a new paper run and open its JSONL file. Returns run_id."""
    _state["run_id"] = _run_id(tag or "unknown")
    _state["tag"] = tag or _state["run_id"]
    _state["start"] = _now_iso()
    _state["path"] = REPO_ROOT / "telemetry" / f"{_state['run_id']}.jsonl"
    _state["path"].parent.mkdir(parents=True, exist_ok=True)
    _state["f"] = open(_state["path"], "a", encoding="utf-8")
    _append(
        "INFO",
        "run_start",
        tag=_state["tag"],
        paper_only=True,
        zero_burn=True,
        note="Zero-burn paper-only telemetry (no network, no keys, no live orders).",
    )
    return _state["run_id"]


def finish_run(run_id: Optional[str] = None) -> None:
    """Close the JSONL and record run_end. Safe to call twice."""
    if _state["f"] is None:
        return
    rid = run_id or _state["run_id"]
    _append(
        "INFO",
        "run_end",
        tag=_state["tag"],
        paper_only=True,
        note=f"Finished {rid}; all events above are observation-only paper data.",
    )
    _state["f"].close()
    _state["f"] = None


def record(level: str, event: str, **payload: Any) -> None:
    """Append one free-form event line. level in DEBUG/INFO/WARN/ERROR."""
    _append(level.upper(), event, **payload)


def decision(
    pair: str,
    latency_s: float,
    cost_tokens: int = 0,
    pnl_pct: Optional[float] = None,
    verdict: str = "stand-down",
    decision: Optional[str] = None,
    consent: Optional[int] = None,
    combined_score: Optional[float] = None,
    qualified: bool = False,
    paper_size: float = 0.0,
) -> None:
    """Record one gate decision cycle (paper-only)."""
    _append(
        "INFO",
        "decision",
        pair=pair,
        paper_size=paper_size,
        latency_s=latency_s,
        cost_tokens=cost_tokens,
        pnl_pct=pnl_pct,
        verdict=verdict,
        latency_ok=latency_s <= 0.100,
        cost_ok=cost_tokens <= 6000,
        pnl_ok=(pnl_pct if pnl_pct is not None else 0.0) >= 0.0,
        decision=decision,
        consent=consent,
        combined_score=combined_score,
        qualified=qualified,
    )


def stand_down(
    pair: str,
    latency_s: float,
    reason: str = "stand-down",
    consent: Optional[int] = None,
    combined_score: Optional[float] = None,
    paper_size: float = 0.0,
) -> None:
    """Record a live-scan stand-down (observation only; never shrinks paper)."""
    decision(
        pair=pair,
        latency_s=latency_s,
        cost_tokens=0,
        pnl_pct=None,
        verdict="stand-down",
        decision="STAND_DOWN",
        consent=consent,
        combined_score=combined_score,
        qualified=False,
        paper_size=paper_size,
    )
    _append(
        "WARN",
        "stand_down",
        pair=pair,
        latency_s=latency_s,
        reason=reason,
        consent=consent,
        combined_score=combined_score,
        paper_size=paper_size,
        note="Observation only - account is NOT shrunk (paper-only guard).",
    )


def ledger_snapshot(
    decisions: int,
    avg_latency_s: float,
    avg_cost_tokens: float,
    avg_pnl_pct: float,
    per_layer: Dict[str, float],
) -> None:
    """Snapshot the shared budget ledger (paper-only, observation only)."""
    _append(
        "DEBUG",
        "ledger_snapshot",
        decisions=decisions,
        avg_latency_s=avg_latency_s,
        avg_cost_tokens=avg_cost_tokens,
        avg_pnl_pct=avg_pnl_pct,
        per_layer=per_layer,
        note="Copy of lyta_budget._GATE_LEDGER.report() - observation only.",
    )


def paper_state(capital: float, positions: int, paper_size: float, asset: str = "GOBLIN/SOL") -> None:
    """Paper account state (observation only)."""
    _append(
        "INFO",
        "paper_state",
        asset=asset,
        capital=capital,
        positions=positions,
        paper_size=paper_size,
        note="Paper-only account state - simulated funds, no real capital.",
    )


def error(exc: BaseException) -> None:
    """Record an error line (observation only; no traceback to JSONL)."""
    _append(
        "ERROR",
        "error",
        exc_type=type(exc).__name__,
        exc=str(exc),
    )


class trace:
    """Times one instrumented call; logs a trace span (DEBUG level)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.start_ts = _now_iso()

    def __enter__(self) -> "trace":
        _append("DEBUG", "trace", name=self.name, state="start", ts=self.start_ts)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _append(
            "DEBUG",
            "trace",
            name=self.name,
            state="end",
            ts=_now_iso(),
            duration_s=round(
                (datetime.now(timezone.utc).astimezone().timestamp()
                 - datetime.fromisoformat(self.start_ts).timestamp()), 6
            ),
            error=bool(exc_type),
        )
        if exc_type is not None:
            error(exc)
