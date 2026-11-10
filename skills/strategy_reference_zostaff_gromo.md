══════════════════════════════════════════════════════════════════════
STRATEGY REFERENCE — zostaff GROMO + zostaff 3-Sniper Copy (Nov 4, 2026)
══════════════════════════════════════════════════════════════════════

FROM: https://x.com/zostaff/status/2118045006472544738 (retrieved via web_extract)
LIVE DEMO: 9 trades, 6 green, 3 red, +15x in one night

● GROMO: 4-agent copy system on Solana (Scanner/Auditor/Analyst/Executor/Risk)
● 3 snipers copied: Salem ($6.3M/294K followers), DumbCrayonEater ($8.8M/
  695K followers), PoorGoat (#1 PnL)
● GROMO's rule: "copy 30s after, stop loss minus 8%, close by 6am"

══════════════════════════════════════════════════════════════════════
GROMO 5-AGENT PIPELINE (architecture)
══════════════════════════════════════════════════════════════════════

1. Scanner — finds market tokens, filters by wallet seed, top-10 share,
   developer share, rug_risk (api.rugcheck.xyz)
2. Auditor — 9-layer deep dive:
   Layer 1: wallet seed (where token came from)
   Layer 2: top-10 share (concentration)
   Layer 3: developer share (<15%)
   Layer 4: rug risk (<0.8)
   Layer 5: token authorities (holders, top wallets, dev)
   Layer 6: Meme quality (known naming, token icon, name)
   Layer 7: X activity (organic or coordinated shill)
   Layer 8: GrokHOOD Safety Score (0-1)
   Layer 9: funded by Grok bot or not (who is building on it)
3. Analyst — 4 closed questions:
   ● Is this token alive in 6 hours?
   ● Does organic buying exist or are we chasing a run?
   ● Is the buying flush being absorbed or can frontrunners exit?
   ● Is there any activity from wallstreetfunds on X?
4. Executor — enters the trade, applies the risk rules
5. Risk — manages the open position, updates bot stats, writes to logs

══════════════════════════════════════════════════════════════════════
LYTA-GROK-DESK-PAPERBOT — CONFIG v8 vs GROMO
══════════════════════════════════════════════════════════════════════

GROMO (5 agents):
  1. Scanner → our 12 bots (scanning, valuation, vote)
  2. Auditor → our 9 gates, Gate 3 disabled
  3. Analyst → our 7/12 vote + 1h ≤ +100% filter
  4. Executor → our 0.05 SOL buys, exit ladder
  5. Risk → our trailing exit, time exits

Key differences:
  ● GROMO: 5 agents, 9-layer Auditor, 4-question Analyst, −8% stop
  ● Our: 12 bots, 9 gates (Gate 3 disabled), no custom stop (deferred)
  ● GROMO: speed = buy 30s after sniper (Trenches terminal advantage)
  ● Our: 7/12 vote + shared memory = quorum filter, not speed

══════════════════════════════════════════════════════════════════════
ZOSTAFF 3-SNIPER COPY STRATEGY (what works)
══════════════════════════════════════════════════════════════════════

Three snipers were copied:
  1. Salem — $6.3M, 294K followers
  2. DumbCrayonEater — $8.8M, 695K followers
  3. PoorGoat — #1 PnL, 619K followers

GROMO's formula:
  1. Watch whom the whales are sniping
  2. Buy 30s after (not before)
  3. Stop loss minus 8% (the user's deferred −8% trigger)
  4. Close by 6am (close window)

Result: 6 tokens, 9 trades, 6 green, 3 red, +15x overnight.

══════════════════════════════════════════════════════════════════════
WHAT THIS MEANS FOR LYTA-GROK-DESK-PAPERBOT
══════════════════════════════════════════════════════════════════════

1. Speed advantage: TrenchersAI terminal's snipe tools give the same
   timing edge GROMO has (buy 30s after, not before)

2. Consensus filter: 7/12 vote is our "who the whales are copying"
   consensus detector — more agents = more reliable signal

3. Gate discipline: GROMO's 9-layer Auditor = our 9 gates (Gate 3 disabled
   in paper run, but the Auditor logic transfers)

4. Risk rule: our exit ladder (50% at 2x, rest at 3x) replaces GROMO's
   −8% stop until we're ready for it

5. Friday review: zostaff's live demo is a free A/B test — we can compare
   one week of our config v8 vs one week of GROMO's +8% stop

══════════════════════════════════════════════════════════════════════
END OF STRATEGY REFERENCE
══════════════════════════════════════════════════════════════════════
