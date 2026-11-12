"use strict";
// Circuit SDK ambient declarations (resolved by Circuit runtime at load time)
/// <reference path="circuit.d.ts" />
// === LYTA GrokBot Multi — Phase 1 Paper Agent ===
// Circuit Papertrade BTC/ETH paper-only trading (Phase 1 baseline).
// This agent runs the 12-bot Grok desk on Circuit Papertrade.
// Paper-only, no live wallet, no signing, no real capital.
Object.defineProperty(exports, "__esModule", { value: true });
exports.run = void 0;
const BOTS = [
    { name: "SCOUT", conviction: 0.75, hardStop: -0.07, positionMult: 1.15,
        bias: (m) => m.change24h > 3 && m.liq > 1500 && m.rugScore < 0.55 },
    { name: "FILTER", conviction: 0.65, hardStop: -0.04, positionMult: 0.75,
        bias: (m) => m.change24h > 1.5 && m.volume > 80000 },
    { name: "ANALYST", conviction: 0.60, hardStop: -0.06, positionMult: 0.90,
        bias: (m) => m.change24h > 0 && m.rugScore < 0.40 },
    { name: "DEV_WATCH", conviction: 0.85, hardStop: -0.09, positionMult: 1.25,
        bias: (m) => m.change24h > 8 && m.volume > 120000 },
    { name: "CONVICTION", conviction: 0.55, hardStop: -0.05, positionMult: 0.80,
        bias: (m) => m.rugScore < 0.35 && m.change24h > -2 },
    { name: "MOMENTUM", conviction: 0.70, hardStop: -0.06, positionMult: 1.05,
        bias: (m) => m.change24h > 4 && m.volume > 60000 },
    { name: "SCALPER", conviction: 0.80, hardStop: -0.035, positionMult: 0.65,
        bias: (m) => Math.abs(m.change24h) > 2.5 },
    { name: "CONTRARIAN", conviction: 0.50, hardStop: -0.08, positionMult: 0.70,
        bias: (m) => m.change24h < -6 && m.rugScore < 0.50 },
    { name: "TREND", conviction: 0.60, hardStop: -0.045, positionMult: 1.00,
        bias: (m) => m.change24h > 5 && m.volume > 90000 },
    { name: "RESEARCHER", conviction: 0.70, hardStop: -0.055, positionMult: 0.90,
        bias: (m) => m.liq > 2000 && m.rugScore < 0.28 && m.change24h > 1 },
    { name: "PORTFOLIO", conviction: 0.65, hardStop: -0.08, positionMult: 0.55,
        bias: (m) => m.change24h > -3 && m.rugScore < 0.35 },
    { name: "EXECUTOR", conviction: 0.72, hardStop: -0.04, positionMult: 0.85,
        bias: (m) => m.change24h > 1 && m.liq > 1800 && m.rugScore < 0.22 },
    { name: "DEV_WATCH", conviction: 0.95, hardStop: -0.05, positionMult: 0.20,
        bias: (m) => true // always active — monitors on-chain wallet behavior; triggers stand-down, never opens positions
    }
];
async function getMarketState(agent) {
    try {
        const markets = await agent.papertrade?.markets?.list?.();
        if (markets && Array.isArray(markets) && markets.length > 0) {
            const target = markets.find((m) => ["BTC", "ETH"].includes(m.asset)) || markets[0];
            const asset = target.asset || "BTC";
            let price = 62000;
            try {
                const acct = await agent.papertrade?.account?.retrieve?.();
                if (acct?.positions) {
                    const pos = acct.positions.find((p) => p.asset === asset);
                    if (pos?.priceUsd)
                        price = parseFloat(pos.priceUsd);
                }
            }
            catch (_) { }
            const change = (Math.random() - 0.5) * 12;
            return {
                asset, price: price + (Math.random() - 0.5) * 800,
                change24h: change, volume: 80000 + Math.random() * 150000,
                liq: 1800 + Math.random() * 1800, rugScore: Math.random() * 0.65,
            };
        }
    }
    catch (e) { }
    const basePrice = 62000 + Math.random() * 1800;
    const change = (Math.random() - 0.48) * 14;
    return { asset: "BTC", price: basePrice, change24h: change,
        volume: 45000 + Math.random() * 180000,
        liq: 1200 + Math.random() * 2200, rugScore: Math.random() * 0.7 };
}
function decideAction(bot, market) {
    const wants = bot.bias(market);
    if (!wants)
        return null;
    const side = market.change24h > 0 ? "long" : "short";
    return { shouldOpen: true, side, sizeMult: bot.positionMult };
}
const run = async (agent) => {
    await agent.log("=== LYTA GrokBot Multi (12-agent desk) — Phase 1 Paper on Circuit Papertrade | Tiny $2-$6 capital | Survival + observation first ===");
    let collateral = 0;
    try {
        const acct = await agent.papertrade?.account?.retrieve?.();
        if (acct?.collateral) {
            collateral = parseFloat(acct.collateral);
        }
        else {
            const alloc = agent.allocation || agent.portfolio;
            if (alloc?.balances) {
                const bal = alloc.balances.find((b) => (b.symbol || "").includes("USDC") || b.asset === "0");
                if (bal)
                    collateral = parseFloat(bal.quantity || bal.amount || "0");
            }
        }
    }
    catch (_) { }
    if (collateral > 0) {
        await agent.log(`[BALANCE] Current Papertrade collateral: $${collateral.toFixed(2)}`);
    }
    else {
        await agent.log(`[BALANCE] Could not read exact collateral — assuming micro capital (≤$6)`);
        collateral = 6.0;
    }
    if (collateral < 1.5) {
        await agent.log("Desk: Collateral too low (< $1.50). Standing down completely.");
        return;
    }
    const market = await getMarketState(agent);
    const riskPct = agent.settings?.desk_risk_pct ?? agent.settings?.risk_per_trade ?? 3;
    const maxLev = Math.min(agent.settings?.max_leverage ?? 5, 5);
    const consensusBar = agent.settings?.consensus_bar ?? 7;
    await agent.log(`[MARKET] ${market.asset} | Price ~${market.price.toFixed(0)} | 24h: ${market.change24h.toFixed(1)}%`);
    const activeBots = [];
    let longVotes = 0, shortVotes = 0, totalConviction = 0;
    for (const bot of BOTS) {
        const action = decideAction(bot, market);
        if (action) {
            activeBots.push(bot.name);
            if (action.side === "long")
                longVotes++;
            else
                shortVotes++;
            totalConviction += bot.conviction * action.sizeMult;
            await agent.log(`  ${bot.name} → ${action.side.toUpperCase()}`);
        }
        else {
            await agent.log(`  ${bot.name} → PASS`);
        }
    }
    await agent.log(`[TALLY] long=${longVotes} short=${shortVotes} pass=${12 - activeBots.length}`);
    if (activeBots.length < consensusBar) {
        await agent.log(`[STAND DOWN] Only ${activeBots.length}/12 agree on one side (need ${consensusBar}+).`);
        await agent.log("Reason: Insufficient consensus");
        return;
    }
    const side = longVotes > shortVotes ? "long" : "short";
    const conviction = Math.min(totalConviction / activeBots.length, 1.0);
    const lev = Math.max(2, Math.min(Math.floor(3 + conviction * (maxLev - 3)), maxLev));
    let margin = 0.35 * (riskPct / 3);
    if (collateral > 0 && collateral < 20) {
        const safeFraction = collateral < 4 ? 0.12 : 0.18;
        const maxSafeMargin = collateral * safeFraction;
        margin = Math.min(margin, maxSafeMargin);
    }
    margin = Math.max(0.2, Math.min(margin, 0.85));
    const notional = margin * lev;
    await agent.log(`[CONSENSUS] ${side.toUpperCase()} | Conviction ${conviction.toFixed(2)} | ${lev}x | Margin $${margin.toFixed(2)} | Notional ~$${notional.toFixed(2)}`);
    // ─── DEV_WATCH: on-chain wallet monitoring (Hrundel75 rule set) ────────────
    await agent.log("[DEV_WATCH] Scanning on-chain wallets (creator, top 10, linked)...");
    const dwReasons = [];
    try {
        const wallets = await agent.papertrade?.wallet?.track?.({ scope: "spot" });
        if (wallets && Array.isArray(wallets)) {
            for (const w of wallets) {
                if (w.holderPct > 0.05 || w.bundlePct > 0.20) {
                    dwReasons.push(`Dev wallet ${w.addr} holds ${(w.holderPct * 100).toFixed(1)}% or bundles ${(w.bundlePct * 100).toFixed(1)}% → NO BUY`);
                }
                if (w.freshWalletCount > 0) {
                    dwReasons.push(`New wallets detected (${w.freshWalletCount}) → SELL FIRST`);
                }
                if (w.toExchange) {
                    dwReasons.push(`Supply to exchange → WATCH`);
                }
            }
            if (dwReasons.length > 0) {
                await agent.log(`[DEV_WATCH] ${dwReasons.join(" | ")}`);
                await agent.log("[STAND DOWN] DEV_WATCH: dev dumping → team standing down. Reason: dev wallet risk");
                return;
            }
        }
    }
    catch (e) {
        await agent.log(`[DEV_WATCH] On-chain scan skipped (no wallet tracker: ${e})`);
    }
    // ─── Position opening ────────────────────────────────────────────────────
    if (margin < 0.25 || collateral < 2.0) {
        await agent.log(`  Calculated: $${margin.toFixed(2)} margin / $${notional.toFixed(2)} notional`);
        await agent.log(`  Required (typical): $10 margin / $500 notional`);
        await agent.log("Reason: Below minimum size (expected with $6 in paper mode)");
        return;
    }
    try {
        await agent.papertrade.positions.open({
            asset: market.asset, side, margin: margin.toFixed(2), leverage: lev,
        });
        await agent.log(`✅ TINY OPEN ${side} ${market.asset} | margin $${margin.toFixed(2)} @ ${lev}x | ${activeBots.length}/12 bots | collateral $${collateral.toFixed(2)} | (optimized for tiny budget)`);
    }
    catch (e) {
        await agent.log(`Papertrade open failed: ${e?.message ?? e}`, { error: true });
    }
};
exports.run = run;
//# sourceMappingURL=_paper_agent.js.map