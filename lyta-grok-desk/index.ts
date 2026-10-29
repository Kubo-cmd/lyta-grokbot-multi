import type { RunFunction, AgentContext } from "circuit:sdk";

// === 12-Agent Grok Desk (inspired by LYTA GrokBot Multi) ===
// Each "bot" has a personality with bias toward different conditions.
// In this starter we run them against Papertrade (popular on Circuit for high-leverage PAPER farming).
// Start with circuit run --simulated

type BotName =
  | "SCOUT" | "FILTER" | "ANALYST" | "PUMP_CHASER" | "CONVICTION"
  | "MOMENTUM" | "SCALPER" | "CONTRARIAN" | "TREND"
  | "RESEARCHER" | "PORTFOLIO" | "EXECUTOR";

interface BotProfile {
  name: BotName;
  conviction: number;
  hardStop: number;      // negative = loss tolerance
  positionMult: number;
  bias: (market: MarketState) => boolean;
}

interface MarketState {
  asset: string;
  price: number;
  change24h: number;
  volume: number;
  liq: number;
  rugScore: number;   // 0-1 lower is better
}

const BOTS: BotProfile[] = [
  {
    name: "SCOUT",
    conviction: 0.75,
    hardStop: -0.07,
    positionMult: 1.15,
    bias: (m) => m.change24h > 3 && m.liq > 1500 && m.rugScore < 0.55,
  },
  {
    name: "FILTER",
    conviction: 0.65,
    hardStop: -0.04,
    positionMult: 0.75,
    bias: (m) => m.change24h > 1.5 && m.volume > 80000,
  },
  {
    name: "ANALYST",
    conviction: 0.60,
    hardStop: -0.06,
    positionMult: 0.90,
    bias: (m) => m.change24h > 0 && m.rugScore < 0.4,
  },
  {
    name: "PUMP_CHASER",
    conviction: 0.85,
    hardStop: -0.09,
    positionMult: 1.25,
    bias: (m) => m.change24h > 8 && m.volume > 120000,
  },
  {
    name: "CONVICTION",
    conviction: 0.55,
    hardStop: -0.05,
    positionMult: 0.80,
    bias: (m) => m.rugScore < 0.35 && m.change24h > -2,
  },
  {
    name: "MOMENTUM",
    conviction: 0.70,
    hardStop: -0.06,
    positionMult: 1.05,
    bias: (m) => m.change24h > 4 && m.volume > 60000,
  },
  {
    name: "SCALPER",
    conviction: 0.80,
    hardStop: -0.035,
    positionMult: 0.65,
    bias: (m) => Math.abs(m.change24h) > 2.5,
  },
  {
    name: "CONTRARIAN",
    conviction: 0.50,
    hardStop: -0.08,
    positionMult: 0.70,
    bias: (m) => m.change24h < -6 && m.rugScore < 0.5,
  },
  {
    name: "TREND",
    conviction: 0.60,
    hardStop: -0.045,
    positionMult: 1.00,
    bias: (m) => m.change24h > 5 && m.volume > 90000,
  },
  {
    name: "RESEARCHER",
    conviction: 0.70,
    hardStop: -0.055,
    positionMult: 0.90,
    bias: (m) => m.liq > 2000 && m.rugScore < 0.28 && m.change24h > 1,
  },
  {
    name: "PORTFOLIO",
    conviction: 0.65,
    hardStop: -0.08,
    positionMult: 0.55,
    bias: (m) => m.change24h > -3 && m.rugScore < 0.35,
  },
  {
    name: "EXECUTOR",
    conviction: 0.72,
    hardStop: -0.04,
    positionMult: 0.85,
    bias: (m) => m.change24h > 1 && m.liq > 1800 && m.rugScore < 0.22,
  },
];

function getMarketState(agent: AgentContext): MarketState {
  // In real runs this would pull from agent.data or perps markets.
  // For now we synthesize realistic variation so the desk can make decisions in simulation.
  const basePrice = 62000 + Math.random() * 1800;
  const change = (Math.random() - 0.48) * 14; // -7% to +7% ish
  return {
    asset: "BTC",
    price: basePrice,
    change24h: change,
    volume: 45000 + Math.random() * 180000,
    liq: 1200 + Math.random() * 2200,
    rugScore: Math.random() * 0.7,
  };
}

function decideAction(bot: BotProfile, market: MarketState, riskPct: number): { shouldOpen: boolean; side: "long" | "short"; sizeMult: number } | null {
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
  const market = getMarketState(agent);
  const riskPct = (agent.settings.desk_risk_pct as number) ?? 8;
  const maxLev = (agent.settings.max_leverage as number) ?? 20;

  const activeBots: string[] = [];
  let longVotes = 0;
  let shortVotes = 0;
  let totalConviction = 0;

  for (const bot of BOTS) {
    const action = decideAction(bot, market, riskPct);
    if (action) {
      activeBots.push(bot.name);
      if (action.side === "long") longVotes++;
      else shortVotes++;
      totalConviction += bot.conviction * action.sizeMult;
    }
  }

  await agent.log(
    `[DESK] Market ${market.asset} ${market.change24h.toFixed(1)}% | Active: ${activeBots.length}/12 (${activeBots.slice(0,4).join(", ")}...)`
  );

  if (activeBots.length === 0) {
    await agent.log("Desk: No strong signals this cycle. Standing down.");
    return;
  }

  const side = longVotes > shortVotes ? "long" : "short";
  const conviction = Math.min(totalConviction / activeBots.length, 1.0);
  const lev = Math.min(Math.floor(5 + conviction * (maxLev - 5)), maxLev);

  // MICRO CAPITAL MODE — you only have ~$6 paper
  // We size extremely small so we don't blow the tiny account on one bad move.
  // Base notional is tiny, then capped at ~15% of whatever collateral we can see.
  let notional = 3.5 * (riskPct / 5); // base ~3.5 for $6 account, scaled by your risk setting

  // Try to respect actual balance if the platform gives it to us
  try {
    const account = (agent as any).account;
    if (account && account.collateral) {
      const collat = parseFloat(account.collateral);
      if (collat > 0 && collat < 50) {
        // we are in micro mode
        const maxRiskNotional = collat * 0.18; // never risk more than ~18% of tiny balance
        notional = Math.min(notional, maxRiskNotional);
      }
    }
  } catch (_) {
    // fallback to safe micro size
  }

  // Final safety: never try to use more than $4-5 notional with $6
  notional = Math.min(notional, 4.5);

  await agent.log(
    `[DESK] Consensus ${side.toUpperCase()} | Conviction ${conviction.toFixed(2)} | Lev ${lev}x | Bots: ${activeBots.length} | Size $${notional.toFixed(2)} (micro-capital mode)`
  );

  try {
    // Papertrade open — the main way agents trade on Circuit
    await (agent as any).papertrade.open({
      asset: market.asset,
      side,
      amount: { value: notional.toFixed(2) },
      leverage: lev,
    });

    await agent.log(
      `Opened ${side} ${market.asset} @ ~${market.price.toFixed(0)} | ${activeBots.length} bots agreed | using tiny size`
    );
  } catch (e: any) {
    await agent.log(`Papertrade open failed: ${e?.message ?? e}`, { error: true });
  }
};
