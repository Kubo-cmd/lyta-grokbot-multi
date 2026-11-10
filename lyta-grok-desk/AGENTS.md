# OpenBot Agent Workspace

This is the **OpenBot (Agent Execution Layer)** — the local desktop workspace where
10 trading agents run.

**Role:** Trading execution, signal generation, analysis, and risk management.
**Platform:** Local desktop (GitHub `de1lymoon` stack), MCP-native.

## Trading Agents (10)

| Agent | File | Role |
|-------|------|------|
| `lyta-grok-desk-paper` | `_paper_agent.ts` | Circuit BTC/ETH paper trading (Phase 1 baseline) |
| `lyta-grok-desk-pumpfun` | `index.ts` | Pump.fun memecoin trading (Phase 2) |
| `lyta-grok-desk-signal` | `_signal_agent.ts` | Signal scanner for pump.fun opportunities |
| `lyta-grok-desk-analyst` | `_analyst_agent.ts` | Rug risk, liquidity, score evaluation |
| `lyta-grok-desk-trader` | `_trader_agent.ts` | Micro-sizing execution ($0.20–$0.85) |
| `lyta-grok-desk-risk` | `_risk_agent.ts` | Risk management (3% risk, 5x max, stand-down) |
| `lyta-grok-desk-scout` | `_scout_agent.ts` | Narrative/rug signal checker — GMGN + wallet analysis |
| `lyta-grok-desk-devwatch` | `_devwatch_agent.ts` | On-chain wallet monitoring (Hrundel75 rules) |
| `lyta-grok-desk-trencher` | `_trencher_agent.ts` | TrenchAI deployment monitor + integration |
| `grok-bot` | `_grok_router.ts` | Server router — routes tasks to LYTA agents |

## Platform Roles

- **Grok Bot (server)** — Cloud VM (xAI), always-on, task routing/firing, persistent state
- **OpenBot (agents)** — Local desktop workspace, multi-agent FIFO queues, shared files, ACP communication

## How an agent lives
An agent is one exported function in `index.ts`: `run(agent)`. The platform calls it each time a trigger declared in `circuit.toml` fires, and `agent.trigger` says which one. Choose the trigger that matches when the strategy must act instead of polling for an event a trigger already reports. Any user can start the agent on their own wallets, so read `agent.walletAddress` at run time and never hard-code the agent's own address.

Every run starts from nothing; only `agent.memory` survives, and it belongs to this session. `agent.allocation`, read each run, is the truth about what the session holds; filter its `holdings` by `kind` (`token`, `perp` or `prediction`). The session pays its own network fees, so a gas token it was never allocated holds a negative quantity: a cost already paid, never invalid data or a reason to skip a run. An order shows up in allocation on a later run, so within a run track what you just did. The first run acts: read the history a signal needs with a lookback instead of collecting it across runs.

A session ends when the user presses stop: the platform halts the triggers and runs no agent code; holdings, positions and resting orders stay as they are for the user to close from the Terminal.

## Reading data
`agent.data` is the first source for any asset, market or venue fact. Search while building to find the exact address, symbol or key, and ship that identity, never a search whose first row could change. Circuit owns data freshness: use every answer as served and never check timestamps or row counts. An outside source is only for a fact Circuit data lacks. Protocols the SDK does not model are reachable through `agent.wallet.transactions` and outside APIs. The engine approves only its own swaps; send a raw contract's allowance as its own keyed transaction first. Confirm during the build that an outside endpoint answers with the shape you read, and that an RPC endpoint the agent brings as a named constant has the right chain id. Give each request `AbortSignal.timeout`.

A trigger or schedule that marks a period treats the whole period as its window: act once while the period is open and its keyed operation is not yet admitted, so a late or missed tick does not skip it.

Backtests answer every `agent.data` read as of the simulated clock and simulate perpetual orders on the venue whose USDC the agent starts from, Hyperliquid or Lighter; any other money action, outside request or venue HTTP call fails the run.

## Sizing
Size from `agent.allocation`; `"max"`, `{ balancePercent }` and `perpReduce` measure the session's own holding, and `{ valueUsdc }` lets the engine convert at the live mid. Every amount the SDK takes or returns is a decimal string of whole tokens: do money math only with the `circuit:sdk` decimal helpers, never floats or decimal.js, cross from a float signal with `toFixed`, and floor long products with `decimalDivide(x, "1", 18)`; never write decimal parsers, rebuild allocation from another ledger or round: the engine rounds spends down and minimums up to each token's smallest unit. Allocation is a budget, not an authorization, so the agent's own arithmetic keeps it inside. A size the user does not state splits the allocation evenly across the positions the strategy holds at once, and a repeating buy spreads it across its stated period. A leverage multiple only sizes notional, once: allocation times the multiple; a close is never multiplied, and the agent never sets venue leverage or margin mode. When a computed size falls below the venue minimum below, place the minimum instead. The engine owns every other check; send the order and let a refusal throw.

## Money writes
The engine owns preparation, prerequisites, quotes, balance and minimum checks, submission and settlement; the strategy owns only the decision. Call `create` directly, even for "best price": the engine already takes the best executable route. Quote only when the rule needs a number to decide whether or how much to trade. Never persist previews, quotes or plans. A money write returns the completed operation or throws `MoneyActionError` (`outcome.status` `rejected`, `failed` or `unresolved`); let it throw. Treat past `error` operations as history. Do not repeat an intent while `operations.list({ pendingOnly: true })` holds it. A decision that must happen at most once (a weekly buy, a single entry) gets a key such as `buy/${week}`, passed as `{ idempotencyKey }` in the write's second argument. Before deciding, read `operations.retrieve({ idempotencyKey })`: `null` means write, and anything else means already decided. A reused key returns its succeeded operation, or throws its failure or pending outcome, without preparing the request again.

Exits, stops and limits are the user's; add none they did not ask for. Only the session's own orders and liquidations change its holdings, never the user's manual trades on the same account. Close a position with a plain opposite order for its exact session quantity. Use each holding's `entryPriceUsd`, `priceUsd` and `unrealizedPnlUsd`, where null means unknown, never zero; realized results, fees and funding already land in the session's collateral holding. A user's limit those numbers cannot measure uses the nearest one they can.

## Settings and configuration
Prefer good defaults to settings. Declare at most three, each a choice a person must make before starting (size, the main signal threshold), and read every one in code. A number the user specifies is a default. Each number setting has a `min` and `max` where the strategy still makes sense. Read settings through the generated `circuit-settings.d.ts` without a cast, and never repeat a default as a literal.

Declared triggers are the ones the code expects. `[startingAsset]` names the exact asset the strategy starts from, never the whole wallet, on the venue it trades (HyperCore for Hyperliquid, Polygon for Polymarket), and its minimum funds the first order including fees. Preserve `agentId`.

## What the user sees
`agent.log` is the user's only window into the agent. Write short plain sentences with symbols, formatted amounts and percentages: what the rule saw and what was traded, such as "Bought 0.01 ETH: price crossed above the 20-day average." Never claim confirmation from submission alone, and leave addresses, hashes, raw units and transaction details to the transaction cards. Log after a loop, one line per kind of outcome with a count, never per item.

## Code
Write the least code that does the job: read what the rule needs, decide, place the order; a rule stated in a few sentences is a few dozen lines. No state machines, wrappers, helpers, validation of values you wrote yourself, or memory of what was done; memory holds only facts the rule needs across runs, such as a high-water mark, under stable keys. Type SDK argument objects where they are built so discriminants stay literal, and await SDK calls. Implement the requested behaviour: only a venue the SDK cannot write to or a credential the agent cannot hold blocks it. Never substitute fabricated signals, disabled execution, monitor-only, manual input or paper trading.

## Prompt & Builder Reference

Copy-paste prompts for Circuit AI (the Builder / chat interface):

|- **Multi-Agent Setup (Option A):** `CURCH_BOT_MULTI_AGENT_PROMPT.txt` — Grok Bot server + 10 OpenBot agents architecture
- **Phase 1 (Option B):** `CIRCUIT_AI_12BOT_PROMPT.txt` — 12-bot Paper trading desk (BTC/ETH)
- **Phase 2 (Option C):** `CIRCUIT_AI_PUMPFUN_PROMPT.txt` — 12-bot Pump.fun memecoin desk
- **How to Run (Option D):** `CURCH_BOT_STARTUP_PROMPT.txt` — step-by-step builder instructions
- **Original prompt:** `CIRCUIT_AI_PROMPT.txt` — legacy 12-bot prompt

After getting replies from Circuit AI, paste generated code here and we fix/verify it.

## DESCRIPTION.md
DESCRIPTION.md has exactly this shape, each line saying what belongs there; publishing rejects any other shape.

## Thesis
One sentence of at most 160 characters: what the agent bets on and how it makes money.

## Strategy
- **Title:** 1 to 3 "- **Title:** rule" lines on what makes it act, when it exits and how it sizes; titles at most 32 characters, each rule one sentence of at most 160.

## Exposure
- **Holds:** At most 24 characters — What your money is in while the agent runs.
- **Venue:** At most 24 characters — Where it trades or deposits, where your funds sit, and any setup you must do.
- **Leverage:** At most 24 characters — How much it borrows to enlarge its positions, or None.
- **Costs:** At most 24 characters — What it pays along the way: trading fees, funding, gas, swaps, bridges.
- **Data:** At most 24 characters — Circuit, or each outside service it calls by host and why Circuit data was not enough.
- **On unwind:** At most 24 characters — What you get back when you close its positions after stopping, and in which asset.

Write for a reader new to trading in everyday words: no internal names, and plain phrases over trading terms ("main account" over "master", "halfway between the buying and selling prices" over "midpoint") without losing their meaning. Each line names this agent's concrete assets, venues, numbers and limits. Titles and answers are short glanceable phrases; details carry the specifics. Write every Exposure line as label, answer, spaced em dash, detail: `- **Leverage:** Up to 3x — Borrows up to three times its USDC to enlarge BTC positions.` Say what the agent does and how it makes money; do not list downsides or caveats. Anything the user must do that the agent cannot goes in Venue. Keep the points of user-supplied description text, moving each into its line and dropping notes meant for the builder. State the behaviour truthfully, without restating implementation or configuration.

## Hyperliquid
`agent.data.markets` has size decimals and the market list; do not call `api.hyperliquid.xyz` for them.

### Naming a market
Pass `venueSymbol` from `agent.data.markets({ venue: "hyperliquid", assetType: "perpetual" })` or `asset` from `spotMarkets.list()` unchanged; it is case-sensitive. Main perps look like `BTC`, builder-dex perps keep their prefix (`xyz:NVDA`), and spot pairs are `@107` or `PURR/USDC`.
The SDK exposes no order book depth, account leverage or maximum trade size, spot midpoints (spot has candles only), or prices fresher than the fifteen-second `mids`.

### An order
`orders.create` takes the reviewed order proposals: `perpOpen` with `side: "long" | "short"`, `perpReduce`, `spotBuy` and `spotSell`, each with `amount: { size } | { valueUsdc }`. `valueUsdc` is order notional in USDC, not margin. Omit `execution` for a market order within one percent of the mid; the engine reads the mid, sets the limit and rounds size to the market's decimals. Pass `{ kind: "limit", price, timeInForce }` only for a price the strategy chose; `"ioc"` cancels what does not cross, `"gtc"` rests until filled or cancelled, and `"alo"` rests as maker only. On `perpReduce`, `{ kind: "takeProfit" | "stopLoss", triggerPrice }` executes at market once the mark crosses it. `orders.listOpen()` lists the session's resting orders, TP/SL included, and `orders.cancel({ orderId })` cancels one.

Hyperliquid refuses an opening order worth under 10 of the quote token at the price it trades.

Circuit charges no builder fee; Hyperliquid's own trading fees apply. An agent may place about fifteen orders a minute; going over pauses all of the agent's sessions.

### Positions and closing
A perp holding's collateral figures are in the collateral token, USDC when `collateralToken` is 0; `priceUsd` is that mark in USD, null when the collateral is not a dollar. Close the session's position with `{ kind: "perpReduce", asset, amount: { size: "max" } }`: it measures the session's own position and sends a plain opposite order.

## Lighter
### Naming a market
Pass `venueSymbol` from `agent.data.markets({ venue: "lighter", assetType: "perpetual" })` unchanged, such as `ETH`. Lighter lists perpetuals only, and mids refresh every minute.

### An order
`agent.lighter.orders.create` takes Hyperliquid's `perpOpen` and `perpReduce` proposals, sized by the engine from the mid. `"gtc"` and `"alo"` limits rest for at most 28 days. The engine rejects any order below the market's minimum size, closes included, and any limit order below its minimum notional. `orders.listOpen()` lists resting orders and `orders.cancel({ orderId })` cancels one. A swap into Lighter USDC from any source opens the account. Standard accounts pay no trading fees; funding is paid hourly.

## Papertrade
`agent.papertrade.positions.open({ asset, side, margin, leverage })` opens one isolated BTC or ETH position at Hyperliquid's mid; notional is margin × leverage, up to 1000×; Papertrade currently requires at least 10 USDC margin and 10,000 USDC notional. Each open is its own position with its own `positionId`: there are no resting orders, partial closes or added margin. `positions.close({ positionIds })` closes up to twelve at once; `account.retrieve()` lists the wallet's open positions with ids, margin and liquidation prices. Winning closes lose a move-dependent haircut and a 2% fee; losses pay nothing extra. A swap from HyperCore USDC into Papertrade USDC (`papertrade`, asset `0`) funds the account, at least 10 USDC at a time. `paper.stake({ amount })` and `paper.unstake({ amount })` move earned PAPER in and out of staking instantly, and `paper.claim()` credits the claimable USDC rewards to the Papertrade balance; `account.retrieve().paper` reports `balance`, `staked` and `rewards`.

## Polymarket
Circuit's data and these SDK calls come first; fetch `clob.polymarket.com` or the Gamma API only for what they cannot answer.

### Finding a market
Never match question or title text or hard-code a resolution time. Ship a single event's `slug`; search each period for a recurring one. Retrieve the event by `slug`, choose the market by structured fields (`endDate`, `groupItemTitle`, `line`, `sportsMarketType`, `gameStartTime`) and the outcome by `outcomes[].name`. Search returns at most 20 active events, which shorter markets can fill on a busy subject. For a recurring market, choose the event whose `endDate` falls on the period's last day: `endDate` can mark that day rather than the closing instant, and `startDate` is a listing time that can fall days into the period. If the choice is not unique, throw naming the candidates. At build time, run the agent's search and selection through the `polymarket` tool.

An order needs the outcome's token id, `outcomes[i].asset`; outcome order is not fixed, so match on `name`. A held outcome carries it as `holding.asset`, a trigger as `agent.trigger.asset`.

### Orders
Every order is a market order against the book; there is no limit price or order type. A buy's `spendPusd` is the most it spends, Polymarket taker fees included, so pass the full stake. Amounts are cut to two decimals, and partial fills return the partial amount. Each market has its own minimum order size, which the SDK does not expose; Polymarket refuses an order below it with `SUBMISSION_REJECTED`. The SDK also exposes no order book depth, tick size, open-order status or payout amounts.

The engine tops up pUSD from USDC.e and sets the exchange allowance itself. Circuit deploys the Deposit Wallet of a wallet it created on first use; an imported wallet's user sets it up before starting. pUSD is the `kind: "token"` holding on `ethereum:137`, so outcome prices are per share in dollars.

### Resolution and redemption
Declare a `resolution` trigger for venue `polymarket` with no asset; it fires once per held outcome whose market resolved, with `agent.trigger` carrying that `asset` and the winning `outcome`. `isRedeemable` on a held outcome is the other signal; skip quoting or selling a held outcome whose `acceptingOrders` is false. Never poll for resolution: `markets.retrieve` throws once a market stops trading.

`agent.polymarket.positions.redeem({ asset })` redeems the asset's whole market, both sides; call it once per `conditionId`, in sequence. A losing position redeems for nothing without error. The result lists shares redeemed, not pUSD received.

## Swaps, vaults and contracts
### Swaps
A swap's two networks may differ; routing picks the bridge. `create` simulates eligible providers and selects the highest output whose guaranteed minimum meets the approved floor. Reviews derive that floor from expected output less slippage, or a higher inherited or explicit minimum; execution preserves it. Pass no `engines` or `slippage` the user did not name, and never pin a quote's provider: estimates are unsimulated, and a pin removes alternatives. Same-chain EVM routes (KyberSwap, Velora, Uniswap) report no venue fees, `venuePriceImpact` only on some Uniswap routes, and gas as `amountUsd` alone; a missing cost field is unreported, not zero and no reason to wait, and the quoted output already reflects price impact. Leave `minimumReceive` out unless the strategy has a price the trade must beat.

`create` takes `amount: "max"` or `{ balancePercent }` of the session's own holding, never more than the wallet can spend after fees; quote's `max: true` sizes to the whole wallet balance.

The engine adds swap approvals itself. Wrapping is a swap to the destination token. A completed swap returns no amounts; the result appears in the next run's allocation.

### Vault deposits and withdrawals
Where the network has the `erc4626` swap provider (`swapProviders` in the network facts), a deposit is a swap from the underlying to the vault's share token and a withdrawal is the reverse, with approval and minimum output handled; never hand-build `deposit` or `redeem` there. Elsewhere, approve the vault for the underlying, then deposit, as two raw transactions.

### Raw transactions
`agent.wallet.transactions.create({ network, request })` simulates before admission; `preview` is optional inspection with no authority. Simulation shows the call would succeed now, not that the contract is the one you think.

### Reading the chain
The SDK has no contract or allowance read and no RPC endpoint. Before reaching outside:
- A vault share balance is the allocation holding whose `asset` is the vault address, marked at net asset value.
- `agent.data.marks({ network, address })` prices an asset the session does not hold. Never value holdings with swap quotes: thin-route price impact looks like a loss.
- `agent.data.yields({ depositToken: [{ network, address: vault }] })`, keyed on the vault, never the underlying, gives APY with and without rewards, TVL, `withdrawalOutcome` and `withdrawableAmount`.
- `agent.transactions.list()` shows what the session's past operations moved, on hosted targets only.

### Arc
On Arc (`ethereum:5042`) USDC is the native dollar and gas token. Its ERC-20 view of the same balance never appears in allocation: treat the native entry as the USDC balance and never add the two. Arc has no `erc4626` provider.

## Version Quick Reference

|| Version | Profile | Key Parameters | Status |
|---------|---------|----------------|--------|
|| v9 | Historical | — | Marked historical |
|| v10_tuned | Tightened paper parameters | PO_STOP_LOSS 0.82, PO_TRAIL 3.0, PO_MIN_BUYS 4, PO_MAX_POOL_FEE 0.04, PO_POSITION_MULT 1.2, PO_ENTRY_MAX 72 | Active trial mode |
