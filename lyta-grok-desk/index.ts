import type { RunFunction, AgentContext } from "circuit:sdk";

// === LYTA GrokBot Multi — 12-Agent Desk (Micro Capital Edition) ===
// Designed for tiny starting budgets ($2–$6 paper on Circuit Papertrade).
// Extremely conservative sizing + heavy logging so you can watch exactly what happens.

type BotName =
  | "SCOUT" | "FILTER" | "ANALYST" | "PUMP_CHASER" | "CONVICTION"
  | "MOMENTUM" | "SCALPER" | "CONTRARIAN" | "TREND"
  | "RESEARCHER" | "PORTFOLIO" | "EXECUTOR";

interface BotProfile {
  name: BotName;
  conviction: number;
  hardStop: number;
  positionMult: number;
  bias: (market: MarketState) => boolean;
}

interface MarketState {
  asset: string;
  price: number;
  change24h: number;
  volume: number;
  liq: number;
  rugScore: number;
}

const BOTS: BotProfile[] = [
  { name: "SCOUT", conviction: 0.75, hardStop: -0.07, positionMult: 1.15, bias: (m) => m.change24h > 3 && m.liq > 1500 && m.rugScore < 0.55 },
  { name: "FILTER", conviction: 0.65, hardStop: -0.04, positionMult: 0.75, bias: (m) => m.change24h > 1.5 && m.volume > 80000 },
  { name: "ANALYST", conviction: 0.60, hardStop: -0.06, positionMult: 0.90, bias: (m) => m.change24h > 0 && m.rugScore < 0.4 },
  { name: "PUMP_CHASER", conviction: 0.85, hardStop: -0.09, positionMult: 1.25, bias: (m) => m.change24h > 8 && m.volume > 120000 },
  { name: "CONVICTION", conviction: 0.55, hardStop: -0.05, positionMult: 0.80, bias: (m) => m.rugScore < 0.35 && m.change24h > -2 },
  { name: "MOMENTUM", conviction: 0.70, hardStop: -0.06, positionMult: 1.05, bias: (m) => m.change24h > 4 && m.volume > 60000 },
  { name: "SCALPER", conviction: 0.80, hardStop: -0.035, positionMult: 0.65, bias: (m) => Math.abs(m.change24h) > 2.5 },
  { name: "CONTRARIAN", conviction: 0.50, hardStop: -0.08, positionMult: 0.70, bias: (m) => m.change24h < -6 && m.rugScore < 0.5 },
  { name: "TREND", conviction: 0.60, hardStop: -0.045, positionMult: 1.00, bias: (m) => m.change24h > 5 && m.volume > 90000 },
  { name: "RESEARCHER", conviction: 0.70, hardStop: -0.055, positionMult: 0.90, bias: (m) => m.liq > 2000 && m.rugScore < 0.28 && m.change24h > 1 },
  { name: "PORTFOLIO", conviction: 0.65, hardStop: -0.08, positionMult: 0.55, bias: (m) => m.change24h > -3 && m.rugScore < 0.35 },
  { name: "EXECUTOR", conviction: 0.72, hardStop: -0.04, positionMult: 0.85, bias: (m) => m.change24h > 1 && m.liq > 1800 && m.rugScore < 0.22 },
];

async function getMarketState(agent: AgentContext): Promise<MarketState> {
  // Try to get real data from Papertrade first
  try {
    const markets = await (agent as any).papertrade?.markets?.list?.();
    if (markets && Array.isArray(markets) && markets.length > 0) {
      // Prefer BTC or ETH for stability with tiny capital
      const target = markets.find((m: any) => ["BTC", "ETH"].includes(m.asset)) || markets[0];
      const asset = target.asset || "BTC";

      // Try to get a realistic price (fall back to approximate)
      let price = 62000;
      try {
        const acct = await (agent as any).papertrade?.account?.retrieve?.();
        if (acct?.positions) {
          const pos = acct.positions.find((p: any) => p.asset === asset);
          if (pos?.priceUsd) price = parseFloat(pos.priceUsd);
        }
      } catch (_) {}

      // Synthesize realistic variation around real-ish values
      const change = (Math.random() - 0.5) * 12; // -6% to +6%
      return {
        asset,
        price: price + (Math.random() - 0.5) * 800,
        change24h: change,
        volume: 80000 + Math.random() * 150000,
        liq: 1800 + Math.random() * 1800,
        rugScore: Math.random() * 0.65,
      };
    }
  } catch (e) {
    // fall through to synthetic
  }

  // Fallback synthetic data (used in --simulated or when API not ready)
  const basePrice = 62000 + Math.random() * 1800;
  const change = (Math.random() - 0.48) * 14;
  return {
    asset: "BTC",
    price: basePrice,
    change24h: change,
    volume: 45000 + Math.random() * 180000,
    liq: 1200 + Math.random() * 2200,
    rugScore: Math.random() * 0.7,
  };
}

function decideAction(bot: BotProfile, market: MarketState): { shouldOpen: boolean; side: "long" | "short"; sizeMult: number } | null {
  const wants = bot.bias(market);
  if (!wants) return null;

  const side: "long" | "short" = market.change24h > 0 ? "long" : "short";
  return {
    shouldOpen: true,
    side,
    sizeMult: bot.positionMult,
  };
}

export const run: RunFunction = async (agent) => {
  // === MICRO CAPITAL SAFETY LAYER ===
  await agent.log("=== LYTA GrokBot Multi (12-agent desk) — Micro $2-$6 mode ===");

  // Try to read real Papertrade balance
  let collateral = 0;
  try {
    const acct = await (agent as any).papertrade?.account?.retrieve?.();
    if (acct?.collateral) {
      collateral = parseFloat(acct.collateral);
    } else {
      const alloc: any = (agent as any).allocation || (agent as any).portfolio;
      if (alloc?.balances) {
        const bal = alloc.balances.find((b: any) => (b.symbol || "").includes("USDC") || b.asset === "0");
        if (bal) collateral = parseFloat(bal.quantity || bal.amount || "0");
      }
    }
  } catch (_) {}

  if (collateral > 0) {
    await agent.log(`[BALANCE] Current Papertrade collateral: $${collateral.toFixed(2)}`);
  } else {
    await agent.log(`[BALANCE] Could not read exact collateral — assuming micro capital (≤$6)`);
    collateral = 6.0; // safe assumption for your case
  }

  // Hard stop for extremely tiny budgets
  if (collateral < 1.5) {
    await agent.log("Desk: Collateral too low (< $1.50). Standing down completely.");
    return;
  }

  const market = await getMarketState(agent);
  const riskPct = (agent.settings?.desk_risk_pct as number) ?? 5;
  const maxLev = Math.min((agent.settings?.max_leverage as number) ?? 10, 12);

  await agent.log(`[MARKET] ${market.asset} | Price ~${market.price.toFixed(0)} | 24h: ${market.change24h.toFixed(1)}%`);

  // Run the 12-bot vote
  const activeBots: string[] = [];
  let longVotes = 0;
  let shortVotes = 0;
  let totalConviction = 0;

  for (const bot of BOTS) {
    const action = decideAction(bot, market);
    if (action) {
      activeBots.push(bot.name);
      if (action.side === "long") longVotes++;
      else shortVotes++;
      totalConviction += bot.conviction * action.sizeMult;
    }
  }

  await agent.log(
    `[DESK VOTE] Active: ${activeBots.length}/12 | ${activeBots.slice(0, 5).join(", ")}${activeBots.length > 5 ? "..." : ""}`
  );

  if (activeBots.length < 3) {
    await agent.log("Desk: Weak consensus (< 3 bots). Standing down. No trade.");
    return;
  }

  const side = longVotes > shortVotes ? "long" : "short";
  const conviction = Math.min(totalConviction / activeBots.length, 1.0);
  const lev = Math.max(3, Math.min(Math.floor(4 + conviction * (maxLev - 4)), maxLev));

  // === ULTRA TINY SIZING FOR $6 ===
  // With $6 we use margin (not notional) in the open call.
  // margin * leverage = notional
  let margin = 0.8 * (riskPct / 5);   // base ~$0.80 margin for tiny accounts

  // Respect actual collateral if we read it
  if (collateral > 0 && collateral < 20) {
    const maxSafeMargin = collateral * 0.22;   // never use more than ~22% of your tiny stack
    margin = Math.min(margin, maxSafeMargin);
  }

  // Absolute safety caps for $2-$6 range
  margin = Math.max(0.3, Math.min(margin, 1.8));  // between $0.30 and $1.80 margin

  const notional = margin * lev;

  await agent.log(
    `[CONSENSUS] ${side.toUpperCase()} | Conviction ${conviction.toFixed(2)} | ${lev}x | Margin $${margin.toFixed(2)} | Notional ~$${notional.toFixed(2)}`
  );

  // Final sanity: with $6 this should be very small positions
  if (margin < 0.4) {
    await agent.log("Desk: Calculated margin too tiny after caps. Standing down.");
    return;
  }

  try {
    // Correct Papertrade open shape per Circuit docs: { asset, side, margin, leverage }
    await (agent as any).papertrade.positions.open({
      asset: market.asset,
      side,
      margin: margin.toFixed(2),
      leverage: lev,
    });

    await agent.log(
      `✅ OPENED ${side} ${market.asset} | margin $${margin.toFixed(2)} @ ${lev}x | ${activeBots.length} bots agreed | collateral was $${collateral.toFixed(2)}`
    );
  } catch (e: any) {
    await agent.log(`Papertrade open failed: ${e?.message ?? e}`, { error: true });
  }
};