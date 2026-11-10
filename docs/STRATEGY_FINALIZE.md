# 🎯 LYTA GROKBOT TRADING DESK — STRATEGY & FINE-TUNING
## The "Bet" Document
**Date:** 2026-11-02
**Status:** Active — Paper Observer config v3 is the "bet"
**Strategic Priority:** We are only making the strategy and fine-tuning. This is the bet for our grokbot trading desk goal.

---

## 1. The "Bet"

The grokbot trading desk is betting on **circuit-paper spot trading screening** — a continuously-running paper bot that screens bonding-curve tokens and either buys or skips. No sniping. No live capital. No real swaps. Paper only.

The bet is: **a behavior-based, aggregator-style bot will produce a persistent edge on circuit-paper spot tokens over a 2–3 week window**, and we will gather enough paper data to validate (or kill) the strategy.

### Why this is the bet

| Component | What it does | Why it's the bet |
|---|---|---|
| **Continuous screening** | Screens bonding-curve tokens, either buys or skips — no fixed cycle, no shorts | The user-specified behavior: one continuous-screening, long-only bot |
| **Minimum activity gates** | 15 unique wallets / 3 buys / 30 holders | Filters out tokens with no real traction |
| **Concentration limits** | Top 10 ≤ 30%, developer holdings ≤ 15% | Reduces rug/flip risk from insiders |
| **Fee break-even ~1.06x** | At 0.05 SOL buy size, fees break even at ~1.06x | The math checks out at the current size |
| **Exits (2x / 3x)** | 50% at 2x, 100% remainder at 3x | Caps upside for the first tranche, banks the rest |
| **Stop-loss 0.10x** | Trigger only, NOT a guaranteed loss cap | Thin liquidity or a rug can produce a much worse fill |
| **Stale/dead exits** | 120s stale, 300s dead | Catches frozen or abandoned pools |
| **Paper-only ledger** | Simulated capital, no live money | Zero burn. The strategy is fine-tuned entirely against paper. |

---

## 2. Strategy Architecture

### Continuous screening loop

The bot does NOT follow a fixed 15-minute cycle. It continuously screens the market and either buys or skips based on the rules. This was corrected by the user — a fixed cycle is not a supported config control here.

### Bot personality summary

The deployed strategy is **one continuous-screening, long-only bot** with these guards:
- Minimum activity: 15 wallets / 3 buys / 30 holders
- Concentration: top 10 ≤ 30%, developer holdings ≤ 15%
- Fee break-even ~1.06x
- Entry window: 8%–70% bonding-curve progress
- Exits: 2x/3x ladder, trailing 2.5x/15% drawdown, stale 120s, dead 300s
- Stop-loss: 0.10x (trigger only)
- Slippage: 15% entry / 5% exit
- Mint/freeze authority revoked required
- Risky extensions blocked
- Max pool fee 4%
- Trading hours: 24/7
- Session P&L limits: off

---

## 3. Early Results & Evidence Floor

### What we observed

- **2 completed positions, both losses**, totaling **-0.030125731 SOL realized (-30.55%)**
- Both closed because of the recorded `bc_drop` rule (bonding-curve drop below the entry window), **not** the configured 0.10x stop-loss
- **0 open positions** currently
- The 20-position evidence floor is **not yet reached** — 2 positions cannot establish a persistent pattern or support fine-tuning claims

### Why this matters

Two losses on two trades is not evidence of an edge — it's sample noise. The `bc_drop` exit (bonding curve dropping below the entry window) is a structural rule that will fire on any token that loses momentum, regardless of whether the entry was sensible. We need:

1. **More trades** — at least 20 positions before drawing conclusions
2. **Exit reason comparison** — how often do we exit on `bc_drop` vs stop-loss trigger vs 2x/3x ladder vs stale/dead?
3. **Realized PnL per exit reason** — does `bc_drop` consistently produce losses? Do 2x/3x exits produce wins?
4. **Rejection gate analysis** — how many tokens do we skip, and why?

### The cleanest move right now

**Leave v3 unchanged.** It is currently gathering a larger sample. Once we have 20+ positions, we will:
- Compare rejection gates (how many tokens are skipped at each filter)
- Compare exit reasons (bc_drop vs stop-loss vs ladder vs stale/dead)
- Analyze realized results per exit reason
- Then decide on fine-tuning

---

## 4. Paper-Only Ledger Rules (Preserved)

```text
• No live money.
• No sniping.
• No real XLIQUID buys.
• No real swaps.
• No live wallets.
• Simulated paper only.
• Verbose logging of every vote, stand-down reason, and exit.
• One continuous-screening, long-only bot.
```

---

## 5. Fine-Tuning Checklist

- [ ] Wait for 20+ positions before drawing conclusions
- [ ] Compare rejection gates across all filters (wallets, buys, holders, concentration, dev)
- [ ] Compare exit reasons (bc_drop, stop-loss, 2x/3x ladder, stale, dead)
- [ ] Analyze realized PnL per exit reason
- [ ] Verify fee break-even at 0.05 SOL (~1.06x)
- [ ] Keep 0.10x stop-loss as trigger only (not a guaranteed loss cap)
- [ ] Keep continuous screening (no fixed cycle, no shorts)
- [ ] Keep paper-only invariant throughout

---

## 6. Next Step

The Paper Observer config v3 is the bet. While it gathers a larger sample, we will:
1. **Wait for 20+ positions** on the paper ledger
2. **Compare rejection gates** across all filters
3. **Compare exit reasons** across all exit types
4. **Analyze realized PnL per exit reason**
5. **Then fine-tune** based on the actual distribution — not on two losses

The bet is finalized. Now we fine-tune with evidence.
