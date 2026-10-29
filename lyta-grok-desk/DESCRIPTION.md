{/* circuit:starter */}

## Thesis
12 Grok personalities act as an autonomous desk trading Papertrade perps with different biases.

## Strategy
- **Multi-bot desk:** SCOUT to EXECUTOR vote on perps using tuned risk rules.
- **Papertrade focus:** Opens high-leverage synthetic positions with hard stops.
- **Sizing:** 8% max risk per the desk, consensus from active bots.

## Exposure
- **Holds:** USDC + open perps — Collateral and active positions on Papertrade.
- **Venue:** Papertrade — Synthetic perps on HyperEVM.
- **Leverage:** 5-100x — Configurable in settings, default 20x.
- **Costs:** Fees + funding — Papertrade trading fees and funding rates.
- **Data:** Circuit + heuristics — Uses Circuit data plus internal market signals.
- **On unwind:** Closes positions — All perps closed, remaining USDC returned.