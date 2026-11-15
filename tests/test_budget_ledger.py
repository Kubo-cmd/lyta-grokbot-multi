#!/usr/bin/env python3
"""Paper-only unit checks for BudgetLedger + evaluate_budget + _apply_budget.

Zero-burn: no network, no live orders, no Grok-bot calls.
Run: python3 tests/test_budget_ledger.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import paper_trade_exec as p  # noqa: E402
import lyta_budget as _lb  # noqa: E402  (shared system ledger, one source of truth)


def check(name: str, cond: bool) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    print("=== BudgetLedger (shared module) ===")
    led = _lb.BudgetLedger({"runtime": 0.1, "infrastructure": 0.1, "tooling": 0.1})
    led.add(0.000041, 0, 0.498)
    led.add(0.000031, 0, 0.498)
    led.add(0.000050, 0, 0.498)
    check("3 decisions recorded", led.decisions == 3)
    check("avg latency ~4.07e-5", abs(sum(led.latency_samples) / 3 - 4.0666e-5) < 1e-8)
    check("avg cost 0", sum(led.cost_samples) / 3 == 0)
    check("avg pnl +0.498", abs(sum(led.pnl_samples) / 3 - 0.498) < 1e-9)
    led.reset()
    check("reset clears decisions", led.decisions == 0)
    check("reset clears samples", led.latency_samples == [])

    print("=== evaluate_budget (static) ===")
    eb = p.PaperTradeSimulator.evaluate_budget
    within = eb(0.00004, 0, 0.498)
    check("within -> compounding", within["verdict"] == "compounding")
    check("within latency_ok", within["latency_ok"] is True)
    lat = eb(0.200, 0, 0.498)
    check("latency 0.200s -> stand-down", lat["verdict"] == "stand-down" and lat["latency_ok"] is False)
    cost = eb(0.00004, 7000, -0.1)
    check("cost+pnl over -> stand-down", cost["verdict"] == "stand-down")
    check("cost_ok False", cost["cost_ok"] is False)
    check("pnl_ok False", cost["pnl_ok"] is False)
    none_pnl = eb(0.00004, 0, None)
    check("pnl=None treated as 0 -> compounding", none_pnl["verdict"] == "compounding")

    print("=== _apply_budget paper_size (paper-only) ===")
    s = p.PaperTradeSimulator()
    start = s.paper_size
    check("default paper_size > 0.01", start > 0.01)
    # observation-only stand-down must NOT shrink size
    s._apply_budget(0.200, 0, -0.1, record=False)
    check("record=False does not shrink", s.paper_size == start)
    # closed-trade stand-down halves size
    s._apply_budget(0.200, 0, -0.1, record=True)
    check("record=True stand-down halves size", s.paper_size == round(start / 2.0, 4))
    check("ledger recorded 1 closed trade", s.ledger.decisions == 1)

    print("\nAll budget-ledger checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
