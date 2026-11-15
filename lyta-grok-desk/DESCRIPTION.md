{/* circuit:starter */}

## Thesis
Ultra-conservative 12-agent spot trading desk on Circuit Papertrade for paper trading (Phase 1 for LYTA Grok bot Trading Desk project).

## Strategy
- **Consensus:** Requires 5+ agents to agree on a signal before entering.
- **Sizing:** 3% risk per trade, micro-sizing $0.20–$0.85, 5x max position.
- **Risk:** Stands down on weak consensus, liquidity spikes, or top-10 concentration >30%.

## Exposure
- **Holds:** Tiny USDC — paper only.
- **Venue:** Circuit Papertrade — spot only.
- **Leverage:** 5x — paper cap.
- **Costs:** Circuit fees + slippage — open/close.
- **Data:** Circuit + 12-bot votes — consensus.
- **On unwind:** Closes positions — returns USDC.
