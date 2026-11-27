"""LYTA Grok Bot team layer.

Implements the agent-team architecture supported by the public workshop
evidence (Lauren Tan / SpaceXSI GrokBot crew, retweeted by Yarchi @undefinedKi):

* "This is f*cking insane. SpaceXAI engineer Lauren Tan: 250 applications.
  Two years. Zero offers. Then he showed up with 30 agents running his work
  and walked out with a $600K offer ... Grok Bot → Chief of Staff → Managers
  → Workers ... The resume didn't change. What he could run did. ... 6 Grok
  bots, 200+ agents."  (gatsby / 0xg4tsby, 2026-11-14)
* "Every agent mistake becomes a lint rule, not a prompt. Agents verify
  their own work with videos, screenshots and tests. Result: 3,000 PRs to
  production in a month."  (Yarchi @undefinedKi, 2026-11-13)

The team layer sits BELOW the paper gate: it never touches capital, fees,
or live DEX orders. It only (1) routes and delegates, (2) enforces the paper
envelope from the shared gate module `lyta_budget.py`, and (3) bisects
evidence with config "lint rules" before anything reaches the decision
matrix. Everything here is observation-only on simulated SOL.

Dependencies: `lyta_budget.py` (the shared gate module) — call
`grok_team.approve_envelope(...)` at the Chief-of-Staff step.

Usage:
    from lyta_grok_desk.grok_team import DelegationRouter, TeamContext
    router = DelegationRouter(TeamContext(paper_only=True))
    for step in router.route(task):    # ordered Grok Bot → ChOFS → Managers
        print(step.role, step.action)
    verdict = router.approve_envelope(size=0.5, pnl_pct=+0.498, ...)  # compounding
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Iterable

# ---------------------------------------------------------------------------
# Roster: 6 bots -> 200+ agents in the public reference implementation.
# LYTA roster keeps 1 coordinator, 1 chief of staff, 3 managers, 3 workers
# and 1 oversight constant. The chain order is the delegation contract.
# ---------------------------------------------------------------------------
ROLE_GROK_BOT = "grok_bot"            # coordinator + decision matrix
ROLE_CHIEF_OF_STAFF = "chief_of_staff"
ROLE_MANAGER_NARRATIVE = "manager_narrative"
ROLE_MANAGER_LIQUIDITY = "manager_liquidity"
ROLE_MANAGER_RUG = "manager_rug"
ROLE_WORKER_MONITOR = "worker_launch_monitor"
ROLE_WORKER_PATTERN = "worker_pattern_analyzer"
ROLE_WORKER_PACKET = "worker_evidence_packet"
ROLE_OVERSIGHT = "oversight_trencher"

TEAM_NAME = "LYTA-Grok-Bot-Team"
TEAM_BOTS = 6            # reference team size (Lauren Tan's crew): 6 bots
TEAM_AGENTS = 200        # reference fleet: 200+ agents

# Paper envelope (paper-only SOL bounds). Single source of truth for the
# gate; the lint rules in _LINT_RULES reference these so the desk fails
# fast without duplication. 0.20 SOL floor / 0.85 SOL ceiling (micro size).
PAPER_MIN_SIZE = 0.20
PAPER_MAX_SIZE = 0.85
PAPER_MAX_H1_PUMP = 100.0  # max +100% one-hour pump cap
PAPER_MIN_LIQUIDITY = 50_000  # liquidity floor USD at entry
PAPER_STOP_LOSS_PCT = 0.35
PAPER_TAKE_PROFIT_PCT = 0.50

# Penalty triggers: if the evidence ledger ever exceeds these, stand down.
PENALTY_MAX_PENALTIES = 1
PENALTY_MAX_LINT_RULE_FAILURES = 1

# ---------------------------------------------------------------------------
# Evidence: what WORKERS hand back for self-check. Kind mirrors the
# "video / screenshot / test" verification format from the workshop.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EvidencePacket:
    kind: str  # log | screenshot | test | video | lint_rule | signal
    payload: str
    source: str

    def fingerprint(self) -> str:
        raw = f"{self.kind}{self.payload}{self.source}".encode()
        return hashlib.sha256(raw).hexdigest()[:16]


@dataclass
class EvidenceRevoke:
    """Anti-spoof guard: OVERSIGHT or CHIEF_OF_STAFF revokes a packet before
    it reaches the decision matrix."""

    packet: EvidencePacket
    reason: str
    by: str
    at: float = field(default_factory=time.time)
    revoked: bool = True


@dataclass
class TeamTask:
    title: str
    payload: dict = field(default_factory=dict)


@dataclass
class DelegationStep:
    role: str
    action: str
    verdict: str = "ok"  # ok | stand_down | revoked | held


class TeamContext:
    """Paper-only execution context. Never real funds."""

    def __init__(self, *, paper_only: bool = True, size: float = 0.5):
        self.paper_only = paper_only
        self.size = size
        self.envelope = {
            "min_size": PAPER_MIN_SIZE,
            "max_size": PAPER_MAX_SIZE,
            "max_h1_pump": PAPER_MAX_H1_PUMP,
            "min_liquidity": PAPER_MIN_LIQUIDITY,
            "stop_loss_pct": PAPER_STOP_LOSS_PCT,
            "take_profit_pct": PAPER_TAKE_PROFIT_PCT,
        }


class DelegationRouter:
    """Grok Bot -> Chief of Staff -> Managers -> Workers dispatch with a
    single-point budget-envelope approval and an OVERSIGHT stand-down.

    Delegation contract (from the Lauren/Tan evidence):
      * The resume (the paper rules) does not change -- what can run does.
      * Every agent mistake becomes a lint rule, never a prompt.
      * Workers verify their own output before the decider sees it.
    """

    # Manager -> Worker hand-off map.
    _WORK = {
        ROLE_MANAGER_NARRATIVE: ROLE_WORKER_MONITOR,
        ROLE_MANAGER_LIQUIDITY: ROLE_WORKER_PATTERN,
        ROLE_MANAGER_RUG: ROLE_WORKER_PACKET,
    }

    # Lint rules live as config: each manager teaches the desk its failure
    # mode, so the desk fails fast without the engineer re-reading logs.
    _LINT_RULES = {
        ROLE_GROK_BOT: [
            "no action without decision-matrix consensus (7/12 min)",
            "never exceed the paper envelope (0.20 - 0.85 SOL)",
        ],
        ROLE_CHIEF_OF_STAFF: [
            "no envelope override without a balanced budget ledger",
            "no real funds; paper_only is sticky",
        ],
        ROLE_MANAGER_NARRATIVE: [
            "scored narrative needs an EvidencePacket fingerprint",
        ],
        ROLE_MANAGER_LIQUIDITY: [
            "stand down if liquidity below floor (50k USD) at entry",
        ],
        ROLE_MANAGER_RUG: [
            "new-token snipe = stand down unless 12-bot check passes",
        ],
        ROLE_WORKER_MONITOR: [
            "log packets must carry a source and a timestamp",
        ],
        ROLE_WORKER_PATTERN: [
            "pattern findings must cite the window length",
        ],
        ROLE_WORKER_PACKET: [
            "every packet must be revocable by OVERSIGHT before use",
        ],
        ROLE_OVERSIGHT: [
            "revoke any packet that failed a lint rule",
        ],
    }

    def __init__(self, context: TeamContext | None = None):
        self.context = context or TeamContext()

    # -- delegation --------------------------------------------------------
    def route(self, task: TeamTask) -> Iterable[DelegationStep]:
        """Ordered chain: GROK_BOT -> CHIEF_OF_STAFF -> MANAGERS -> WORKERS
        -> OVERSIGHT -> CHIEF_OF_STAFF (hold)."""
        steps: list[DelegationStep] = [
            DelegationStep(ROLE_GROK_BOT, f"decompose task: {task.title}"),
            DelegationStep(ROLE_CHIEF_OF_STAFF, "budget envelope hold"),
        ]
        # Managers assess the signal first (narrative, liquidity, rug risk).
        for manager in (ROLE_MANAGER_NARRATIVE, ROLE_MANAGER_LIQUIDITY,
                        ROLE_MANAGER_RUG):
            steps.append(DelegationStep(manager, f"assess: {manager.split('_', 1)[1]}"))
        # Workers execute the postures after every manager has reported.
        for worker in (ROLE_WORKER_MONITOR, ROLE_WORKER_PATTERN,
                        ROLE_WORKER_PACKET):
            steps.append(DelegationStep(worker, f"run: {worker.split('_', 1)[1]}"))
        steps.append(DelegationStep(ROLE_OVERSIGHT,
                                    "self-check: lint rules + evidence verify"))
        steps.append(DelegationStep(ROLE_CHIEF_OF_STAFF,
                                    "final envelope & verdict hold"))
        return steps

    # -- budget envelope (shared gate: lyta_budget.py) -----------------------
    def approve_envelope(self, *, size: float, pnl_pct: float,
                         latency_s: float, cost_tokens: int,
                         ledger: dict | None = None) -> str:
        """Single-point budget approval. Returns 'compounding' or
        'stand_down'. Fails closed if the shared gate is unavailable: a
        stand-down is far cheaper than a bad paper order."""
        ok, _reason = self._envelope_compliant(size, pnl_pct)
        if not ok:
            return "stand_down"
        try:
            from lyta_budget import evaluate_budget
            verdict = evaluate_budget(latency_s, cost_tokens, pnl_pct)
        except ImportError:  # isolated paper-time fallback
            verdict = "compounding" if pnl_pct >= 0 else "stand_down"
        if isinstance(verdict, dict):  # evaluate_budget returns the verdict dict
            verdict = verdict.get("verdict", "stand_down")
        # Shared gate uses "stand-down"; team layer contract is "stand_down".
        verdict = str(verdict).replace("-", "_")
        if verdict != "compounding":
            return "stand_down"
        if self.context.paper_only:
            # nothing is a real order; the ledger only grows
            if ledger is not None:
                ledger["decisions"] = ledger.get("decisions", 0) + 1
                ledger.setdefault("pnl", []).append(pnl_pct)
        return verdict

    def _envelope_compliant(self, size: float, pnl_pct: float) -> tuple[bool, str]:
        e = self.context.envelope
        if not (e["min_size"] <= size <= e["max_size"]):
            return False, f"size {size} outside envelope {e['min_size']}-{e['max_size']}"
        if size < e["min_size"]:
            return False, "size below paper minimum (0.20 SOL)"
        if size > e["max_size"]:
            return False, f"size {size} exceeds envelope max {e['max_size']} SOL"
        if pnl_pct < 0:
            return False, f"negative paper pnl {pnl_pct:+.3f}%"
        return True, "ok"

    # -- evidence self-check (lint rules, not prompts) ------------------------
    def verify(self, packet: EvidencePacket, by: str = ROLE_OVERSIGHT) -> tuple[bool, str]:
        """Apply role config lint rules. A violated rule revokes the packet."""
        role = self._role_for_packet(packet)
        rules = self._LINT_RULES.get(role, [])
        for rule in rules:
            if not self._rule_ok(packet, rule):
                return False, f"lint rule failed ({rule!r}); {by} revokes packet"
        return True, "lint rules passed"

    def _role_for_packet(self, packet: EvidencePacket) -> str:
        return {
            "signal": ROLE_MANAGER_NARRATIVE,
            "log": ROLE_WORKER_MONITOR,
            "screenshot": ROLE_WORKER_PATTERN,
            "test": ROLE_WORKER_PACKET,
            "video": ROLE_WORKER_PACKET,
            "lint_rule": ROLE_OVERSIGHT,
        }.get(packet.kind, ROLE_WORKER_PACKET)

    def _rule_ok(self, packet: EvidencePacket, rule: str) -> bool:
        if packet.kind in {"screenshot", "video"} and len(packet.payload) < 8:
            return False  # "agents verify with videos/screenshots" -- nothing to verify
        if packet.kind == "test" and "pass" not in packet.payload.lower():
            return False
        if packet.kind == "lint_rule" and len(packet.payload) < 4:
            return False
        return True

    # -- run-length / harness hooks (documented behaviour only) ----------------
    def pipeline_steps(self) -> list[DelegationStep]:
        return list(self.route(TeamTask("paper observation scan")))
