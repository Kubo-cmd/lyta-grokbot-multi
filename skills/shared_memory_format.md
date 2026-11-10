══════════════════════════════════════════════════════════════════════
SHARED MEMORY FORMAT — coin_evaluations.log
(lyta-grok-desk-pumpfun, config v8)
══════════════════════════════════════════════════════════════════════

Every coin evaluated writes ONE line to this file. Format:

[TIMESTAMP] [COIN] [RESULT] [GATE_N] [VALUE] [THRESHOLD] [REASON] [SOURCE]

Where:
  TIMESTAMP  ISO-8601 UTC, e.g. 2026-11-05T11:45:00Z
  COIN       token symbol, e.g. PEPE
  RESULT     PASS or SKIP
  GATE_N     gate number that passed/failed, e.g. 5
  VALUE      actual value, e.g. 12.3
  THRESHOLD  required threshold, e.g. 8.0
  REASON     written reason (one sentence, quote verbatim)
  SOURCE     who evaluated, where from (RugCheck, API, manual), when

EXAMPLE:
2026-11-05T11:45:00Z | PEPE | SKIP | 5 | 1.2% | 8% | curve too low to trade | RugCheck reader: Z-ALPHA, 11:45 UTC, api.rugcheck.xyz

SOURCE RULE (quote verbatim in logs):
  Every number carries who read it, when, and where it came from.
  Example: [SKIP 3] liquidity 24.6k below 50k — RugCheck reader: Z-ALPHA,
  11:45 UTC, api.rugcheck.xyz

CHARTER TEMPLATE (apply to each agent role):
  OWNS: <role> — <who/why>
  DONE LOOKS LIKE: <concrete completion signal>
  STOPS AT: <hard stop condition>

EXAMPLE:
  OWNS: Z-ALPHA_SCALPER — scanner agent, candidate discovery
  DONE LOOKS LIKE: 7/12 votes, top 5 coins evaluated, [PASS]/[SKIP] logged
  STOPS AT: no trades executed outside paper pool, exit ladder rules enforced
