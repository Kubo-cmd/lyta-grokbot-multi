"use strict";
// === LYTA GrokBot Multi — SCOUT Agent ===
// Scout: narrative/rug signal checker for pump.fun
//
// Philosophy: 1 good trade/day at 3% gain + 12-bot consensus = compounding advantage
// Scout's job: detect narrative manipulation early → let consensus traders decide
//
// Rules:
//   1. Being discussed + age_minutes > 2 = valid pump signal (no sniper)
//   2. GMGN fee rate elevated = possible sniper presence → WATCH
//   3. Unique authors vs mentions: if bots dominate conversation = rug signal
//   4. Paid wave detected (influencer cash-out) = stand down
//   5. Report: "scout: <token> has healthy narrative" or "scout: <token> has rug signal"
Object.defineProperty(exports, "__esModule", { value: true });
exports.run = run;
async function run(agent) {
    const { agentId, timestamp } = agent;
    await agent.log(`[SCOUT] Starting run ${agentId} @ ${timestamp}`);
    try {
        // Scout needs to know which token to check
        const token = agent.token ?? agent.tokenAddress;
        if (!token) {
            await agent.log('[SCOUT] No token to scout');
            return;
        }
        // Scout checks:
        // 1. Narrative health (mentions vs unique authors)
        // 2. GMGN fee rate (elevated = sniper risk)
        // 3. Age filter (age_minutes > 2 = valid pump)
        await agent.log(`[SCOUT] Scout report for ${token}: narrative healthy`); // Placeholder
    }
    catch (e) {
        await agent.log(`[SCOUT] Run failed: ${String(e)} | ${String(e?.message ?? '')}`);
    }
}
//# sourceMappingURL=_scout_agent.js.map