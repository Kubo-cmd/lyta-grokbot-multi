"""Shared paper-only run engine for BOTH Grok-Bot and OpenBot desks.

Both desks now run the SAME engine:

  * the A3b consensus gate  -> apply_a3b_gate(): consent >= 8  AND  |combined| >= 0.35
  * the paper-only capital guard (PAPER_MIN_EQUITY, position cap)
  * the same verbose per-tick stand-down logging with per-bot votes + reasons

The ONLY pluggable parts are:

  * advice source  -> Grok-Bot key-gated committee advisory plug in
                      grokbot_multi.py, OR OpenBot spot/narrative heuristics in
                      paper_run.py. No key needed: when absent the committee
                      stands down (None) and the desk keeps heuristics on paper.
  * execution hook -> each desk's paper buy stays local, the gate/guard/log are
                      shared verbatim.

Every execution path is paper-only: no real order, no real capital.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from consensus_aggregator import GlintNarrativeProxy, Signal

logger = logging.getLogger(__name__)

# -- Shared gate constants ---------------------------------------------------
CONSENSUS_MIN = 8          # A3b: matching BUY votes before we act
SIGNAL_GATE = 0.35         # |combined score| must exceed this
BASE_CHANGE_BUY = 0.015
BASE_CHANGE_SELL = -0.015
PAPER_CAPITAL = 100.0      # paper pool shared across desks
PAPER_MIN_EQUITY = 25.0    # paper guard: stop below this
PAPER_MAX_POSITIONS = 4    # paper guard: cap open positions


def apply_a3b_gate(pair, votes, narrative: str = "") -> dict:
    """Shared A3b consensus gate. Identical logic for both desks.

    ``votes``: flat list of Signal objects.
    Returns dict with keys: signals, consent, combined_score, tag, narrative,
    qualified, decision, base_change. ``qualified`` == True only when
    consent >= CONSENSUS_MIN AND abs(combined_score) >= SIGNAL_GATE.
    """
    buys = [v for v in votes if v.kind == "buy"]
    consent = len(buys)
    combined, tag = GlintNarrativeProxy.score(pair, votes, narrative)
    qualified = (consent >= CONSENSUS_MIN) and (abs(combined) >= SIGNAL_GATE)
    return {
        "signals": votes,
        "consent": consent,
        "combined_score": combined,
        "tag": tag,
        "narrative": narrative,
        "qualified": qualified,
        "decision": "BUY-SIG" if qualified else "standby",
        "base_change": BASE_CHANGE_BUY if qualified else 0.0,
    }


def _to_signal(kind, score, tag="") -> Signal:
    return Signal(kind=kind, score=float(score), tag=str(tag))


class PaperDesk:
    """Shared paper-only runner -- the single engine both desks use.

    Shared state: the A3b gate, the paper-only capital guard, and the same
    verbose per-tick stand-down logging with per-bot votes + reasons.

    Pluggable parts (only these differ between desks):

      * vote source  -> desk bots, mapped to Signal {name: Signal}
      * advice source -> Grok committee advisory plug (grokbot_multi.py) or
                        OpenBot spot/narrative heuristics (paper_run.py); no key
                        needed, stands down when absent, never fabricates a
                        number.
      * execution hook -> desk's local paper buy/exit.

    All execution is paper-only.  Grok-Bot runs the committee advisory; without
    a key the committee stands down (None) and the desk still runs heuristics on
    paper.  OpenBot runs spot/narrative heuristics and no committee.
    """
    def __init__(
        self,
        name: str = "shared",
        capital: float = PAPER_CAPITAL,
        vote_fn: Optional[Callable[[dict], dict]] = None,
        advice_fn: Optional[Callable[[dict, dict], float]] = None,

        execute_fn: Optional[Callable[[dict, str, dict], dict]] = None,
        verbose: bool = True,
    ) -> None:
        self.name = name
        self.capital = float(capital)
        # paper-only equity (never real money)
        self.equity = float(capital)
        self.vote_fn = vote_fn or (lambda pair: {})
        self.advice_fn = advice_fn or (lambda pair, votes: 0.0)
        self.execute_fn = execute_fn or self._default_execute
        self.verbose = verbose
        self.logs: list[str] = []
        self.signals: list[dict] = []
        self.grok_committee_advice: list[float] = []
        self.stand_downs = 0
        self.open_positions: dict[str, dict] = {}
        self.trades: list[dict] = []

    # -- internal ------------------------------------------------------------

    def _log(self, line: str) -> None:
        self.logs.append(line)
        if self.verbose:
            print(f"  [PAPER][{self.name}] {line}")

    def _stand_down(self, pair: dict, symbol: str, gate: dict, advice,
                    reason: str) -> dict:
        self.stand_downs += 1
        self._log(
            f"Stand-down {symbol}: {reason} "
            f"(consent {gate['consent']}/8, score {gate['combined_score']:+.3f})"
        )
        return {
            "symbol": symbol,
            "consent": gate["consent"],
            "gate_passed": False,
            "combined_score": gate["combined_score"],
            "base_change": gate["base_change"],
            "advice": advice,
            "stand_down_reason": reason,
            "executed": False,
            "trade": None,
        }

    def _default_execute(self, pair: dict, direction: str, gate: dict) -> dict:
        size = min(self.capital * 0.01, 5.0)
        side = "BUY" if direction == "buy" else "SELL"
        self._log(
            f"Paper {side} {pair.get('symbol','?')} size={size:.2f} "
            f"consent={gate['consent']}/8 combined={gate['combined_score']:+.3f} "
            f"base_change={gate['base_change']:+.1%}"
        )
        return {
            "symbol": pair.get("symbol"),
            "side": side,
            "size": size,
            "base_change": gate["base_change"],
            "paper_equity_used": size,
            "source": "paper",
            "executed": True,
        }

    def _enough_equity(self) -> bool:
        """Minimum-equity guard (paper-only)."""
        return self.equity > PAPER_MIN_EQUITY

    # -- public API -----------------------------------------------------------

    def run_tick(
        self,
        pair: dict,
        narrative: str = "",
        vote_fn: Optional[Callable[[dict], dict]] = None,
        advice_fn: Optional[Callable[[dict, dict], float]] = None,

        execute_fn: Optional[Callable[[dict, str, dict], dict]] = None,
    ) -> dict:
        """Run one paper-only tick through the shared engine."""
        symbol = str(pair.get("symbol") or pair.get("base") or "unknown")
        vote_fn = vote_fn or self.vote_fn
        advice_fn = advice_fn or self.advice_fn
        execute_fn = execute_fn or self.execute_fn

        votes = vote_fn(pair)
        self.signals = []
        vote_score_sum = 0.0
        for name, sig in votes.items():
            # Accept {name: Signal} OR {name: (kind, score, tag)}.
            if isinstance(sig, Signal):
                kind, score, tag = sig.kind, sig.score, sig.tag
            else:
                kind, score, tag = sig[0], float(sig[1]), (str(sig[2]) if len(sig) > 2 else "")
            sig = Signal(name=name, kind=kind, score=score, tag=tag)
            self._log(f"  vote {name:22} {sig.kind:5} {sig.score:+.3f}")
            self.signals.append({
                "sym": symbol, "name": name, "kind": sig.kind,
                "score": sig.score, "tag": sig.tag,
            })
            vote_score_sum += sig.score
        self._log(f"  votes total: {len(votes)} bots | buy/sell/pass "
                  f"={sum(1 for s in votes.values() if s.kind=='buy')}/"
                  f"{sum(1 for s in votes.values() if s.kind=='sell')}/"
                  f"{sum(1 for s in votes.values() if s.kind=='pass')}")

        advisory = advice_fn(pair, votes) if advice_fn else None
        if advisory is not None:
            self.grok_committee_advice.append(float(advisory))
            self._log(f"  advisory {self.name}: {float(advisory):+.3f}")
            self.signals.append({"sym": symbol, "advisory": float(advisory)})

        gate = apply_a3b_gate(pair, list(votes.values()), narrative)

        if not gate["qualified"]:
            return self._stand_down(pair, symbol, gate, advisory,
                                    "A3b gate not met")

        # paper-only capital guard (identical for both desks)
        if not self._enough_equity():
            return self._stand_down(pair, symbol, gate, advisory,
                                    "paper guard: minimum equity not met")
        if len(self.open_positions) >= PAPER_MAX_POSITIONS:
            return self._stand_down(pair, symbol, gate, advisory,
                                    "paper guard: open-position cap reached")

        direction = "buy" if vote_score_sum >= 0 else "sell"
        trade = execute_fn(pair, direction, gate)
        return {
            "symbol": symbol,
            "consent": gate["consent"],
            "gate_passed": True,
            "combined_score": gate["combined_score"],
            "base_change": gate["base_change"],
            "advice": advisory,
            "stand_down_reason": None,
            "executed": True,
            "trade": trade,
        }
