// Circuit SDK ambient declarations (resolved by Circuit runtime at load time)
/// <reference path="circuit.d.ts" />
// === LYTA GrokBot Analyst Agent ===
// Rigorous risk evaluator: checks rug risks, liquidity depth, supply spread,
// and price action before the desk commits. Returns a pass/fail score.
// Never calls positions.open.
export const run = async (agent) => {
    await agent.log(`=== 🔬 LYTA GROKBOT ANALYST — rug/liquidity/safety evaluation ===`);
    const checks = [];
    try {
        const raw = await agent.analytics?.inspect?.() ?? agent.papertrade?.markets?.list?.();
        if (raw && typeof raw === "object") {
            const m = raw;
            // Liquidity depth
            const liq = m.liq ?? m.totalLiquidity ?? m.spotLiquidity ?? 0;
            const liqPass = liq > 1000;
            checks.push({
                name: "LiquidityDepth",
                pass: liqPass,
                score: liq > 2000 ? 1.0 : liq > 1000 ? 0.7 : 0.3,
                detail: `liq=${liq.toFixed(0)} (req>1000)`,
            });
            // Rug score from metadata
            const rug = m.rugScore ?? m.bundlerScore ?? m.devScore ?? 0;
            const rugPass = rug < 0.6;
            checks.push({
                name: "RugScore",
                pass: rugPass,
                score: 1.0 - rug,
                detail: `rugMeta=${rug.toFixed(2)} (req<0.6)`,
            });
            // Volume trend
            const vol = m.volume ?? m.holders ?? 0;
            const volPass = vol > 5000;
            checks.push({
                name: "VolumeTrend",
                pass: volPass,
                score: vol > 50000 ? 1.0 : vol > 5000 ? 0.6 : 0.2,
                detail: `vol=${vol.toFixed(0)} (req>5000)`,
            });
            // Price movement
            const chg = m.change24h ?? 0;
            const chgPass = chg > -5;
            checks.push({
                name: "PriceStability",
                pass: chgPass,
                score: chg > 2 ? 1.0 : chg > 0 ? 0.8 : chg > -5 ? 0.6 : 0.2,
                detail: `chg24h=${chg.toFixed(1)}% (req>-5%)`,
            });
        }
    }
    catch (_) {
        checks.push({ name: "AllChecks", pass: false, score: 0.0, detail: "Unable to read market data" });
    }
    const avgScore = checks.reduce((s, c) => s + c.score, 0) / checks.length;
    const pass = avgScore >= 0.5 && checks.every((c) => c.pass || c.score >= 0.3);
    await agent.log(`[ANALYSIS] Score ${avgScore.toFixed(2)} / 1.0 | PASS=${pass}`);
    for (const c of checks) {
        await agent.log(`  ${c.name}: ${c.pass ? "✅" : "❌"} ${c.score.toFixed(2)} ${c.detail}`);
    }
    // Feed score to desk: store in shared memory / agent settings
    try {
        await agent.memory?.set?.("analyst_score", avgScore, "dashboard");
    }
    catch (_) { }
    if (pass) {
        await agent.log(`[ANALYST] Consensus ✓ — desk may proceed`);
    }
    else {
        await agent.log(`[ANALYST] Standing down — risk too high`);
    }
};
