{/* circuit:starter */}

## Thesis
Ultra-conservative 12-bot desk on Papertrade perps for $2-$6 paper trading (Phase 1 for LYTA Pump.fun Grok Bot Trading Desk project).

## Strategy
- **Consensus:** Requires 5+ of 12 bots to agree on a side before opening.
- **Sizing:** 3% risk with margin kept between $0.20-$0.85 and scales with collateral.
- **Risk:** Max 5x leverage; stands down on weak consensus or below minimums.

## Exposure
- **Holds:** Tiny USDC + perps — Papertrade collateral.
- **Venue:** Papertrade — Synthetic perps for tiny budgets.
- **Leverage:** 2-5x — Very low for $2-6 accounts.
- **Costs:** Fees + funding — Papertrade costs.
- **Data:** Circuit + heuristics — Platform data + bot rules.
- **On unwind:** Closes positions — Returns remaining paper USDC.