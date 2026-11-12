#!/usr/bin/env python3
"""
Reward Tracker — Paper-Based Agent Performance & Pruning System.

Tracks per-agent trading performance, computes daily scores, and decides
whether to prune (delete) underperforming agents.  All operations are
paper-based — no real capital is risked.
"""

import csv
import os
import sys
from datetime import datetime, date
from pathlib import Path

REPO = Path(__file__).resolve().parent
PERF_LOG = REPO / "performance_log.csv"
AGENTS_DB = Path.home() / "Library/Application Support/OpenBot/openbot.db"

# Parameters (from circuit.toml)
LEARNING_RATE = 0.05
PRUNE_WIN_RATE_MIN = 0.35
PRUNE_DRAWDOWN_MAX = 0.50
LOSS_AVERSION = 1.5


def log_performance(agent_id, pnl_pct, win, drawdown_pct, status="alive"):
    """Log a single agent's performance day to the CSV."""
    file_exists = PERF_LOG.exists()
    with open(PERF_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["agent_id", "date", "pnl_pct", "win", "drawdown_pct", "total_score", "status"])
        total_score = compute_score(pnl_pct, win, drawdown_pct)
        writer.writerow([agent_id, date.today().isoformat(), pnl_pct, win, drawdown_pct, total_score, status])


def compute_score(pnl_pct, win, drawdown_pct):
    """Compute the daily score for an agent."""
    daily_score = +100 if win else -100
    profit_score = pnl_pct * 2.0
    volatility_penalty = -drawdown_pct * 0.5
    return daily_score + profit_score + volatility_penalty


def read_performance_log():
    """Read the full performance log into a list of dicts."""
    if not PERF_LOG.exists():
        return []
    rows = []
    with open(PERF_LOG) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["pnl_pct"] = float(row["pnl_pct"])
            row["win"] = row["win"].strip().lower() == "true"
            row["drawdown_pct"] = float(row["drawdown_pct"])
            row["total_score"] = float(row["total_score"])
            rows.append(row)
    return rows


def compute_agent_stats(agent_id):
    """Compute rolling 3-week stats for an agent."""
    rows = read_performance_log()
    # Filter to recent 21 days (3 weeks)
    recent = []
    for r in rows:
        if r["agent_id"] == agent_id:
            try:
                r_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
                if (datetime.now().date() - r_date).days <= 21:
                    recent.append(r)
            except ValueError:
                pass
    if not recent:
        return None

    win_rate = sum(1 for r in recent if r["win"]) / len(recent)
    avg_pnl = sum(r["pnl_pct"] for r in recent) / len(recent)
    recent_drawdowns = [r["drawdown_pct"] for r in recent if r["drawdown_pct"] > 0]
    max_drawdown = max(recent_drawdowns) if recent_drawdowns else 0.0
    cumulative_pnl = sum(r["pnl_pct"] for r in recent)

    return {
        "agent_id": agent_id,
        "days": len(recent),
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "max_drawdown": max_drawdown,
        "cumulative_pnl": cumulative_pnl,
        "last_date": recent[-1]["date"],
    }


def should_prune(agent_id):
    """Check if an agent meets any pruning condition."""
    stats = compute_agent_stats(agent_id)
    if not stats:
        return False, "No data yet"

    conditions = []

    # 5 consecutive losing days
    losing_days = 0
    for r in read_performance_log():
        if r["agent_id"] == agent_id:
            try:
                r_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
                if (datetime.now().date() - r_date).days <= 5 and not r["win"]:
                    losing_days += 1
            except ValueError:
                pass
    if losing_days >= 5:
        conditions.append("5 consecutive losing days")

    # 3 consecutive losing weeks
    losing_weeks = 0
    streak = 0
    for r in reversed(sorted([r for r in read_performance_log() if r["agent_id"] == agent_id], key=lambda x: x["date"])):
        if not r["win"]:
            streak += 1
            if streak >= 21:
                losing_weeks = 3
                break
        else:
            streak = 0
    if losing_weeks >= 3:
        conditions.append("3 consecutive losing weeks")

    # Cumulative drawdown > 50%
    if stats["max_drawdown"] > PRUNE_DRAWDOWN_MAX * 100:
        conditions.append(f"drawdown {stats['max_drawdown']:.1f}% > {PRUNE_DRAWDOWN_MAX*100:.0f}%")

    # 3-week win rate < 35%
    if stats["win_rate"] < PRUNE_WIN_RATE_MIN:
        conditions.append(f"win rate {stats['win_rate']*100:.0f}% < {PRUNE_WIN_RATE_MIN*100:.0f}%")

    # Cumulative PnL < -30% for 5 weeks
    if stats["cumulative_pnl"] < -30 and stats["days"] >= 35:
        conditions.append(f"cumulative PnL {stats['cumulative_pnl']:.1f}% < -30%")

    return (len(conditions) > 0), "; ".join(conditions) if conditions else "None"


def prune_agent(agent_id):
    """Delete an agent from the OpenBot agent store and remove its config."""
    import sqlite3
    conn = sqlite3.connect(AGENTS_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM projection_agents WHERE agent_id = ?", (agent_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        print(f"  ✅ [PRUNE] Deleted {agent_id} (removed {deleted} agents from store)")
    except Exception as e:
        print(f"  ❌ [PRUNE] Error deleting {agent_id}: {e}")
        return False
    finally:
        conn.close()

    # Remove config file
    config_path = Path(REPO) / "lyta-grok-desk" / f"{agent_id}.toml"
    if config_path.exists():
        config_path.unlink()
        print(f"  ✅ [PRUNE] Removed config {config_path.name}")
    return True


def show_leaderboard(n=10):
    """Show the top-n agents by average score."""
    rows = read_performance_log()
    if not rows:
        print("  No performance data yet.")
        return
    # Group by agent
    from collections import defaultdict
    agent_scores = defaultdict(list)
    for r in rows:
        agent_scores[r["agent_id"]].append(r["total_score"])

    leaderboard = []
    for agent_id, scores in agent_scores.items():
        avg = sum(scores) / len(scores)
        wins = sum(1 for r in rows if r["agent_id"] == agent_id and r["win"])
        total = len([r for r in rows if r["agent_id"] == agent_id])
        win_rate = wins / total if total else 0
        leaderboard.append((agent_id, avg, win_rate, len(scores)))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    print(f"\n  {'Rank':<6} {'Agent':<30} {'Avg Score':<12} {'Win Rate':<10} {'Days':<6}")
    print(f"  {'-'*66}")
    for i, (agent_id, avg, win_rate, days) in enumerate(leaderboard[:n], 1):
        print(f"  {i:<6} {agent_id:<30} {avg:>8.1f}{'':<6} {win_rate*100:>5.0f}%{'':<6} {days:<6}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Paper-based reward tracker for LYTA trading desk agents")
    parser.add_argument("--log", nargs=4, metavar=("AGENT_ID", "PNL_PCT", "WIN", "DRAWDOWN_PCT"),
                        help="Log a performance entry: agent_id pnl_pct win drawdown_pct")
    parser.add_argument("--check", nargs="*", metavar="AGENT_ID",
                        help="Check pruning status for given agents (or all if empty)")
    parser.add_argument("--leaderboard", type=int, default=10,
                        help="Show top-N leaderboard")
    parser.add_argument("--prune", nargs="*", metavar="AGENT_ID",
                        help="Actually delete agents that meet pruning conditions")
    args = parser.parse_args()

    if args.log:
        agent_id, pnl_pct, win, drawdown_pct = args.log
        log_performance(agent_id, float(pnl_pct), win.lower() == "true", float(drawdown_pct))
        print(f"  ✅ Logged {agent_id} — score {compute_score(float(pnl_pct), win.lower() == 'true', float(drawdown_pct)):.1f}")

    if args.check or not args.log and not args.leaderboard:
        agents = args.check if args.check else read_performance_log()
        if not agents:
            print("  No agents to check.")
        else:
            for agent_id in agents:
                should, reason = should_prune(agent_id)
                status = "⚠️  PRUNE" if should else "✅ OK"
                print(f"  {status} {agent_id}: {reason}")

    if args.leaderboard:
        show_leaderboard(args.leaderboard)

    if args.prune:
        for agent_id in args.prune:
            should, reason = should_prune(agent_id)
            if should:
                prune_agent(agent_id)
            else:
                print(f"  ⏸️  {agent_id}: {reason} (not pruned)")
