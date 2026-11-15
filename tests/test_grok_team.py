"""Tests for the LYTA Grok Bot team layer (lyta-grok-desk/grok_team.py).

Pure logic + the paper envelope: no live bots, no real money, no API calls.
Runs standalone:  python3 tests/test_grok_team.py   (exit 0)
or under pytest:      pytest tests/test_grok_team.py -v

The module file lives in the hyphenated `lyta-grok-desk` directory; it is
loaded by dotted module name `lyta_grok_desk.grok_team` (hyphen cannot be
used in a plain `import` statement).
"""

import importlib.util
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_MODULE_PATH = REPO_ROOT / "lyta-grok-desk" / "grok_team.py"
_spec = importlib.util.spec_from_file_location(
    "lyta_grok_desk.grok_team", _MODULE_PATH
)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot build spec for {_MODULE_PATH}")
_gt = importlib.util.module_from_spec(_spec)
sys.modules["lyta_grok_desk.grok_team"] = _gt  # dataclasses introspect this during exec
_spec.loader.exec_module(_gt)

from lyta_grok_desk.grok_team import (  # noqa: E402
    DelegationRouter,
    EvidencePacket,
    EvidenceRevoke,
    TeamContext,
    TEAM_BOTS,
    TEAM_AGENTS,
    ROLE_CHIEF_OF_STAFF,
    ROLE_GROK_BOT,
    ROLE_MANAGER_LIQUIDITY,
    ROLE_MANAGER_NARRATIVE,
    ROLE_MANAGER_RUG,
    ROLE_OVERSIGHT,
    ROLE_WORKER_MONITOR,
    ROLE_WORKER_PACKET,
    ROLE_WORKER_PATTERN,
    PAPER_MAX_SIZE,
    PAPER_MIN_SIZE,
)

gt = _gt  # module exposed under dotted name `lyta_grok_desk.grok_team`


class TestRoster:
    def test_team_size_references(self):
        assert TEAM_BOTS == 6
        assert TEAM_AGENTS >= 200

    def test_roster_roles_present(self):
        role_values = {
            getattr(gt, name) for name in dir(gt) if name.startswith("ROLE_")
        }
        for role in (
            ROLE_GROK_BOT, ROLE_CHIEF_OF_STAFF,
            ROLE_MANAGER_NARRATIVE, ROLE_MANAGER_LIQUIDITY, ROLE_MANAGER_RUG,
            ROLE_WORKER_MONITOR, ROLE_WORKER_PATTERN, ROLE_WORKER_PACKET,
            ROLE_OVERSIGHT,
        ):
            assert role in role_values, role


class TestChainOrder:
    def _chain(self):
        router = DelegationRouter()
        return list(router.route(gt.TeamTask("paper observation scan")))

    def test_grok_bot_first(self):
        assert self._chain()[0].role == ROLE_GROK_BOT

    def test_chief_of_staff_holds_budget(self):
        assert self._chain()[1].role == ROLE_CHIEF_OF_STAFF

    def test_managers_before_workers(self):
        names = [s.role for s in self._chain()]
        for m in (ROLE_MANAGER_NARRATIVE, ROLE_MANAGER_LIQUIDITY, ROLE_MANAGER_RUG):
            assert m in names
            assert names.index(m) < names.index(ROLE_WORKER_MONITOR)

    def test_oversight_and_chief_of_staff_at_ends(self):
        names = [s.role for s in self._chain()]
        assert names[-1] == ROLE_CHIEF_OF_STAFF
        assert ROLE_OVERSIGHT in names


class TestEnvelope:
    def test_compliant_within_limits(self):
        router = DelegationRouter(TeamContext(paper_only=True, size=0.5))
        assert router.approve_envelope(size=0.5, pnl_pct=0.498, latency_s=1e-3, cost_tokens=0) == "compounding"

    def test_below_min_stand_down(self):
        router = DelegationRouter(TeamContext(paper_only=True, size=0.05))
        assert router.approve_envelope(size=0.05, pnl_pct=3.0, latency_s=1e-3, cost_tokens=0) == "stand_down"

    def test_above_max_stand_down(self):
        router = DelegationRouter(TeamContext(paper_only=True, size=1.2))
        assert router.approve_envelope(size=1.2, pnl_pct=3.0, latency_s=1e-3, cost_tokens=0) == "stand_down"

    def test_paper_only_sticky(self):
        router = DelegationRouter(TeamContext(paper_only=True))
        assert router.context.paper_only is True

    def test_shared_constants(self):
        assert PAPER_MIN_SIZE == 0.20
        assert PAPER_MAX_SIZE == 0.85


class TestEvidenceAndLintRules:
    def test_revoke_changes_state(self):
        packet = EvidencePacket(kind="screenshot", payload="x" * 10, source="worker_a")
        revoke = EvidenceRevoke(packet=packet, reason="spoof", by=ROLE_OVERSIGHT)
        assert revoke.revoked is True
        assert revoke.packet is packet

    def test_verify_passes_clean_packet(self):
        router = DelegationRouter()
        packet = EvidencePacket(kind="log", payload="launch ok", source="worker_monitor")
        ok, reason = router.verify(packet)
        assert ok is True
        assert "passed" in reason

    def test_verify_revokes_when_lint_rule_fails(self):
        router = DelegationRouter()
        packet = EvidencePacket(kind="screenshot", payload="x", source="worker_a")  # too short
        ok, reason = router.verify(packet, by=ROLE_OVERSIGHT)
        assert ok is False
        assert "revokes" in reason

    def test_verify_passes_brief_test(self):
        router = DelegationRouter()
        packet = EvidencePacket(kind="test", payload="2026-11-15 PASS", source="worker_packet")
        ok, _ = router.verify(packet)
        assert ok is True

    def test_stand_down_when_under_min_price(self):
        router = DelegationRouter(TeamContext(paper_only=True))
        assert router.approve_envelope(size=0.5, pnl_pct=0.0, latency_s=1e-3, cost_tokens=0) == "compounding"
        assert router.approve_envelope(size=0.5, pnl_pct=-0.35, latency_s=1e-3, cost_tokens=0) == "stand_down"
