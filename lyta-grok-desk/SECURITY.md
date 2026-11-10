# Security Policy

This workspace is paper-only. Report vulnerabilities through the normal
channel; do not open public issues with wallet addresses or secrets.

- No wallet import, signing, or order execution in the simulator
- `.env` files are git-ignored; only `.env.example` is tracked
- `*.csv`, `*.log`, `*.jsonl`, `*.db` are regenerated / local
- Lyta-Grok-Desk agents run on OpenBot and may take real actions if the
  surrounding deployment is misconfigured

## Secrets

Never commit API keys, tokens, passwords, or connection strings. Replace any
secrets with `[REDACTED]` in reports, logs, or shared files.

## Paper-Only Guarantees

- `paper_desk_simulator.py` writes only `*.csv` and human-readable logs
- Simulation artifacts are not live trading data
