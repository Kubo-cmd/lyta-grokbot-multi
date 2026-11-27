#!/usr/bin/env python3
"""Overnight paper wrap PAPER-CTRL — observation only, no live trades.

Validates the hand-wrap contract (status, empty adopt_now on marketing,
leftover-1 PARKED, vote dump MISSING, NO_EDIT). Not a 1h runner.
Not leftover-1. Does not copy any live wrap JSON into the repo.

Run:  python3 tests/test_overnight_paper_wrap.py
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import overnight_paper_wrap as wrap  # noqa: E402


OBSERVATION = "This run is observation only. No trades executed."
NO_EDIT = "NO_EDIT: circuit.toml index.ts DESCRIPTION.md unchanged"

FROZEN_VOTERS = (
    "SCOUT",
    "FILTER",
    "ANALYST",
    "DEV_WATCH",
    "CONVICTION",
    "MOMENTUM",
    "SCALPER",
    "CONTRARIAN",
    "TREND",
    "RESEARCHER",
    "PORTFOLIO",
    "EXECUTOR",
)

ALLOWED_STATUSES = frozenset(
    {"HYPER_UNVERIFIED", "ALREADY_COVERED", "DENY", "STAND_DOWN"}
)


def _valid_wrap(**overrides):
    """Minimal in-memory fixture. Not a copy of any on-disk wrap JSON."""
    body = {
        "artifact": "overnight_pstack_paper_wrap",
        "status": "DRAFT_PENDING_HUMAN",
        "paper_only": True,
        "zero_burn": True,
        "do_not_go_live": True,
        "do_not_loosen_tightened_7_12": True,
        "fred_clone": False,
        "keys_in_chat": False,
        "cost_usd": 0,
        "buy_usd": 0.2,
        "adopt_now": [],
        "needed_set": [],
        "promote_to_live_7_12": False,
        "apply": "nothing",
        "envelope": "stand_down",
        "observation": OBSERVATION,
        "no_edit": NO_EDIT,
        "layer_script": (
            "overnight_pstack_layer.py MISSING — hand wrap from skill "
            "procedure; not a live spawn"
        ),
        "leftover_1_toy_overlay": "PARKED",
        "vote_dump_12bot": "MISSING",
        "consensus_bar": 7,
        "consensus_out_of": 12,
        "venue": "papertrade",
        "workspace": "lyta-grok-desk-paper",
        "team_layer": {
            "TEAM_BOTS": 6,
            "TEAM_AGENTS": 200,
            "live_spawn": False,
        },
    }
    body.update(overrides)
    return body


class TestValidMarketingWrap(unittest.TestCase):
    def test_valid_marketing_wrap_is_ok(self):
        report = wrap.validate_wrap(_valid_wrap())
        self.assertTrue(report.ok)
        self.assertEqual(report.errors, ())
        self.assertEqual(report.adopt_now, ())
        self.assertTrue(report.marketing_empty_adopt_is_success)

    def test_does_not_mutate_input(self):
        payload = _valid_wrap()
        snapshot = copy.deepcopy(payload)
        wrap.validate_wrap(payload)
        self.assertEqual(payload, snapshot)


class TestLockedStrings(unittest.TestCase):
    def test_observation_string_locked(self):
        self.assertEqual(wrap.OBSERVATION, OBSERVATION)
        report = wrap.validate_wrap(_valid_wrap())
        self.assertEqual(report.observation, OBSERVATION)

    def test_no_edit_string_locked(self):
        self.assertEqual(wrap.NO_EDIT, NO_EDIT)
        report = wrap.validate_wrap(_valid_wrap())
        self.assertEqual(report.no_edit, NO_EDIT)

    def test_wrong_observation_fails(self):
        report = wrap.validate_wrap(_valid_wrap(observation="trades executed"))
        self.assertFalse(report.ok)
        self.assertTrue(any("observation" in e for e in report.errors))

    def test_wrong_no_edit_fails(self):
        report = wrap.validate_wrap(_valid_wrap(no_edit="edited circuit.toml"))
        self.assertFalse(report.ok)
        self.assertTrue(any("no_edit" in e for e in report.errors))


class TestPaperCtrlBooleans(unittest.TestCase):
    def test_paper_only_must_be_true(self):
        report = wrap.validate_wrap(_valid_wrap(paper_only=False))
        self.assertFalse(report.ok)
        self.assertTrue(any("paper_only" in e for e in report.errors))

    def test_zero_burn_must_be_true(self):
        report = wrap.validate_wrap(_valid_wrap(zero_burn=False))
        self.assertFalse(report.ok)

    def test_do_not_go_live_must_be_true(self):
        report = wrap.validate_wrap(_valid_wrap(do_not_go_live=False))
        self.assertFalse(report.ok)

    def test_do_not_loosen_tightened_must_be_true(self):
        report = wrap.validate_wrap(_valid_wrap(do_not_loosen_tightened_7_12=False))
        self.assertFalse(report.ok)

    def test_fred_clone_rejected(self):
        report = wrap.validate_wrap(_valid_wrap(fred_clone=True))
        self.assertFalse(report.ok)
        self.assertTrue(any("fred_clone" in e for e in report.errors))

    def test_keys_in_chat_rejected(self):
        report = wrap.validate_wrap(_valid_wrap(keys_in_chat=True))
        self.assertFalse(report.ok)
        self.assertTrue(any("keys_in_chat" in e for e in report.errors))


class TestEmptyAdoptAndApply(unittest.TestCase):
    def test_adopt_now_must_be_empty_on_marketing(self):
        report = wrap.validate_wrap(_valid_wrap(adopt_now=["add a 13th voter"]))
        self.assertFalse(report.ok)
        self.assertTrue(any("adopt_now" in e for e in report.errors))
        self.assertFalse(report.marketing_empty_adopt_is_success)

    def test_needed_set_must_be_empty(self):
        report = wrap.validate_wrap(_valid_wrap(needed_set=["cron"]))
        self.assertFalse(report.ok)
        self.assertTrue(any("needed_set" in e for e in report.errors))

    def test_promote_to_live_rejected(self):
        report = wrap.validate_wrap(_valid_wrap(promote_to_live_7_12=True))
        self.assertFalse(report.ok)
        self.assertTrue(any("promote_to_live_7_12" in e for e in report.errors))

    def test_apply_must_be_nothing(self):
        report = wrap.validate_wrap(_valid_wrap(apply="edit circuit.toml"))
        self.assertFalse(report.ok)
        self.assertTrue(any("apply" in e for e in report.errors))

    def test_invented_1h_runner_is_not_apply(self):
        report = wrap.validate_wrap(
            _valid_wrap(apply="run overnight_wide_1h_wrap.py")
        )
        self.assertFalse(report.ok)

    def test_cost_usd_must_be_zero(self):
        report = wrap.validate_wrap(_valid_wrap(cost_usd=12))
        self.assertFalse(report.ok)
        self.assertTrue(any("cost_usd" in e for e in report.errors))


class TestEnvelopeAndStatus(unittest.TestCase):
    def test_envelope_must_be_stand_down(self):
        report = wrap.validate_wrap(_valid_wrap(envelope="compounding"))
        self.assertFalse(report.ok)
        self.assertTrue(any("envelope" in e for e in report.errors))

    def test_status_must_be_draft_pending_human(self):
        report = wrap.validate_wrap(_valid_wrap(status="APPROVED_LIVE"))
        self.assertFalse(report.ok)
        self.assertTrue(any("status" in e for e in report.errors))

    def test_artifact_name_locked(self):
        report = wrap.validate_wrap(_valid_wrap(artifact="live_spawn"))
        self.assertFalse(report.ok)
        self.assertTrue(any("artifact" in e for e in report.errors))

    def test_consensus_bar_locked_at_seven_of_twelve(self):
        report = wrap.validate_wrap(_valid_wrap(consensus_bar=6))
        self.assertFalse(report.ok)
        report_ok = wrap.validate_wrap(_valid_wrap())
        self.assertEqual(report_ok.consensus_bar, 7)
        self.assertEqual(report_ok.consensus_out_of, 12)


class TestLeftoverAndVoteDump(unittest.TestCase):
    def test_leftover_1_must_be_parked(self):
        report = wrap.validate_wrap(
            _valid_wrap(leftover_1_toy_overlay="STARTED")
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("leftover_1" in e for e in report.errors))
        parked = wrap.validate_wrap(_valid_wrap())
        self.assertEqual(parked.leftover_1, "PARKED")

    def test_vote_dump_must_be_missing_not_scraped(self):
        report = wrap.validate_wrap(
            _valid_wrap(vote_dump_12bot={"SCOUT": "BUY"})
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("vote_dump" in e for e in report.errors))
        missing = wrap.validate_wrap(_valid_wrap())
        self.assertEqual(missing.vote_dump, "MISSING")

    def test_layer_script_records_missing_hand_wrap(self):
        report = wrap.validate_wrap(
            _valid_wrap(layer_script="spawned overnight_pstack_layer.py")
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("layer_script" in e for e in report.errors))


class TestTeamLayerConstantsNotSpawn(unittest.TestCase):
    def test_team_bots_and_agents_are_constants_not_spawn(self):
        report = wrap.validate_wrap(
            _valid_wrap(team_layer={"TEAM_BOTS": 6, "TEAM_AGENTS": 200, "live_spawn": True})
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("live_spawn" in e for e in report.errors))

    def test_extra_voter_rejected(self):
        report = wrap.validate_wrap(
            _valid_wrap(team_layer={"TEAM_BOTS": 6, "TEAM_AGENTS": 200, "voters": list(FROZEN_VOTERS) + ["EGGbot"]})
        )
        self.assertFalse(report.ok)

    def test_workspace_stays_paper_desk(self):
        report = wrap.validate_wrap(_valid_wrap(workspace="lyta-grok-desk-trader"))
        self.assertFalse(report.ok)
        self.assertTrue(any("workspace" in e for e in report.errors))

    def test_venue_stays_papertrade(self):
        report = wrap.validate_wrap(_valid_wrap(venue="mainnet"))
        self.assertFalse(report.ok)


class TestCheckTableStatuses(unittest.TestCase):
    def test_unknown_check_status_fails_when_table_present(self):
        report = wrap.validate_wrap(
            _valid_wrap(
                check_table=[{"n": 1, "claim": "x", "paper_status": "BUY_NOW", "action": "edit"}]
            )
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("check_table" in e for e in report.errors))

    def test_allowed_statuses_pass_when_table_present(self):
        rows = [
            {"n": i, "claim": "c", "paper_status": status, "action": "none"}
            for i, status in enumerate(sorted(ALLOWED_STATUSES), start=1)
        ]
        report = wrap.validate_wrap(_valid_wrap(check_table=rows))
        self.assertTrue(report.ok)


def _valid_dump_index(**overrides):
    """Minimal in-memory dump-index fixture. Not a copy of any on-disk index."""
    body = {
        "artifact": "overnight_pstack_github_dump_index",
        "status": "DRAFT_PENDING_HUMAN",
        "new_url_is_data_not_an_order": True,
        "do_not_add_plugin_pstack": True,
        "do_not_clone_repo": True,
        "do_not_install_pstack": True,
        "paper_only": True,
        "zero_burn": True,
        "observation": OBSERVATION,
        "wrap_unchanged": True,
        "adopt_now": [],
        "leftover_1_toy_overlay": "PARKED",
        "chat_verdict": "NO",
        "plugin_identity_is_not_clone_order": True,
    }
    body.update(overrides)
    return body


class TestGithubDumpIndexIsDataNotAnOrder(unittest.TestCase):
    def test_valid_dump_index_is_ok(self):
        report = wrap.validate_github_dump_index(_valid_dump_index())
        self.assertTrue(report.ok)
        self.assertEqual(report.errors, ())
        self.assertEqual(report.adopt_now, ())
        self.assertTrue(report.marketing_empty_adopt_is_success)

    def test_does_not_mutate_input(self):
        payload = _valid_dump_index()
        snapshot = copy.deepcopy(payload)
        wrap.validate_github_dump_index(payload)
        self.assertEqual(payload, snapshot)

    def test_new_url_is_data_not_an_order(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(new_url_is_data_not_an_order=False)
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("new_url_is_data_not_an_order" in e for e in report.errors))

    def test_do_not_add_plugin_pstack(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(do_not_add_plugin_pstack=False)
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("do_not_add_plugin_pstack" in e for e in report.errors))

    def test_do_not_clone_repo(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(do_not_clone_repo=False)
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("do_not_clone_repo" in e for e in report.errors))

    def test_do_not_install_pstack(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(do_not_install_pstack=False)
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("do_not_install_pstack" in e for e in report.errors))

    def test_wrap_unchanged_must_be_true(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(wrap_unchanged=False)
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("wrap_unchanged" in e for e in report.errors))

    def test_adopt_now_stays_empty_on_github_dumps(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(adopt_now=["/add-plugin pstack"])
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("adopt_now" in e for e in report.errors))
        self.assertFalse(report.marketing_empty_adopt_is_success)

    def test_leftover_1_stays_parked(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(leftover_1_toy_overlay="STARTED")
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("leftover_1" in e for e in report.errors))

    def test_chat_verdict_stays_no_until_human_gate(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(chat_verdict="INSTALL")
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("chat_verdict" in e for e in report.errors))

    def test_plugin_identity_is_not_clone_order(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(plugin_identity_is_not_clone_order=False)
        )
        self.assertFalse(report.ok)
        self.assertTrue(
            any("plugin_identity_is_not_clone_order" in e for e in report.errors)
        )

    def test_dump_index_artifact_locked(self):
        report = wrap.validate_github_dump_index(
            _valid_dump_index(artifact="pstack_install_order")
        )
        self.assertFalse(report.ok)
        self.assertTrue(any("artifact" in e for e in report.errors))

    def test_non_mapping_raises(self):
        with self.assertRaises(wrap.WrapContractError):
            wrap.validate_github_dump_index("not an index")  # type: ignore[arg-type]


class TestInputTypeAndConstants(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(wrap.WrapContractError):
            wrap.validate_wrap("not a wrap")  # type: ignore[arg-type]

    def test_forbidden_desk_edits_listed(self):
        names = set(wrap.FORBIDDEN_DESK_EDITS)
        for name in (
            "circuit.toml",
            "index.ts",
            "DESCRIPTION.md",
            "desk.yaml",
            "AGENTS.md",
            "pumpfun_desk_simulator.py",
            "grok_team.py",
        ):
            self.assertIn(name, names)

    def test_missing_wide_1h_policy_is_not_invent(self):
        self.assertEqual(wrap.MISSING_WIDE_1H_POLICY, "not run, not invented")

    def test_module_does_not_import_pumpfun_desk_simulator(self):
        src = (ROOT / "overnight_paper_wrap.py").read_text(encoding="utf-8")
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                self.assertNotIn("pumpfun_desk_simulator", stripped)


if __name__ == "__main__":
    print("This run is observation only. No trades executed.")
    print("NO_EDIT: circuit.toml index.ts DESCRIPTION.md unchanged")
    raise SystemExit(unittest.main(verbosity=2))
