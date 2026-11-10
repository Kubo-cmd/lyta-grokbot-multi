# Contributing to Grok bot Multi

## Repo Layout

```text
lyta-grokbot-multi/
├── README.md                   # Overview, platform split, trading rules
├── ARCHITECTURE.md             # Dual-platform separation (Grok Bot server / OpenBot agents)
├── STRATEGY_FINALIZE.md        # Strategy decisions
├── paper_desk_simulator.py     # Phase 1: Circuit BTC/ETH paper simulator
├── paper_desk_simulator.py   # paper trading simulator (frozen)
├── paper_desk_adapter.py       # paper trading data adapter (future)
├── scripts/                    # Auxiliary scripts (runners, monitors, plotters)
├── config/                     # LOCAL config (git-ignored, example in .env.example)
├── legacy/                     # Experimental / superseded artifacts
├── lyta-grok-desk/             # OpenBot agent workspace (7 agents + Circuit SDK)
└── docs/                       # Design & strategy documentation
```

## How to Add a Trading Rule

1. Put the rule in `paper_desk_simulator.py` (Phase 1) or
   `paper_desk_simulator.py` (paper).
2. If the rule is agent-facing, add a trigger to `lyta-grok-desk/circuit.toml`.
3. Register the agent in the 7-agent table in `lyta-grok-desk/AGENTS.md`.
4. Document the rule in `README.md` (Trading Desk Parameters).

## Submitting Changes

1. Keep paper-only behavior intact — no real trades, no signing.
2. Update documentation when you change parameters.
3. Do not commit `*.csv`, `*.log`, `*.jsonl`, or `*.db`.
4. Add a one-line summary to the commit message.

## Agent Platform

- **Grok Bot** = server (managed cloud VM, always-on, task routing)
- **OpenBot** = agents (local workspace, 7 trading agents)

See `ARCHITECTURE.md` for the full split.
