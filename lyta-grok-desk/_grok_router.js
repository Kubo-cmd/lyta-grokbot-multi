// Circuit SDK ambient declarations (resolved by Circuit runtime at load time)
/// <reference path="circuit.d.ts" />
// === LYTA GrokBot Router Agent ===
// Server-side route dispatcher. Receives task payloads from the Grok Bot
// server (xAI managed cloud VM) and routes to the correct desk agent.
// Handles: paper, signal, analyst, trader, risk, spot.
const TARGET_MAP = {
    paper: "paper", circuit: "paper", pd: "paper",
    signal: "signal", scan: "signal", scanner: "signal", sc: "signal",
    analyst: "analyst", analysis: "analyst", risk: "risk", safety: "risk",
    trade: "trader", execute: "trader", exec: "trader",
    spot: "spot", memecoin: "spot", pump: "spot",
    status: "status", info: "status", ls: "status",
    standdown: "standdown", stop: "standdown", pause: "standdown",
};
export const run = async (agent) => {
    await agent.log("=== 🛣️ LYTA GROKBOT ROUTER — task dispatcher ===");
    await agent.log(`[ROUTER] Listening on task queue...`);
    await agent.log(`[ROUTER] Target map: ${Object.entries(TARGET_MAP)
        .map(([k, v]) => `${k}→${v}`).join(", ")}`);
    try {
        const task = await agent.queue?.nextTask?.({
            timeout: 15000,
            poll: true,
        });
        if (!task) {
            await agent.log("[ROUTER] No pending task (poll timeout).");
            return;
        }
        const target = TARGET_MAP[task.target] ?? task.target;
        switch (target) {
            case "paper": {
                await agent.log("[ROUTER] → Routing to lyta-grok-desk-paper (paper desk)");
                const p = task.payload ?? {};
                const m = agent.desktop?.getAgent?.({ agentId: "lyta-grok-desk-paper" });
                if (m) {
                    try {
                        const res = await m?.run?.(p);
                        if (res)
                            await agent.log(`[ROUTER] paper agent returned: ${JSON.stringify(res).slice(0, 300)}`);
                    }
                    catch (e) {
                        await agent.log(`[ROUTER] paper agent run error: ${e?.message ?? e}`, { error: true });
                    }
                }
                break;
            }
            case "signal": {
                await agent.log("[ROUTER] → Routing to signal scanner");
                const m = agent.desktop?.getAgent?.({ agentId: "lyta-grok-desk-signal" });
                if (m) {
                    try {
                        const res = await m?.run?.(task.payload);
                        if (res)
                            await agent.log(`[ROUTER] signal returned: ${JSON.stringify(res).slice(0, 300)}`);
                    }
                    catch (e) {
                        await agent.log(`[ROUTER] signal agent error: ${e?.message ?? e}`, { error: true });
                    }
                }
                break;
            }
            case "analyst": {
                await agent.log("[ROUTER] → Routing to analyst evaluator");
                const m = agent.desktop?.getAgent?.({ agentId: "lyta-grok-desk-analyst" });
                if (m) {
                    try {
                        const res = await m?.run?.(task.payload);
                        if (res)
                            await agent.log(`[ROUTER] analyst returned: ${JSON.stringify(res).slice(0, 300)}`);
                    }
                    catch (e) {
                        await agent.log(`[ROUTER] analyst agent error: ${e?.message ?? e}`, { error: true });
                    }
                }
                break;
            }
            case "trader": {
                await agent.log("[ROUTER] → Routing to trader executor");
                const m = agent.desktop?.getAgent?.({ agentId: "lyta-grok-desk-trader" });
                if (m) {
                    try {
                        const res = await m?.run?.(task.payload);
                        if (res)
                            await agent.log(`[ROUTER] trader returned: ${JSON.stringify(res).slice(0, 300)}`);
                    }
                    catch (e) {
                        await agent.log(`[ROUTER] trader agent error: ${e?.message ?? e}`, { error: true });
                    }
                }
                break;
            }
            case "risk": {
                await agent.log("[ROUTER] → Routing to risk monitor");
                const m = agent.desktop?.getAgent?.({ agentId: "lyta-grok-desk-risk" });
                if (m) {
                    try {
                        const res = await m?.run?.(task.payload);
                        if (res)
                            await agent.log(`[ROUTER] risk returned: ${JSON.stringify(res).slice(0, 300)}`);
                    }
                    catch (e) {
                        await agent.log(`[ROUTER] risk agent error: ${e?.message ?? e}`, { error: true });
                    }
                }
                break;
            }
            case "spot": {
                await agent.log("[ROUTER] → Routing to spot desk");
                const m = agent.desktop?.getAgent?.({ agentId: "lyta-grok-desk-paper" });
                if (m) {
                    try {
                        const res = await m?.run?.(task.payload);
                        if (res)
                            await agent.log(`[ROUTER] spot returned: ${JSON.stringify(res).slice(0, 300)}`);
                    }
                    catch (e) {
                        await agent.log(`[ROUTER] spot agent error: ${e?.message ?? e}`, { error: true });
                    }
                }
                break;
            }
            case "status": {
                const agents = await agent.desktop?.listAgents?.();
                await agent.log(`[ROUTER] Active agents: ${JSON.stringify(agents ?? "none")}`);
                break;
            }
            case "standdown": {
                const t = task;
                const cmd = { standDown: true, reason: t.payload?.reason ?? "manual" };
                await agent.notifications?.post?.({
                    topic: "desktop:stand_down",
                    payload: cmd,
                });
                await agent.log(`[ROUTER] Commands broadcast: stand down (${cmd.reason})`);
                break;
            }
            default:
                await agent.log(`[ROUTER] Unknown target: ${task.target ?? "undefined"}.`);
                break;
        }
    }
    catch (e) {
        await agent.log(`[ROUTER] Task loop error: ${e?.message ?? e}`, { error: true });
    }
};
