# 📖 Documentation Index

This workspace contains the **groc bot trading desk** — a paper-only
trading desk built on OpenBot (local agent execution) + Grok Bot (server router)
+ Circuit Papertrade SDK. **Paper-only. No live capital.**

## 📋 Core Documentation

| Document | Purpose |
|----------|---------|
| [`PAPER_COMPLETE.md`](PAPER_COMPLETE.md) | Paper run status, frozen rules, v3 evidence log |
| [`STRATEGY_FINALIZE.md`](STRATEGY_FINALIZE.md) | The "bet" document — entry/exit strategy spec |
| [`MULTI_VERSION_REPORT.md`](MULTI_VERSION_REPORT.md) | Version comparison (v2/v3/v9/v10) |
| [`comparison_showcase.md`](comparison_showcase.md) | Comparison framework showcase |

## 🤖 Agent Documentation

| Document | Purpose |
|----------|---------|
| [`lyta-grok-desk/AGENTS.md`](lyta-grok-desk/AGENTS.md) | 10 OpenBot agent workspace overview |
| [`lyta-grok-desk/circuit.toml`](lyta-grok-desk/circuit.toml) | Circuit papertrade config + agent definitions |
| [`lyta-grok-desk/BOT-COMPARE.md`](lyta-grok-desk/BOT-COMPARE.md) | OpenBot vs Grok Bot yes/no contrast |
| [`lyta-grok-desk/DESCRIPTION.md`](lyta-grok-desk/DESCRIPTION.md) | Agent workspace description |

## 🛠️ Scripts

| Script | Purpose |
|--------|---------|
| [`paper_desk_simulator.py`](paper_desk_simulator.py) | Circuit paper simulator (80-iteration regression) |
| [`paper_desk_simulator.py`](paper_desk_simulator.py) | Paper trading simulator (10-agent spot) |
| [`test_paper_desk_simulator.py`](test_paper_desk_simulator.py) | Module resolution test |
| [`scripts/multi_version_runner.py`](scripts/multi_version_runner.py) | Multi-version comparison runner |
| [`scripts/reward_tracker.py`](scripts/reward_tracker.py) | Agent performance reward tracker |

## 📦 Configuration

| File | Purpose |
|------|---------|
| [`config/bot_versions_config.json`](config/bot_versions_config.json) | v2/v3/v9/v10 tightener configs |
| [`config/your_run_config.json`](config/your_run_config.json) | Current run configuration |
| [`lyta-grok-desk/tsconfig.json`](lyta-grok-desk/tsconfig.json) | TypeScript build config |

## 🎯 Version Selector

| Version | Description | Config |
|---------|-------------|--------|
| `v10_tuned` | Tighter stops, better trails, higher conviction | `PO_STOP_LOSS=0.82, PO_TRAIL=3.0, PO_MIN_BUYS=4, PO_MAX_POOL_FEE=0.04, PO_POSITION_MULT=1.2, PO_ENTRY_MAX=72` |
| `v9` | Previous version (historical) | `PO_STOP_LOSS=0.82, PO_TRAIL=3.0, PO_MIN_BUYS=4, PO_MAX_POOL_FEE=0.04, PO_POSITION_MULT=1.2, PO_ENTRY_MAX=72` |
| `v2` | Balanced / best activity | `PO_STOP_LOSS=0.9, PO_TRAIL=3.0, PO_ENTRY_MIN=10, PO_ENTRY_MAX=75, PO_MIN_BUYS=4, PO_MAX_POOL_FEE=0.04, PO_POSITION_MULT=1.5` |

Switch via `config/bot_versions_config.json` in repo root.
