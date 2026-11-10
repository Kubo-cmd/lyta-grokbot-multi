{/* circuit:starter */}

## Thesis
Ultra-conservative 10-agent spot trading desk on Circuit Papertrade for paper trading (Phase 1 for LYTA Grok bot Trading Desk project).

## Strategy
- **Consensus:** Requires 5+ agents to agree on a signal before entering.
- **Sizing:** 3% risk per trade, micro-sizing $0.20–$0.85, 5x max position.
- **Risk:** Stands down on weak consensus, liquidity spikes, or top-10 concentration >30%.

## Exposure
- **Holds:** Tiny USDC — paper trading only.
- **Venue:** Circuit Papertrade — spot trading only (paper).
- **Leverage:** 5x — Max capped for paper.
- **Costs:** Trading fees + slippage — Circuit Papertrade.
- **Data:** Circuit Papertrade + 10-agent consensus — platform data + bot signals.
- **On unwind:** Closes positions — returns remaining paper USDC.
