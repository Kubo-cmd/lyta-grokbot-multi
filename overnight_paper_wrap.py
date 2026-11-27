#!/usr/bin/env python3
"""PAPER-CTRL validator for overnight pstack paper wraps.

Observation only. No live trades, no 1h runner, no leftover-1 start.
Does not import pumpfun_desk_simulator. TEAM_BOTS / TEAM_AGENTS here are
reference constants, not a live spawn.

Contract source: overnight-pstack-paper hand-wrap fields. A marketing wrap
with empty adopt_now is success. Missing overnight_wide_1h_wrap.py is
not a license to invent a spawn.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Tuple

OBSERVATION = "This run is observation only. No trades executed."
NO_EDIT = "NO_EDIT: circuit.toml index.ts DESCRIPTION.md unchanged"

ARTIFACT = "overnight_pstack_paper_wrap"
GITHUB_DUMP_ARTIFACT = "overnight_pstack_github_dump_index"
STATUS_DRAFT = "DRAFT_PENDING_HUMAN"
ENVELOPE_STAND_DOWN = "stand_down"
APPLY_NOTHING = "nothing"
LEFTOVER_1_PARKED = "PARKED"
VOTE_DUMP_MISSING = "MISSING"
CHAT_VERDICT_NO = "NO"
WORKSPACE_PAPER = "lyta-grok-desk-paper"
VENUE_PAPERTRADE = "papertrade"
CONSENSUS_BAR = 7
CONSENSUS_OUT_OF = 12
TEAM_BOTS = 6
TEAM_AGENTS = 200
MISSING_WIDE_1H_POLICY = "not run, not invented"

FORBIDDEN_DESK_EDITS: Tuple[str, ...] = (
    "circuit.toml",
    "index.ts",
    "DESCRIPTION.md",
    "desk.yaml",
    "AGENTS.md",
    "pumpfun_desk_simulator.py",
    "grok_team.py",
)

FROZEN_VOTERS = frozenset(
    {
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
    }
)

ALLOWED_CHECK_STATUSES = frozenset(
    {"HYPER_UNVERIFIED", "ALREADY_COVERED", "DENY", "STAND_DOWN"}
)

_TRUE_FLAGS = (
    "paper_only",
    "zero_burn",
    "do_not_go_live",
    "do_not_loosen_tightened_7_12",
)
_FALSE_FLAGS = ("fred_clone", "keys_in_chat", "promote_to_live_7_12")
_DUMP_TRUE_FLAGS = (
    "new_url_is_data_not_an_order",
    "do_not_add_plugin_pstack",
    "do_not_clone_repo",
    "do_not_install_pstack",
    "paper_only",
    "zero_burn",
    "wrap_unchanged",
    "plugin_identity_is_not_clone_order",
)


class WrapContractError(TypeError):
    """Wrap payload is not a mapping."""


@dataclass(frozen=True)
class WrapReport:
    ok: bool
    errors: Tuple[str, ...]
    adopt_now: Tuple[Any, ...]
    marketing_empty_adopt_is_success: bool
    observation: str
    no_edit: str
    consensus_bar: Any
    consensus_out_of: Any
    leftover_1: Any
    vote_dump: Any


def _as_tuple(value: Any) -> Tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def _require_true(payload: Mapping[str, Any], key: str, errors: list[str]) -> None:
    if payload.get(key) is not True:
        errors.append(f"{key} must be True")


def _require_false(payload: Mapping[str, Any], key: str, errors: list[str]) -> None:
    if payload.get(key) is not False:
        errors.append(f"{key} must be False")


def _require_equal(
    payload: Mapping[str, Any], key: str, expected: Any, errors: list[str]
) -> None:
    if payload.get(key) != expected:
        errors.append(f"{key} must be {expected!r}")


def _empty_sequence(payload: Mapping[str, Any], key: str, errors: list[str]) -> None:
    value = payload.get(key, [])
    if not isinstance(value, (list, tuple)) or len(value) != 0:
        errors.append(f"{key} must be empty")


def _validate_layer_script(script: Any, errors: list[str]) -> None:
    text = script if isinstance(script, str) else ""
    lowered = text.lower()
    if "MISSING" not in text or "hand wrap" not in lowered or "not a live spawn" not in lowered:
        errors.append(
            "layer_script must record MISSING hand wrap; not a live spawn"
        )


def _validate_team_layer(team: Any, errors: list[str]) -> None:
    if not isinstance(team, Mapping):
        errors.append("team_layer must be a mapping")
        return
    if "TEAM_BOTS" in team and team["TEAM_BOTS"] != TEAM_BOTS:
        errors.append("TEAM_BOTS must stay 6 (constant, not a spawn)")
    if "TEAM_AGENTS" in team and team["TEAM_AGENTS"] != TEAM_AGENTS:
        errors.append("TEAM_AGENTS must stay 200 (constant, not a spawn)")
    if team.get("live_spawn") is True:
        errors.append("live_spawn is forbidden; TEAM_BOTS/TEAM_AGENTS are constants")
    voters = team.get("voters")
    if voters is None:
        return
    if not isinstance(voters, Iterable) or isinstance(voters, (str, bytes)):
        errors.append("team_layer voters must be a sequence of names")
        return
    extra = [name for name in voters if name not in FROZEN_VOTERS]
    if extra:
        errors.append(f"extra voter rejected: {extra!r}")


def _validate_check_table(table: Any, errors: list[str]) -> None:
    if table is None:
        return
    if not isinstance(table, (list, tuple)):
        errors.append("check_table must be a list of rows")
        return
    for row in table:
        if not isinstance(row, Mapping):
            errors.append("check_table row must be a mapping")
            continue
        status = row.get("paper_status")
        if status not in ALLOWED_CHECK_STATUSES:
            errors.append(f"check_table paper_status {status!r} is not allowed")


def validate_wrap(payload: Any) -> WrapReport:
    """Return a frozen report. Never mutates payload. Never places an order."""
    if not isinstance(payload, Mapping):
        raise WrapContractError("wrap payload must be a mapping")

    errors: list[str] = []

    _require_equal(payload, "artifact", ARTIFACT, errors)
    _require_equal(payload, "status", STATUS_DRAFT, errors)
    for key in _TRUE_FLAGS:
        _require_true(payload, key, errors)
    for key in _FALSE_FLAGS:
        _require_false(payload, key, errors)
    _require_equal(payload, "observation", OBSERVATION, errors)
    _require_equal(payload, "no_edit", NO_EDIT, errors)
    _require_equal(payload, "apply", APPLY_NOTHING, errors)
    _require_equal(payload, "envelope", ENVELOPE_STAND_DOWN, errors)
    _require_equal(payload, "leftover_1_toy_overlay", LEFTOVER_1_PARKED, errors)
    _require_equal(payload, "vote_dump_12bot", VOTE_DUMP_MISSING, errors)
    _require_equal(payload, "consensus_bar", CONSENSUS_BAR, errors)
    _require_equal(payload, "consensus_out_of", CONSENSUS_OUT_OF, errors)
    _require_equal(payload, "workspace", WORKSPACE_PAPER, errors)
    _require_equal(payload, "venue", VENUE_PAPERTRADE, errors)
    _require_equal(payload, "cost_usd", 0, errors)
    _empty_sequence(payload, "adopt_now", errors)
    _empty_sequence(payload, "needed_set", errors)
    _validate_layer_script(payload.get("layer_script"), errors)
    _validate_team_layer(payload.get("team_layer"), errors)
    _validate_check_table(payload.get("check_table"), errors)

    adopt = _as_tuple(payload.get("adopt_now", ()))
    leftover = payload.get("leftover_1_toy_overlay")
    vote_dump = payload.get("vote_dump_12bot")

    return WrapReport(
        ok=not errors,
        errors=tuple(errors),
        adopt_now=adopt,
        marketing_empty_adopt_is_success=len(adopt) == 0,
        observation=payload.get("observation", ""),
        no_edit=payload.get("no_edit", ""),
        consensus_bar=payload.get("consensus_bar"),
        consensus_out_of=payload.get("consensus_out_of"),
        leftover_1=leftover,
        vote_dump=vote_dump,
    )


def validate_github_dump_index(payload: Any) -> WrapReport:
    """GitHub dump is data, not an install/clone order. Never mutates payload."""
    if not isinstance(payload, Mapping):
        raise WrapContractError("github dump index must be a mapping")

    errors: list[str] = []

    _require_equal(payload, "artifact", GITHUB_DUMP_ARTIFACT, errors)
    _require_equal(payload, "status", STATUS_DRAFT, errors)
    for key in _DUMP_TRUE_FLAGS:
        _require_true(payload, key, errors)
    _require_equal(payload, "observation", OBSERVATION, errors)
    _require_equal(payload, "leftover_1_toy_overlay", LEFTOVER_1_PARKED, errors)
    _require_equal(payload, "chat_verdict", CHAT_VERDICT_NO, errors)
    _empty_sequence(payload, "adopt_now", errors)

    adopt = _as_tuple(payload.get("adopt_now", ()))
    leftover = payload.get("leftover_1_toy_overlay")

    return WrapReport(
        ok=not errors,
        errors=tuple(errors),
        adopt_now=adopt,
        marketing_empty_adopt_is_success=len(adopt) == 0,
        observation=payload.get("observation", ""),
        no_edit=payload.get("no_edit", ""),
        consensus_bar=payload.get("consensus_bar"),
        consensus_out_of=payload.get("consensus_out_of"),
        leftover_1=leftover,
        vote_dump=payload.get("vote_dump_12bot"),
    )
