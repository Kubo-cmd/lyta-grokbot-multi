# Host vs application

This note splits **host** (the runtime that loads an agent) from **application** (this paper desk). The original table scored application architecture as a platform win. That is the error this rewrite removes. There is no winner column.

This tree is PRIVATE. Observation only. No trades executed.

## Application (this desk)

The application is the 12-agent paper desk in `lyta-grok-desk/`, gated by Tightened **7/12**, `$6` paper collateral, BTC/ETH `papertrade`, stop **−35%** / take **+50%**, liquidity floor **≥ $50k**, 1h pump cap **≤ 100%**. Workspace PAPER-CTRL on `lyta-grok-desk-paper` keeps buy **$0.20**.

These are application rules, not host features:

| Application fact | Why it is not a host score |
|---|---|
| Agent count (12) and named roster | Lives in this repo’s prompts and `index.ts`, not in the host binary |
| Paper-only / zero-burn | A desk policy. Hosts do not make it true |
| Voting / consensus bar 7/12 | **Not a risk layer.** Same model family, seven signatures, one correlated failure |
| Micro-sizing | Desk config (`risk_per_trade`, size gates). Changing host does not change size |
| Isolation between named Bots | Not a security boundary when they share one model family |

Do not treat separate Bot names as a security boundary.

## Host (runtime)

A host is wherever this application is loaded. Isolation between hosts is the discriminator. Scoring “which host has more agents” revives the original table.

| Host | Role here | Do not |
|---|---|---|
| OpenBot | Current paper workspace: `lyta-grok-desk-paper`. License is PolyForm Noncommercial, **not OSS** | Score a “full open-sourcing” row as an OpenBot win; start a live thread this pass |
| Grok Bot.app | One possible desktop host. Inspect-only this pass. The paper desk is **not** hosted inside the `.app` | Equate it with the `grok` CLI; turn computer-use on; treat inspect notes as a setup |
| Hermes Agent | Ships `hermes migrate openbot` / `hermes import-agent openbot` and `hermes migrate grok-bot` / `hermes import-agent grok-bot` | Treat migrate-ability as a unique OpenBot win |

Migrate-ability is shared. Those Hermes commands exist; they are not a reason to import this desk this pass.

## What this note does not claim

- No live capital. No pump.fun this pass. Phase 1 remains Circuit papertrade BTC/ETH.
- Tightened 7/12 stays. Do not strip settings to make `circuit check` pass.
- A zip named like this repo can be a 2-file review pack. Keep packs in scratch; do not copy them over `comparison_showcase.md` / `showcase.html`.
- Sibling adapters named in a review (`agent-turn-receipts`, `authority-lightcone-auditor`, `agent-quiescence-receipts`, `token-null-router`, `micro-pm-okx`, `hermes-studio`, `lyta-shield`) are **unwired here**. A citation is not a wire-in.
- LICENSE MIT text is tracked in this PRIVATE tree only — unpublished.

## Frozen application gates (not host rows)

| Gate | Frozen value |
|---|---|
| Consensus | 7/12 |
| Liquidity | ≥ $50k |
| 1h pump | ≤ 100% |
| Stop / take | −35% / +50% |
| User capital | $6 paper |
| Network | `papertrade` |
| Monitor pass-rate band | 35–55% |

Opening paper under current `index.ts` still needs `margin >= 0.25` and `collateral >= 2.0`, which conflicts with PAPER-CTRL buy **$0.20**. That conflict is left in place. Neither size raise nor 7/12 loosen is “earn more.”
