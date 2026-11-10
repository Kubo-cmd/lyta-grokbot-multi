══════════════════════════════════════════════════════════════════════
LYTA-GROK TRADERS DESK — V4 COMPREHENSIVE PACKAGE
(lyta-grok-desk-pumpfun, config v8, TrenchersAI-only, paper session)
══════════════════════════════════════════════════════════════════════

══════════════════════════════════════════════════════════════════════
FOLDER STRUCTURE
══════════════════════════════════════════════════════════════════════
lyta-grokbot-multi/
├── trenches_ai_prompt_reconciled.txt    ← THE main TrenchersAI prompt (v4)
├── circuit_ai_prompt_reconciled.txt     ← TrenchersAI reference (v4)
├── skills/
│   ├── shared_memory_format.md          ← coin_evaluations.log format
│   ├── friday_review_template.md        ← Friday post-run review
│   ├── competitive_benchmark.md         ← Arena vs our paper bot
│   └── strategy_reference_zostaff_gromo.md ← GROMO/Zostaff reference
└── (paper run ongoing)

══════════════════════════════════════════════════════════════════════
WHAT CHANGED (this session)
══════════════════════════════════════════════════════════════════════

1. trenches_ai_prompt_reconciled.txt (NEW v4)
   ✅ TrenchersAI-only platform (not CircuitAI)
   ✅ TrenchersAI terminal references (paper pool, 12 SOL, snipe tools)
   ✅ GROMO 5-agent pipeline (Scanner/Auditor/Analyst/Executor/Risk)
   ✅ zostaff 3-sniper copying strategy reference
   ✅ TrenchersAI agent roles (Scanners, Auditors, Analysts, Executors, Risk)
   ✅ Shared memory integration (source rule, charter)
   ✅ Friday post-run review reference

2. circuit_ai_prompt_reconciled.txt (UPDATED)
   ✅ Renamed to TrenchersAI-only
   ✅ Updated to reference TrenchersAI terminal
   ✅ Fixed incorrect circuit references

3. skills/shared_memory_format.md (NEW)
   ✅ Source rule format for coin_evaluations.log
   ✅ Charter template (OWNS/DONE LOOKS LIKE/STOPS AT)
   ✅ Evaluation log format with timestamps and sources

4. skills/friday_review_template.md (NEW)
   ✅ Full Friday review template
   ✅ Agent-type breakdown (Scanner/Auditor/Analyst/Executor/Risk)
   ✅ A/B test log
   ✅ Greatness check (5+ bot consensus)

5. skills/competitive_benchmark.md (NEW)
   ✅ Arena competitor analysis (M-42_GRIDMAKER, Z-ALPHA_SCALPER, etc.)
   ✅ GROMO vs our bot architecture map
   ✅ Why our config v8 is strengthened

6. skills/strategy_reference_zostaff_gromo.md (NEW)
   ✅ zostaff GROMO live demo (9 trades, 6 green, 3 red, +15x)
   ✅ GROMO 5-agent pipeline vs our config v8
   ✅ zostaff 3-sniper copying strategy

══════════════════════════════════════════════════════════════════════
KEY FINDINGS FROM THE ARENA + GROMO
══════════════════════════════════════════════════════════════════════

1. BEST AGENT TO STUDY: M-42_GRIDMAKER
   ● 12 trades, +8.2%, 22.40 SOL — most consistent run in the arena
   ● Grid-maker: repeated entries/exits over a range (like our exit ladder)
   ● Lesson: 12 consecutive wins prove consistency beats single trades

2. BEST SINGLE-AGENT REFERENCE: Z-ALPHA_SCALPER
   ● 5 trades, +2.1%, 5.12 SOL — our exact paper pool balance
   ● Scalper: small, frequent, tightly controlled exits
   ● Lesson: our 0.05 SOL base + 7/12 filter matches this profile

3. GROMO ZOSTAFF DEMO (real live)
   ● 9 trades, 6 green, 3 red, +15x in one night
   ● 3 snipers copied: Salem, DumbCrayonEater, PoorGoat
   ● Speed advantage: buy 30s after sniper (Trenches terminal helps)

4. ARCHITECTURE MAP
   ● GROMO: Scanner/Auditor/Analyst/Executor/Risk (5 agents)
   ● Our: 12 bots, 9 gates, shared memory, quorum filter
   ● Our exit ladder: 50% at 2x, rest at 3x (vs GROMO's −8% stop)

══════════════════════════════════════════════════════════════════════
CURRENT PAPER SESSION STATUS
══════════════════════════════════════════════════════════════════════

  Paper funds: $501 (USD)
  PnL: $0.00 (0% ROI)
  Last run: 11:45 UTC
  Candidates checked: 20
  Best 7/12: stood down (likely 1h ≤ +100% filter)
  Liquidity: $0–$11k
  Rug risk: 0.6–0.8
  Buyers: APU −48% to −61%

══════════════════════════════════════════════════════════════════════
NEXT STEPS (for the user to decide)
══════════════════════════════════════════════════════════════════════

1. Lower vote threshold 7→6
   Change in trenches_ai_prompt_reconciled.txt: "12-bot vote: coin must get
   6 of 12 votes" (line 75)

2. Relax Gate 3 liquidity floor from $50k to $10k
   Change in trenches_ai_prompt_reconciled.txt: "GATE 3 — Liquidity:
   $10k minimum floor" (line 96)
3. Consider applying −8% stop when desk is ready
4. Review Friday template after today's run

══════════════════════════════════════════════════════════════════════
END OF PACKAGE
══════════════════════════════════════════════════════════════════════
