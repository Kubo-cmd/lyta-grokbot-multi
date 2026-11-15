# Phase 2 Roadmap — pump.fun Paper Trading Desk (zero-burn)

## Position
This is a **paper-only, observation-only** Phase-2 pump.fun demonstration.
No live capital, no live Grok Bot execution, no trade execution anywhere.
Exit code is always `0`, even when nothing qualifies.

## Rules of this desk (contract)
- [x] Observation only — no trades executed (this run and every run).
- [x] Zero-burn: no API keys, no wallet extensions, no live credentials.
- [x] Read-only data: verified DEX feeds only (DexScreener via RealTradeFeed).
- [x] Multi-bot gate (A3b): 5 heuristic paper bots + 3 volume copies = 8 votes.
- [x] Full-suite gate: `pytest tests/ -q` → **31 passed / 0 failed**, every run.
- [x] Verbose rollup required: every pair prints per-bot votes, gate rollup,
      and one stand-down reason. Aggregate-only output is rejected on review.

## Stage 1 — Current: verbose Phase-2 paper run (this PR)
- `pumpfun_phase2_verbose_run.py`
  - Replaces aggregate-only output with a per-pair verbose rollup.
  - Prints: each bot's kind/score/tag, consent out of 8, `|combined|`,
    gate tag, decision, and **stand-down reason** (consensus_min /
    signal_gate / tag).
  - Live fallback (`RealTradeFeed`) and a deterministic simulation table for
    offline runs with zero credentials.
- `docs/ROADMAP.md`, `PROMPTS.md` run prompt — ready to paste, observation only.
- Green: 31/31 suite preserved.

## Stage 2 — Later: new signal API (only if a real spec is supplied)
- A live-trading wallet-extension credential (e.g. Frontrun.pro browser
  extension) is not a repo-compatible signal API.
- If the user supplies an endpoint + payload/response shape, wire it as a new
  env-var-driven source (`FRONTRUN_PRO_API_KEY` style), add one test, and run
  the full 31/31 suite — paper-only, zero-burn.

## Current verification (actioned this run)
- `python3 pumpfun_phase2_verbose_run.py` → 30 observation pairs printed,
  verbose per-bot rollups + stand-down reasons, exit 0.
- Live feed: RealTradeFeed read-only spot pairs (schema: `chain/dex/base/quote/
  liquidity_usd/vol24_usd`) — pump.dev ticket fields (fee/age/narrative) not
  present in spot table; missing fields reported as observed, never fabricated.
- `pytest tests/ -q` → 31 passed, exit 0; local `main` == `origin/main`
  (5eaeb7bc5685419b4b4d3a52f721e0589bee5bd9), clean tree.
