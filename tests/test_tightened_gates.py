"""Tightened 7/12 paper-desk gates — observation only, no live trades."""

from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_pumpfun_desk_simulator_tightened_constants():
    src = _read("pumpfun_desk_simulator.py")
    assert re.search(r"^MIN_VOTES = 7\b", src, re.M)
    assert re.search(r"^MAX_H1_PUMP = 100\b", src, re.M)
    assert re.search(r"^MIN_LIQ = 50_000\b", src, re.M)
    assert re.search(r"^STOP_LOSS_PCT = 0\.35\b", src, re.M)
    assert re.search(r"^TAKE_PROFIT_PCT = 0\.50\b", src, re.M)


def test_circuit_toml_tightened_keys():
    src = _read("lyta-grok-desk/circuit.toml")
    assert "consensus_bar = { type = \"integer\", default = 7, min = 7, max = 12 }" in src
    assert "stop_loss_pct = { type = \"percentage\", default = 35, min = 35, max = 50 }" in src
    assert "take_profit_pct = { type = \"percentage\", default = 50, min = 50, max = 100 }" in src
    assert "min_liquidity_usd = { type = \"integer\", default = 50000, min = 50000 }" in src
    assert "max_h1_pump_pct = { type = \"integer\", default = 100, min = 50, max = 100 }" in src
    assert "max_leverage = { type = \"integer\", default = 5, min = 1, max = 5 }" in src
    assert "desk_risk_pct = { type = \"percentage\", default = 3, min = 1, max = 3 }" in src
    assert "risk_per_trade = { type = \"percentage\", default = 3, min = 1, max = 3 }" in src
    assert "paper_only = { type = \"boolean\", default = true }" in src


def test_index_ts_consensus_bar_locked():
    src = _read("lyta-grok-desk/index.ts")
    assert "consensusBar = (agent.settings?.consensus_bar as number) ?? 7" in src
    assert "// Tightened 7/12 — do not loosen" in src
    assert "Math.min((agent.settings?.max_leverage as number) ?? 5, 5)" in src


def test_circuit_toml_non_lock_schema_fields():
    """UUID / category / papertrade / align — the four fields circuit check accepted."""
    src = _read("lyta-grok-desk/circuit.toml")
    assert 'category = "experimental"' in src
    assert 'network = "papertrade"' in src
    assert 'align = "rolling"' in src
    match = re.search(r'^agentId = "([^"]+)"', src, re.M)
    assert match, "agentId missing"
    uuid.UUID(match.group(1))


def test_circuit_toml_settings_lock_not_stripped_for_cli():
    """circuit check wants 1-3 settings; freeze keeps the Tightened table."""
    src = _read("lyta-grok-desk/circuit.toml")
    keys = re.findall(r"^([a-z0-9_]+) = \{ type", src, re.M)
    assert len(keys) > 3
    for key in (
        "consensus_bar",
        "stop_loss_pct",
        "take_profit_pct",
        "min_liquidity_usd",
        "max_h1_pump_pct",
        "paper_only",
    ):
        assert key in keys


def test_circuit_settings_dts_lists_tightened_keys():
    src = _read("lyta-grok-desk/circuit-settings.d.ts")
    for key in (
        "consensus_bar",
        "stop_loss_pct",
        "take_profit_pct",
        "min_liquidity_usd",
        "max_h1_pump_pct",
        "paper_only",
        "risk_per_trade",
    ):
        assert key in src


def test_showcase_is_paper_observation_not_openbot_winner():
    src = _read("showcase.html")
    assert "This run is observation only. No trades executed." in src
    assert "7/12" in src
    assert "WINNER: OpenBot" not in src
    assert "paper_only" in src
