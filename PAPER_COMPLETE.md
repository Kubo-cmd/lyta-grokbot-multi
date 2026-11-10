# PAPER_COMPLETE — memecoin grok-bot desk

**This run is observation only. No trades executed.**

**Status:** Local paper freeze. **Not live. Not published.** Active restore target is Tightened **7/12** (STOP_LOSS=0.35, TAKE_PROFIT=0.50, skip >100% 1h, liquidity ≥ $50k). The v3 freeze list below is historical.

## Council

- ALLOW: this paper freeze
- DENY: live capital, sniping, Pelosi/forex live, cron, git push / OSS publish, H03

## Frozen rules (Paper Observer v3 — the "bet" for the grokbot trading desk)

- Continuous screening (NO fixed 15-min cycle)
- LONG-only (No short positions)
- Entry window: 8%–70% bonding-curve progress
- Minimum activity: 15 unique wallets / 3 buys / 30 holders
- Concentration: top 10 ≤ 30%
- Developer holdings: ≤ 15%
- Rebuys: off
- Exits: 50% at 2x, 100% remainder at 3x
- Trailing exit: 2.5x after 15% drawdown
- Stop-loss: 0.10x (−90%) — TRIGGER ONLY, not a guaranteed loss cap
- Stale/dead exits: 120s / 300s
- Hold through PumpSwap graduation: yes
- Slippage: 15% entry / 5% exit
- Mint/freeze authority revoked: required
- Risky extensions: blocked
- Max pool fee: 4%
- Trading hours: 24/7
- Session P&L limits: off
- User paper capital $6 · 3% risk · margin $0.20–$0.85 · 5x cap · paper-only

## What "done" is

The grokbot trading desk memecoin strategy is **paper-complete** on this machine:

- `paper_desk_simulator.py` — Paper Observer v3 simulator (continuous screening, long-only)
paper_desk_simulator.py — 12-agent spot trading simulator (frozen, not active)
- `STRATEGY_FINALIZE.md` — the "bet" document
- Circuit prompts under `lyta-grok-desk/` (Circuit paper)

## What "done" is not

- Not a money-maker. Early paper results: **2 closed positions, both losses, −0.030125731 SOL (−30.55%)** realized. Both closed on the `bc_drop` rule, not the 0.10x stop-loss.
- Not open-sourced. Remote `origin` is **PRIVATE** `Kubo-cmd/lyta-grokbot-multi`. Do not push. `LICENSE` is MIT text tracked in this private tree — unpublished; do not treat as a public OSS grant.
- Not Pelosi copytrading. Not forex. Those are **PARKED**.
- 2 positions is **below the 20-position evidence floor**. We are leaving v3 unchanged while gathering a larger sample. Fine-tuning decisions will be made after we reach the evidence floor.

## Next (pending approval)

1. Extended paper run: gather 20+ positions before any fine-tuning
2. After paper window: compare rejection gates, exit reasons, and realized results
3. Then revisit MIN_LIQ $50k→$20k if needing more trades

Artifact: (experimental paper-run artifact — not part of the open-source repo)

artifact_sha256: `dfa1018366e516024f4cfd07d711a9f8528c04f7f645b9504c29e2cf9fe7e34c`

cost_usd: 0.00

EVIDENCE PENDING — PATTERN NOT YET ESTABLISHED.
