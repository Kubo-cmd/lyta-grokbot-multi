#!/usr/bin/env bash
# lyta-run.sh — zero-burn health check for the LYTA Grok Desk repo.
# Runs the real chain (no mocks, no stubs) and reports actual output+timing.
# Safe to re-run: fully deterministic paper path, idempotent.
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO" || exit 1

pass=0; fail=0
note() { echo; echo "═══ $* ═══"; }

step() { # step <name> <command...>
  local name="$1"; shift
  local t0 t1 rc
  t0=$(date +%s%N)
  echo "── step: $name"
  "$@"
  rc=$?
  t1=$(date +%s%N)
  echo "   [exit=$rc  real=$(( (t1-t0)/1000000 ))ms]"
  if [ $rc -eq 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); fi
  return $rc
}

note "LYTA desk zero-burn health check (Rei Kubota's paper-only desk)"
step "1. Circuit desk schema/check (cd lyta-grok-desk, bun run check)" \
  bash -c 'cd lyta-grok-desk && bun run check'
step "2. Unit tests (pytest, repo root)" \
  python3 -m pytest test_paper_desk_simulator.py -q
step "3. Paper-only simulator default run (no network, no API keys)" \
  python3 pumpfun_desk_simulator.py --quiet
step "4. Simulator --help is instant (sanity: CLI parses)" \
  python3 pumpfun_desk_simulator.py --help >/dev/null

echo
echo "═══ RESULT: $pass ok / $fail failed ═══"
[ $fail -eq 0 ]
