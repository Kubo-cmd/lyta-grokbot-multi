# Security Policy

## Supported Versions

| Version | Supported     |
| ------- | ------------- |
| `paper_desk_simulator.py` | Active |
| `pumpfun_desk_simulator.py` | Active |
| `lyta-grok-desk/` (OpenBot agents) | Active |

## Reporting a Vulnerability

If you discover a security vulnerability in this paper-trading desk, please
report it responsibly. **No real capital is ever risked** — this repository is
paper-only by design.

1. Do **not** open an issue that exposes secrets, wallet addresses, or
   trading keys.
2. Email the maintainer through the contact in the project metadata.
3. Include the affected file, the risk (read-only / simulation / paper), and a
   minimal reproduction.

## Secrets Management

- `.env` files are git-ignored. See `.env.example` for the only expected keys.
- Never commit API keys, tokens, passwords, or connection strings.
- Replace any secrets with `[REDACTED]` in reports, logs, or shared files.

## Paper-Only Guarantees

This workspace runs **paper-only** simulations:

- No wallet import, no signing, no order execution
- `paper_desk_simulator.py` writes only `*.csv` (regeneratable) and
  human-readable logs
- `grok_signals_for_real_bot.json`, `performance_log.csv`, and
  `paper_trades_autonomous_grok.csv` are simulation artifacts, not live
  trading data

## OpenBot / Grok Bot Deployment

The `lyta-grok-desk/` directory is an OpenBot agent workspace. Agent code
runs against the real OpenBot platform and can take real (non-paper) actions
if the surrounding deployment is misconfigured. Keep `agent.memory` sanitized
and read `agent.walletAddress` at run time; never hard-code credentials.

---

*This repo is **PRIVATE** (see `README.md`). Do not publish or mirror.*
