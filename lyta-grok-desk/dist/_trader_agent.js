"use strict";
// Circuit SDK ambient declarations (resolved by Circuit runtime at load time)
/// <reference path="circuit.d.ts" />
// === LYTA GrokBot Trader Agent ===
// Micro-sizing execution engine. Converts a comma-separated signal list into
// real (paper-only) open orders with clamp($0.20-$0.85) and risk-based sizing.
// Pure execution — only calls positions.open (Circuit Papertrade).
Object.defineProperty(exports, "__esModule", { value: true });
exports.run = void 0;
const run = async (agent) => {
    await agent.log(`=== 🛒 LYTA GROKBOT TRADER — micro-sizing from signal list ===`);
    const signals = [];
    try {
        const raw = await agent.signals?.get?.("tradable");
        if (Array.isArray(raw)) {
            for (const s of raw) {
                signals.push({
                    name: s.name ?? s.symbol ?? "UNKNOWN",
                    side: s.side ?? "long",
                    margin: (s.margin ?? 0.40) * (agent.settings?.risk_adjustment ?? 1),
                    leverage: s.leverage ?? (agent.settings?.max_leverage ?? 5),
                });
            }
        }
    }
    catch (_) { }
    const settings = agent.settings ?? {};
    const maxLev = Math.min(parseFloat(settings.max_leverage ?? "5"), 5);
    const minMargin = parseFloat(settings.micro_size_min ?? "0.20");
    const maxMargin = parseFloat(settings.micro_size_max ?? "0.85");
    const posLimit = parseFloat(settings.max_open_positions ?? "1");
    const coll = parseFloat(agent.papertrade?.account?.retrieve?.()?.collateral ?? "0") ||
        parseFloat(agent.allocation?.balances?.[0]?.quantity ?? "0") ||
        parseFloat(agent.papertrade?.account?.get?.()?.collateral ?? "0") || 6.0;
    await agent.log(`[SETTINGS] coll=$${coll.toFixed(2)} maxLev=${maxLev}x minMargin=${minMargin} maxMargin=${maxMargin} posLimit=${posLimit}`);
    if (signals.length === 0) {
        await agent.log(`[TRADER] No tradable signals in queue. Standing down.`);
        return;
    }
    // Enforce open position cap
    const openPos = await agent.papertrade?.positions?.list?.();
    const openCount = openPos?.length ?? 0;
    if (openCount >= posLimit) {
        await agent.log(`[TRADER] Position cap reached (${openCount}/${posLimit}). Standing down.`);
        return;
    }
    await agent.log(`[TRADER] ${signals.length} tradable signal(s), open=${openCount}/${posLimit}`);
    for (const sig of signals) {
        // Micro-sizing clamp
        const margin = Math.max(minMargin, Math.min(maxMargin, 0.35 * (agent.settings?.desk_risk_pct ?? 3) / 3));
        const lev = Math.min(maxLev, Math.max(2, sig.leverage ?? maxLev));
        const notional = margin * lev;
        if (notional < 500) {
            await agent.log(`  ⚠ ${sig.name}: notional $${notional.toFixed(2)} < $500 — cancelling (too small for paper)`);
            continue;
        }
        try {
            await agent.papertrade.positions.open({
                asset: sig.name,
                side: sig.side,
                margin: margin.toFixed(2),
                leverage: lev,
            });
            await agent.log(`  ✅ MICRO BUY ${sig.side} ${sig.name} | $${margin.toFixed(2)} @ ${lev}x | coll $${coll.toFixed(2)}`);
        }
        catch (e) {
            await agent.log(`  ❌ Failed ${sig.side} ${sig.name}: ${e?.message ?? e}`, { error: true });
        }
    }
    await agent.log(`[TRADER] Finished — no further actions.`);
};
exports.run = run;
//# sourceMappingURL=_trader_agent.js.map