#!/usr/bin/env python3
"""
LYTA — Prompt Scoping Guard (Enforces the chunked-context rule)

From the Inference Engineering book spec: a ~60k-token book is too much to
feed into an agent as a single chunk. LYTA's agents should each stay small and
scoped.

This script enforces a PER-FILE token budget across the agent workspace so no
single agent's prompt can silently grow past the safe window.

Usage:
    python3 scripts/check_prompt_scoping.py            # read-only check
    python3 scripts/check_prompt_scoping.py --fail    # exit 1 on violations

Token estimate: 1 token ≈ 4 characters (rough code/markdown heuristic). The
budget is deliberately conservative so it only flags genuinely oversized files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Agent instruction/prompt files only. Implementation code
# (.py), third-party type defs (.d.ts), and data (.json/.yaml) are not
# pasted into an agent's context, so they are excluded.
AGENT_PROMPT_EXTS = (".txt", ".md", ".js", ".ts")
EXCLUDE_DIRS = (".circuit", "node_modules", "__pycache__", ".git")
# Conservative per-prompt token budget (1 token ≈ 4 chars -> ~4800 chars).
BUDGET_TOKENS = 1200


def estimate_tokens(text: str) -> int:
    # Rough heuristic: count whitespace-separated tokens, divide by ~4.
    return max(1, len(text.split()) // 4)


def iter_agent_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix not in AGENT_PROMPT_EXTS:
            continue  # implementation code, data, binaries
        if path.name.endswith(".d.ts"):
            continue  # third-party type declaration (circuit-sdk.d.ts), not an agent instruction
        files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce prompt token budgets.")
    parser.add_argument(
        "--fail",
        action="store_true",
        help="exit 1 if any agent prompt exceeds the budget",
    )
    args = parser.parse_args()

    files = iter_agent_files()
    if not files:
        print("No agent prompt files found.")
        return 0

    violations: list[tuple[Path, int, int]] = []
    print(f"{'#':<4} {'path':<55} {'est_tokens':>10} {'budget':>8} {'status':>8}")
    for i, path in enumerate(files, 1):
        text = path.read_text(encoding="utf-8", errors="replace")
        toks = estimate_tokens(text)
        status = "ok" if toks <= BUDGET_TOKENS else "OVER"
        if toks > BUDGET_TOKENS:
            violations.append((path, toks, BUDGET_TOKENS))
        print(f"{i:<4} {str(path):<55} {toks:>10} {BUDGET_TOKENS:>8} {status:>8}")

    if violations:
        n = len(violations)
        print(f"\n{n} agent prompt(s) exceed {BUDGET_TOKENS} tokens.")
        for path, toks, _ in violations:
            print(f"  - {path}: {toks} tokens (budget {BUDGET_TOKENS})")
        return 1 if args.fail else 0

    print(f"\nAll {len(files)} agent prompts within the {BUDGET_TOKENS}-token budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
