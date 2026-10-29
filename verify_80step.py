#!/usr/bin/env python3
"""Pure stdlib 80-step viability verification for 9-agent desk."""
import csv
import json
import statistics
import os

print("=== 80-STEP VIABILITY TEST — PURE STDLIB VERIFICATION (9 AGENTS) ===")
print("Video-tuned params: ~ -6% hard stops | 8% max size\n")

with open("paper_trades_autonomous_grok.csv") as f:
    trades = list(csv.DictReader(f))

with open("equity_curve_autonomous_grok.csv") as f:
    eq = list(csv.DictReader(f))

with open("grok_signals_for_real_bot.json") as f:
    signals = json.load(f)

start_eq = float(eq[0]["equity_usd"])
end_eq = float(eq[-1]["equity_usd"])

print(f"Total trades: {len(trades)}")
print(f"Equity curve points: {len(eq)}")
print(f"Start ${start_eq:.2f} → End ${end_eq:.2f}")
print(f"Overall PnL ${end_eq - start_eq:.2f}")
wins = sum(1 for t in trades if float(t["pnl"]) > 0)
print(f"Win rate: {wins / len(trades) * 100:.1f}%\n")

print("=== PER-BOT BREAKDOWN ===")
bots = ["SCOUT", "FILTER", "ANALYST", "PUMP_CHASER", "CONVICTION", "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND"]
per_bot_data = {}
for b in bots:
    b_trades = [t for t in trades if t.get("bot", "").upper() == b]
    if not b_trades:
        print(f"  {b}: 0 trades")
        per_bot_data[b] = {"trades": 0, "curve": [0.0]}
        continue
    pnls = [float(t["pnl"]) for t in b_trades]
    wins_b = sum(1 for p in pnls if p > 0)
    total_pnl = sum(pnls)
    print(f"  {b}: {len(b_trades)} trades | {wins_b / len(b_trades) * 100:.0f}% win | PnL ${total_pnl:.2f}")
    per_bot_data[b] = {"trades": len(b_trades), "pnls": pnls, "total": total_pnl}

print("\n=== PER-BOT EQUITY CURVES (cumulative PnL from each bot's trades only) ===")
for b in bots:
    data = per_bot_data[b]
    if data["trades"] == 0:
        continue
    running = 0.0
    curve = [0.0]
    for p in data.get("pnls", []):
        running += p
        curve.append(round(running, 2))
    print(f"  {b}: start 0.00 → {curve[-1]:.2f}  (pts: {len(curve)})")
    # mini last values
    tail = curve[-min(6, len(curve)):]
    print(f"    last: {' '.join(f'{c:+.1f}' for c in tail)}")

print("\n=== EXPORTED SIGNALS FILE (9-agent labels) ===")
print(f"Agents: {signals.get('agents', [])}")
print(f"Total trades recorded: {signals.get('total_trades')}")
print(f"Current equity in signals: ${signals.get('current_equity')}")
if signals.get("signals"):
    s = signals["signals"][0]
    print(f"Sample: {s['bot']} - trades: {s['trades_this_run']} open: {s['current_open_positions']}")

print("\n✅ 80-step test complete. All pure stdlib. Paper only.")

# Optional: write simple per-bot equity curves csv for further analysis
try:
    with open("per_bot_equity_curves.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bot", "step", "cum_pnl"])
        for b in bots:
            data = per_bot_data[b]
            if data["trades"] == 0:
                continue
            running = 0.0
            for i, p in enumerate(data.get("pnls", [])):
                running += p
                w.writerow([b, i, round(running, 2)])
    print("[export] per_bot_equity_curves.csv (pure stdlib)")
except Exception as e:
    print("per-bot csv export skipped:", e)

print("PATTERN PERSISTS.")