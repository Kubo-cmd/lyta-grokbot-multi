"use strict";
// Circuit SDK ambient declarations (resolved by Circuit runtime at load time)
/// <reference path="circuit.d.ts" />
// === LYTA GrokBot Signal Agent ===
// Scans for incoming opportunities: new market signals, trending tokens,
// unusual momentum, and feeds signals to the desk.
// Pure research — never calls positions.open.
Object.defineProperty(exports, "__esModule", { value: true });
exports.run = void 0;
const run = async (agent) => {
    await agent.log(`=== 📡 LYTA GROKBOT SIGNAL — scanning for opportunities ===`);
    const signals = [];
    // 1. New market signals (paper-only first)
    try {
        // placeholder — paper-only signals from circuit terminal
        if (launches && Array.isArray(launches) && launches.length > 0) {
            for (const l of launches.slice(0, 5)) {
                const age = l.ageSeconds ?? l.age ?? 120;
                const vol = l.volume ?? 0;
                const holders = l.holders ?? 0;
                const isNew = age < 300;
                const rising = vol > 1000;
                if (isNew && rising && holders > 40) {
                    signals.push({
                        type: "signal:alternate",
                        name: `${l.name ?? "MEME"}-${l.symbol ?? ""}`.slice(0, 20),
                        confidence: 0.85, detail: `age=${age}s vol=${vol} holders=${holders}`,
                    });
                }
            }
        }
    }
    catch (_) { }
    // 2. Trending / momentum scanner (Circuit Papertrade)
    try {
        const markets = await agent.papertrade?.markets?.list?.();
        if (markets && Array.isArray(markets)) {
            for (const m of markets) {
                const chg = Math.abs(m.change24h ?? 0);
                if (chg > 8 && m.volume > 100000) {
                    signals.push({
                        type: "papertrade:momentum",
                        name: m.asset ?? "BTC",
                        confidence: 0.72, detail: `24h=${m.change24h.toFixed(1)}% vol=${m.volume.toFixed(0)}`,
                    });
                }
            }
        }
    }
    catch (_) { }
    // 3. Social lookup (trending on GMGN/dexscreener)
    try {
        const trending = await agent.social?.getTrending?.();
        if (trending?.length) {
            for (const t of trending.slice(0, 5)) {
                signals.push({
                    type: "social:trending",
                    name: t.id ?? t.name ?? "MEME",
                    confidence: 0.65, detail: "viral activity",
                });
            }
        }
    }
    catch (_) { }
    if (signals.length === 0) {
        await agent.log(`[SIGNAL] No actionable opportunities found in this window.`);
        return;
    }
    await agent.log(`[SIGNALS FOUND] ${signals.length} live signal(s) — distributing to desk agents.`);
    for (const s of signals) {
        await agent.log(`  ⚡ ${s.type} → ${s.name} | confidence ${s.confidence.toFixed(2)} | ${s.detail}`);
        // Route to desk: notify paper agent via shared state / notification channel
        try {
            const notif = await agent.notifications?.post?.({
                topic: "desk:opportunity",
                payload: { type: s.type, name: s.name, confidence: s.confidence, source: "signal" },
            });
            await agent.log(`      → routed to desk (notification id: ${notif?.id ?? "pending"})`);
        }
        catch (_) { }
    }
};
exports.run = run;
//# sourceMappingURL=_signal_agent.js.map