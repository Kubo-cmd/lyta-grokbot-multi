// Circuit SDK ambient declarations (resolved by Circuit runtime at load time)
/// <reference path="circuit.d.ts" />
// === LYTA GrokBot Risk Agent ===
// Stand-down manager. Monitors for instability, low collateral, or consensus
// collapse. Commands the desk to stand down when risk exceeds thresholds.
// Never calls positions.open.

import type { RunFunction } from "circuit:sdk";

export const run: RunFunction = async (agent: any) => {
  await agent.log("=== 🛡️ LYTA GROKBOT RISK — 6-point stand-down monitor ===");

  const rules = [
    {
      name: "CollateralFloor",
      check: () => {
        try {
          const coll = parseFloat(
            (agent as any).papertrade?.account?.retrieve?.()?.collateral ??
              (agent as any).allocation?.balances?.[0]?.quantity ??
              (agent as any).papertrade?.account?.get?.()?.collateral ??
              "0"
          ) || 0;
          const limit = agent.settings?.min_collateral ?? 1.5;
          return { passed: coll >= limit, reason: `collateral=$${coll.toFixed(2)} < $${limit.toFixed(2)}` };
        } catch {
          return { passed: false, reason: "Cannot read collateral" };
        }
      },
    },
    {
      name: "ConsensusCollapse",
      check: () => {
        try {
          const active = agent.context?.desktop?.runningAgents ?? 0;
          if (active < 3) return { passed: false, reason: `Only ${active} agents active` };
          return { passed: true, reason: `${active} agents active — healthy` };
        } catch {
          return { passed: true, reason: "Mono agent running" };
        }
      },
    },
    {
      name: "LiquidityDrop",
      check: () => {
        try {
          const m = (agent as any).papertrade?.markets?.list?.() ?? null;
          if (!m) return { passed: true, reason: "No market data" };
          const liq = m.liq ?? m.totalLiquidity ?? m.spotLiquidity ?? 0;
          return { passed: liq > 500, reason: `liq=${liq.toFixed(0)}` };
        } catch {
          return { passed: true, reason: "No data" };
        }
      },
    },
    {
      name: "RugFlag",
      check: () => {
        try {
          const raw = (agent as any).analytics?.inspect?.() ?? null;
          if (!raw) return { passed: true, reason: "No rug data" };
          const rug = raw.rugScore ?? raw.bundlerScore ?? raw.devScore ?? 0;
          return { passed: rug < 0.6, reason: `rugMeta=${rug.toFixed(2)}` };
        } catch {
          return { passed: true, reason: "No data" };
        }
      },
    },
    {
      name: "NoSignal",
      check: () => {
        try {
          const sigs = (agent as any).signals?.get?.("tradable") ?? [];
          return { passed: sigs.length > 0, reason: `${sigs.length} tradable signal(s)` };
        } catch {
          return { passed: true, reason: "No signal check" };
        }
      },
    },
    {
      name: "ManualOverride",
      check: () => {
        return {
          passed: (agent as any).riskCommand?.standDown === undefined,
          reason: (agent as any).riskCommand?.reason ?? "stand-down unavailable",
        };
      },
    },
  ];

  const decisions: { rule: string; passed: boolean; reason: string }[] = [];
  for (const r of rules) {
    const d = r.check();
    decisions.push({ rule: r.name, passed: d.passed, reason: d.reason });
  }

  const failing = decisions.filter((d) => !d.passed);
  const anyFail = failing.length > 0;

  for (const d of decisions) {
    await agent.log(`  ${d.passed ? "✔" : "✖"} ${d.rule}: ${d.reason}`);
  }

  if (anyFail) {
    const reasons = failing.map((f) => `${f.rule}: ${f.reason}`).join("; ");
    await agent.log(`[RISK COMMAND] ⛔ STAND DOWN — ${reasons}`);
    try {
      await (agent as any).notifications?.post?.({
        topic: "desktop:stand_down",
        payload: { reason: "risk_guard", details: reasons },
      });
    } catch (_) {}
  } else {
    await agent.log("[RISK COMMAND] ✓ No stand-down conditions triggered — desk may proceed");
  }
};
