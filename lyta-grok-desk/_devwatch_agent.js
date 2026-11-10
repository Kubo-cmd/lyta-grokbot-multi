// === LYTA GrokBot Multi — DEV_WATCH Agent ===
// On-chain wallet monitoring (Hrundel75 rule set): detects dev wallet
// dumping and triggers stand-down. Monitors on-chain behavior; never opens
// positions. Stand-down only.
// Paper-only, no real wallet, no signing, no real capital.
// Dev watches: dev holds >5% → NO BUY; supply to fresh wallets → SELL FIRST;
//              supply to exchange → WATCH.
let standDownTriggered = false;
export const run = async (agent) => {
    await agent.log("=== DEV_WATCH: On-chain wallet monitoring (Hrundel75 rules) ===");
    if (standDownTriggered) {
        await agent.log("[DEV_WATCH] Stand-down active — no further action on this cycle.");
        return;
    }
    const reasons = [];
    try {
        // DEV_WATCH: on-chain wallet tracking (Hrundel75 rule set)
        const wallets = await agent.papertrade?.wallet?.track?.({ scope: "spot" });
        if (wallets && Array.isArray(wallets)) {
            for (const w of wallets) {
                // Rule 1: Dev holds >5% → NO BUY
                if (w.holderPct > 0.05 || w.bundlePct > 0.20) {
                    reasons.push(`Dev wallet ${w.addr} holds ${(w.holderPct * 100).toFixed(1)}% or bundles ${(w.bundlePct * 100).toFixed(1)}% → NO BUY`);
                }
                // Rule 2: Fresh wallets detected → SELL FIRST
                if (w.freshWalletCount > 0) {
                    reasons.push(`New wallets detected (${w.freshWalletCount}) → SELL FIRST`);
                }
                // Rule 3: Supply to exchange → WATCH
                if (w.toExchange) {
                    reasons.push(`Supply to exchange → WATCH`);
                }
            }
            if (reasons.length > 0) {
                await agent.log(`[DEV_WATCH] ${reasons.join(" | ")}`);
                await agent.log("[DEV_WATCH] DEV_WATCH ACTIVE: dev dumping detected → STAND DOWN");
                standDownTriggered = true;
                return;
            }
        }
    }
    catch (e) {
        await agent.log(`[DEV_WATCH] On-chain scan skipped (no wallet tracker: ${String(e)} | ${String(e?.message ?? '')})`);
    }
    await agent.log("[DEV_WATCH] On-chain scan complete — clean. No action needed.");
};
