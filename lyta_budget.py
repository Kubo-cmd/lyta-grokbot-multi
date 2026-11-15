#!/usr/bin/env python3
"""Shared budget discipline for the LYTA system (zero-burn, paper-only).

Implements the book's Chapter-1 "taste and optimize" loop at the system
level: per-layer latency/cost budgets, a compounding-vs-stand-down gate,
and a per-decision ledger. Nothing here places a live order or reads a
real API key. Used by paper_trade_exec.py and extendable to the rest of
the Grok-bot desk (lyta-grok-desk, pumpfun_simulator, etc.).

The budget GATE is the single source of truth: paper_trade_exec.py
delegates to this module, and the `record=True` branch of _apply_budget
owns the ledger + paper-size reaction so every runner behaves identically.

Layout:  BUDGET_* constants -> evaluate_budget() -> _apply_budget() ->
BudgetLedger (runtime|infrastructure|tooling).  A `budget()` context
manager times any instrumented lyta call for reuse across all agents.
"""
from __future__ import annotations

import contextlib
import time
from typing import Dict, Iterable, List, Optional

# ── Book Ch.1 budgets (taste-and-optimize loop) ───────────────────────────
BUDGET_DECISION_LATENCY_S = 0.100      # per-decision budget, downstream layers share this
BUDGET_COST_TOKENS = 6000              # token proxy: inference+tooling per circuit cycle
BUDGET_PNL_PCT = 0.0                   # paper ledger: accepting >= 0% per closed trade
BUDGET_PAPER_SIZE_FLOOR = 0.01            # floor for paper-size halving (SOL-equivalent units)

LAYERS = ("runtime", "infrastructure", "tooling")


class BudgetLedger:
    """Per-layer ledger: latency budget, token cost, cumulative P&L."""

    def __init__(self, latency_budget_s: float = BUDGET_DECISION_LATENCY_S,
                 cost_budget_tokens: int = BUDGET_COST_TOKENS) -> None:
        self.latency_budget_s = latency_budget_s
        self.cost_budget_tokens = cost_budget_tokens
        self.per_layer: Dict[str, float] = {layer: 0.0 for layer in LAYERS}
        self.latency_samples: List[float] = []
        self.cost_samples: List[int] = []
        self.pnl_samples: List[float] = []
        self.decisions = 0

    def add(self, latency_s: float, cost_tokens: int, pnl_pct: Optional[float] = None) -> None:
        """Log one closed decision. Stand-downs/observations are recorded
        without shrinking the account (they only count toward the ledger)."""
        self.decisions += 1
        if pnl_pct is None:
            pnl_pct = 0.0
        self.pnl_samples.append(pnl_pct)
        self.latency_samples.append(latency_s)
        self.cost_samples.append(cost_tokens)
        layer = "runtime"
        self.per_layer[layer] = round(self.per_layer[layer] + latency_s, 6)

    def reset(self) -> None:
        self.per_layer = {layer: 0.0 for layer in LAYERS}
        self.latency_samples = []
        self.cost_samples = []
        self.pnl_samples = []
        self.decisions = 0

    def report(self) -> None:
        avg_lat = (sum(self.latency_samples) / self.decisions) if self.decisions else 0.0
        avg_cost = (sum(self.cost_samples) / self.decisions) if self.decisions else 0.0
        avg_pnl = (sum(self.pnl_samples) / self.decisions) if self.decisions else 0.0
        rows = [f"  [budget ledger] decisions={self.decisions}  "
                f"avg_latency={avg_lat:.6f}s  avg_cost={avg_cost:.0f}t  avg_pnl={avg_pnl:+.3f}%"]
        rows += [f"  [budget ledger] {layer:<14} lat_budget={lat:.3f}s"
                 for layer, lat in self.per_layer.items()]
        print("\n".join(rows))


# Module-level gate ledger: one shared instance (the same 3-layer
# BudgetLedger the paper runner exposes as self.ledger) for any runner that
# records a decision with _apply_budget(record=True). Created at import time
# so BudgetLedger + constants exist first. Nothing here places a live order
# or reads a real API key.
_GATE_LEDGER = BudgetLedger()


def evaluate_budget(latency_s: float, cost_tokens: int,
                    pnl_pct: Optional[float] = None) -> dict:
    """Ch.1 gate: compare each measured number against its budget."""
    latency_ok = latency_s <= BUDGET_DECISION_LATENCY_S
    cost_ok = cost_tokens <= BUDGET_COST_TOKENS
    pnl = pnl_pct if pnl_pct is not None else 0.0
    pnl_ok = pnl >= BUDGET_PNL_PCT
    verdict = ("compounding" if (latency_ok and cost_ok and pnl_ok) else "stand-down")
    return {
        "verdict": verdict,
        "latency_ok": latency_ok,
        "cost_ok": cost_ok,
        "pnl_ok": pnl_ok,
        "latency_s": latency_s,
        "cost_tokens": cost_tokens,
        "pnl_pct": pnl,
    }


def _apply_budget(latency_s: float, cost_tokens: int,
                  pnl_pct: Optional[float], *, record: bool = False,
                  paper_size: float = 0.0) -> tuple[dict, float]:
    """Paper-only taste-and-optimize hook (single source of truth).

    Pure discipline gate:
      record=False  -> gate evaluation only (live stand-downs / no-trade).
      record=True   -> this decision CLOSED a paper position, so (a) log the
                       cycle to the ledger and (b) on a stand-down apply the
                       paper-size reaction (halve, floored by BUDGET_PAPER_SIZE_FLOOR).
    The runner owns console formatting and account state; this hook is
    side-effect-free apart from its ledger + size-reaction return values.
    """
    budget = evaluate_budget(latency_s, cost_tokens, pnl_pct)
    if record:
        # A closed paper trade always counts toward the shared ledger.
        _GATE_LEDGER.add(latency_s, cost_tokens, budget["pnl_pct"])
        # Size reaction: stand-down halves the paper size, floored at
        # BUDGET_PAPER_SIZE_FLOOR so paper trading never goes negative.
        if budget["verdict"] == "stand-down" and paper_size > BUDGET_PAPER_SIZE_FLOOR:
            paper_size = round(max(paper_size / 2.0, BUDGET_PAPER_SIZE_FLOOR), 4)
    return budget, paper_size


@contextlib.contextmanager
def budget(layer: str = "runtime", cost_tokens: int = 0):
    """Times one lyta call; returns (latency_s, cost_tokens). Use it at the
    top of any instrumented agent run."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        latency_s = round(time.perf_counter() - t0, 6)
        # cost_tokens is supplied by the caller on exit (0 in paper mode)
        print(f"  [budget][{layer}] decision latency {latency_s}s, cost proxy {cost_tokens} tokens")
