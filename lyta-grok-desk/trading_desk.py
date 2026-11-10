#!/usr/bin/env python3
"""
LYTA GrokTrading Desk — Trading Desk Dashboard
================================================
Shows the overall summary of the trading desk: bot votes, positions,
pnl, alerts, and paper capital state.

Render methods:
  1. Terminal (ASCII table) – run `python3 trading_desk.py` directly.
  2. HTML live dashboard – run `python3 trading_desk.py --html`
     and open the printed file path in a browser (or via Hermes frame).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Bot roster (mirrors the 13 agents in lyta-grok-desk/_paper_agent.ts)
# ---------------------------------------------------------------------------
BOT_ROSTER = [
    "SCOUT", "FILTER", "ANALYST", "FILTER", "CONVICTION",
    "MOMENTUM", "SCALPER", "CONTRARIAN", "TREND",
    "RESEARCHER", "PORTFOLIO", "EXECUTOR", "DEV_WATCH",
]

# ---------------------------------------------------------------------------
# State container
# ---------------------------------------------------------------------------
@dataclass
class Position:
    asset: str
    side: str           # "LONG" | "SHORT" | "PASS"
    entry: float        # entry price / price at open
    exit: Optional[float] = None
    pnl: Optional[float] = None
    bots: int = 0
    entry_time: float = field(default_factory=time.time)
    exit_time: Optional[float] = None

@dataclass
class DeskState:
    config: str = "v3"
    capital: float = 100.0
    asset: str = "GOBLIN"
    positions: list[Position] = field(default_factory=list)
    vote_results: dict = field(default_factory=lambda: {"total": 0, "buy": 0, "sell": 0, "pass": 0})
    completed_positions: int = 0
    sell_legs: int = 0
    realized_pnl: float = 0.0
    pending_alert: Optional[str] = None
    last_updated: float = field(default_factory=time.time)

    # per-agent vote tally for the "12-bot consensus" dashboard row
    agent_votes: dict[str, dict] = field(default_factory=lambda: {
        b: {"buy": 0, "sell": 0, "pass": 0} for b in BOT_ROSTER
    })


# ---------------------------------------------------------------------------
# Trading desk – the "trading desk" we talk about
# ---------------------------------------------------------------------------
class TradingDesk:
    """
    The trading desk is the single source of truth for the running paper
    session.  It aggregates bot votes, positions, pnl and alerts, and can
    render itself to the terminal or to an HTML page (for OpenBot/Telegram
    progress viewing).

    Usage:
        desk = TradingDesk(capital=100.0, asset="GOBLIN")
        desk.add_vote(bot_name, side)
        desk.add_position(asset, side, entry, bots)
        desk.close_position(asset, pnl)
        desk.render()            # terminal table
        desk.to_html()           # HTML string for OpenBot embedding
    """

    def __init__(self, capital: float = 6.0, asset: str = "GOBLIN", config: str = "v3"):
        self.state = DeskState(capital=capital, asset=asset, config=config)

    # -- state updates ------------------------------------------------------
    def add_vote(self, bot: str, side: str) -> None:
        # Normalize vote side
        side_lower = side.lower()
        # Initialize or extend bot's vote dict
        if bot not in self.state.agent_votes:
            self.state.agent_votes[bot] = {"buy": 0, "sell": 0, "pass": 0, "hold": 0, "stand_down": 0}
        elif not all(k in self.state.agent_votes[bot] for k in ("buy", "sell", "pass", "hold", "stand_down")):
            existing = self.state.agent_votes[bot]
            self.state.agent_votes[bot] = {
                "buy": existing.get("buy", 0),
                "sell": existing.get("sell", 0),
                "pass": existing.get("pass", 0),
                "hold": existing.get("hold", 0),
                "stand_down": existing.get("stand_down", 0),
            }
        # Update bot's vote
        if side_lower in ("buy", "sell", "pass", "hold", "stand_down"):
            self.state.agent_votes[bot][side_lower] += 1
        # Update global vote results (only count buy/sell/pass as decisions)
        if side_lower in ("buy", "sell", "pass"):
            self.state.vote_results[side_lower] = (
                self.state.vote_results.get(side_lower, 0) + 1
            )
        # Track total
        self.state.vote_results["total"] = (
            self.state.vote_results.get("buy", 0)
            + self.state.vote_results.get("sell", 0)
            + self.state.vote_results.get("pass", 0)
        )

    def add_position(self, asset: str, side: str, entry: float, bots: int = 12) -> None:
        self.state.positions.append(Position(asset=asset, side=side, entry=entry, bots=bots))

    def close_position(self, asset: str, pnl: float) -> None:
        for i, pos in enumerate(self.state.positions):
            if pos.asset == asset and pos.exit is None:
                pos.exit = time.time()
                pos.pnl = pnl
                pos.exit_time = pos.exit
                self.state.completed_positions += 1
                self.state.sell_legs += 1
                self.state.realized_pnl += pnl
                break

    def update_capital(self, capital: float) -> None:
        self.state.capital = capital

    def set_alert(self, message: str) -> None:
        self.state.pending_alert = message

    # -- rendering ----------------------------------------------------------
    def render(self, show_bot_votes: bool = True) -> str:
        """Terminal-friendly ASCII table of the overall desk summary."""
        s = self.state
        lines = []
        lines.append("=" * 62)
        lines.append("  LYTA GROK TRADING DESK  —  OVERALL SUMMARY")
        lines.append("=" * 62)
        lines.append(f"  Config:      {s.config}")
        lines.append(f"  Asset:       {s.asset}")
        lines.append(f"  Capital:     ${s.capital:.2f}  paper-only")
        lines.append(f"  Open ports:  {len(s.positions)}")
        lines.append(f"  Closed port: {s.completed_positions}")
        lines.append(f"  Sell legs:   {s.sell_legs}")
        lines.append(f"  Realized PnL:{s.realized_pnl:+.4f} SOL")
        lines.append(f"  Last update: {time.strftime('%H:%M:%S')}")
        lines.append("")

        if show_bot_votes and s.vote_results["total"] > 0:
            lines.append("  ─────────────────────────────────────────────")
            lines.append("  BOT VOTES  (12-bot consensus)")
            lines.append("  ─────────────────────────────────────────────")
            for bot in BOT_ROSTER:
                v = s.agent_votes.get(bot, {"buy": 0, "sell": 0, "pass": 0})
                lines.append(
                    f"    {bot:<12}  BUY={v['buy']:<3} SELL={v['sell']:<3} PASS={v['pass']:<3}"
                )
            lines.append(f"    {'TOTAL':<12}  BUY={s.vote_results.get('buy',0):<3} SELL={s.vote_results.get('sell',0):<3} PASS={s.vote_results.get('pass',0)}")
            lines.append("")

        if s.positions:
            lines.append("  ─────────────────────────────────────────────")
            lines.append("  OPEN POSITIONS")
            lines.append("  ─────────────────────────────────────────────")
            for pos in s.positions:
                pnl_str = f" PnL={pos.pnl:+.4f}" if pos.pnl is not None else ""
                lines.append(
                    f"    {pos.asset:<12} {pos.side:<6} entry={pos.entry:.4f} bots={pos.bots}/12{pnl_str}"
                )
            lines.append("")

        if s.realized_pnl != 0.0:
            lines.append(f"  TOTAL REALIZED PnL: {s.realized_pnl:+.4f} SOL")
        lines.append("=" * 62)
        return "\n".join(lines)

    # -- HTML output for OpenBot / Telegram progress view --------------------
    def to_html(self, title: str = "LYTA Trading Desk") -> str:
        """Return an HTML string with the overall desk summary."""
        s = self.state
        now = time.strftime("%H:%M:%S")
        pos_rows = ""
        for pos in s.positions:
            pnl_str = f"{pos.pnl:+.4f}" if pos.pnl is not None else "—"
            pos_rows += f"""
            <tr>
              <td>{pos.asset}</td>
              <td>{pos.side}</td>
              <td>{pos.entry:.4f}</td>
              <td>{pos.bots}/12</td>
              <td>{pnl_str}</td>
            </tr>"""

        agent_rows = ""
        for bot in BOT_ROSTER:
            v = s.agent_votes.get(bot, {"buy": 0, "sell": 0, "pass": 0})
            agent_rows += f"""
            <tr>
              <td>{bot}</td>
              <td>{v['buy']}</td>
              <td>{v['sell']}</td>
              <td>{v['pass']}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #0b0f1a;
    --card: #111827;
    --border: #2a3a5a;
    --accent: #3b82f6;
    --accent-soft: #1e3a8a;
    --text: #e5e7eb;
    --muted: #9ca3af;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:var(--bg);
    color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    padding:16px;
  }}
  .card {{
    background:var(--card);
    border:1px solid var(--border);
    border-radius:10px;
    padding:18px;
    max-width:720px;
    margin:0 auto;
  }}
  h1 {{
    font-size:1.25rem;
    margin-bottom:2px;
    color:{s.asset and '#f59e0b' or 'white'};
  }}
  .sub {{ color:var(--muted); font-size:0.85rem; margin-bottom:14px; }}
  .grid {{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
    gap:10px;
    margin-bottom:14px;
  }}
  .stat {{
    background:#0f172a;
    border:1px solid var(--border);
    border-radius:8px;
    padding:10px;
    text-align:center;
  }}
  .stat .label {{ font-size:0.72rem; color:var(--muted); }}
  .stat .value {{ font-size:1.05rem; font-weight:600; color:white; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.82rem; }}
  th, td {{ text-align:left; padding:7px 8px; border-bottom:1px solid var(--border); }}
  th {{ color:var(--muted); font-weight:500; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.03em; }}
  tr:hover td {{ background:#1e293b; }}
  .alert {{
    background:#1e293b;
    border-left:3px solid #ef4444;
    padding:10px 12px;
    border-radius:4px;
    margin-top:10px;
    font-size:0.85rem;
  }}
  .footer {{ text-align:center; color:var(--muted); font-size:0.72rem; margin-top:14px; }}
</style>
</head>
<body>
  <div class="card">
    <h1>{title}</h1>
    <div class="sub">Updated {now} &middot; paper-only &middot; {s.config}</div>
    <div class="grid">
      <div class="stat"><div class="label">Capital</div><div class="value">${s.capital:.2f}</div></div>
      <div class="stat"><div class="label">Open Ports</div><div class="value">{len(s.positions)}</div></div>
      <div class="stat"><div class="label">Closed Ports</div><div class="value">{s.completed_positions}</div></div>
      <div class="stat"><div class="label">Sell Legs</div><div class="value">{s.sell_legs}</div></div>
      <div class="stat"><div class="label">Realized PnL</div><div class="value">{s.realized_pnl:+.4f} SOL</div></div>
      <div class="stat"><div class="label">Votes Total</div><div class="value">{s.vote_results.get('total',0)}</div></div>
    </div>
    <table>
      <thead>
        <tr><th>Asset</th><th>Side</th><th>Entry</th><th>Bots</th><th>PnL</th></tr>
      </thead>
      <tbody>{pos_rows}</tbody>
    </table>
    <table>
      <thead>
        <tr><th>Bot</th><th>Buy</th><th>Sell</th><th>Pass</th></tr>
      </thead>
      <tbody>{agent_rows}</tbody>
    </table>
    {f'<div class="alert">⚠️ {s.pending_alert}</div>' if s.pending_alert else ''}
    <div class="footer">LYTA GrokBot Multi — Trading Desk v3 (paper-only)</div>
  </div>
</body>
</html>"""
        return html

    # -- JSON for programmatic use -------------------------------------------
    def to_dict(self) -> dict:
        return {
            "config": self.state.config,
            "asset": self.state.asset,
            "capital": self.state.capital,
            "positions": [
                {
                    "asset": p.asset,
                    "side": p.side,
                    "entry": p.entry,
                    "pnl": p.pnl,
                    "bots": p.bots,
                    "entry_time": p.entry_time,
                    "exit_time": p.exit_time,
                }
                for p in self.state.positions
            ],
            "vote_results": self.state.vote_results,
            "agent_votes": self.state.agent_votes,
            "completed_positions": self.state.completed_positions,
            "sell_legs": self.state.sell_legs,
            "realized_pnl": self.state.realized_pnl,
            "last_updated": self.state.last_updated,
        }
