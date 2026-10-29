{/* circuit:starter */}

## Thesis
12 Grok personalities run as an autonomous desk on Papertrade perps. Tuned for tiny ~$6 paper starting capital.

## Strategy
- **Micro desk voting:** 12 bots vote; only tiny sizes allowed.
- **Papertrade perps:** Very small leveraged positions with hard stops.
- **Tiny sizing:** Capped at ~$3.50–$4.50 notional. Max 18% of collateral.

## Exposure
- **Holds:** Tiny USDC + perps — Small collateral and positions.
- **Venue:** Papertrade — Synthetic perps.
- **Leverage:** 5-10x — Kept low for $6 accounts.
- **Costs:** Fees + funding — Papertrade fees matter on small size.
- **Data:** Circuit + heuristics — Internal + platform data.
- **On unwind:** Closes positions — Returns remaining paper USDC.