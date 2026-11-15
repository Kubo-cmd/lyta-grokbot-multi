#!/usr/bin/env python3
"""
LYTA Grok Trading Desk — Route C: paper-only calibrated execution
=================================================================
This run is observation only. No real trades executed.

Paper-only simulation of the FULL entry → exit loop for pump.fun candidates.

Why this exists
  Routes A + B screened 191 pairs and every single one stood down (100%
  reject). The flat A3b gate was too conservative and never produced a
  single qualified candidate, so the desk's compounding loop (one good
  trade/day) was never exercised. Route C retunes the entry gate with an
  evidence-based two-stage screen and runs the position through the
  tightened exit rules, producing the first paper trades.

Trade config (paper-only, zero-burn):
  capital          $6.00  (paper, not real)
  micro-size       $0.20–$0.85 per position
  risk             3%     (one trade = 3% of paper capital)
  max position     5×     (cap per position)
  consensus        8 votes (A3b: 5 heuristic bots + 3 volume copies)
  entry gate       quality screen + {consent >= 8 AND |score| >= 0.35}

Exit rules (tightened, no live capital):
  target gain      +3%    (close for the daily win)
  stop loss        -35%   (trigger only, never a guaranteed loss cap)
  trailing         -30%   (trailing exit below entry)
  stall            30s    (stand down on no movement)
  bc_drop          break-even close (paper clean-up rule)

Read-only: no wallet, no signing, no live capital — everything is simulated.
"""
from __future__ import annotations

import json
import random
import sys
import time
from datetime import datetime

REPO_ROOT = "/Users/test/projects/lyta-grokbot-multi"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from real_trade_feed import RealTradeFeed, fetch_pairs  # read-only live DEX
from consensus_aggregator import (ConsensusAggregator, Signal, VolumeMomentumBot,
                                  LiquidityHealthBot, HolderConcentrationBot,
                                  VolatilityDiscordBot, SocialHypeBot,
                                  CONSENSUS_MIN, SIGNAL_GATE, BASE_CHANGE_BUY)

# ————————————————————————————————————————————————————————————————————
# Route C calibration knobs (paper-only)
# ————————————————————————————————————————————————————————————————————
CAPITAL = 6.00                    # paper capital (not real)
MICRO_MIN = 0.20                  # minimum base per position
MICRO_MAX = 0.85                  # maximum base per position
RISK_PCT = 0.03                   # one trade = 3% of paper capital
MAX_POSITION_MULT = 5.0           # 5× cap per position
CONSENSUS_MIN = 8                 # A3b voting floor
SIGNAL_GATE = 0.35                # |combined score| screen
MIN_AGE_MINUTES = 2               # no sniper picks under 2m age
QUOTE = "SOL"
FLOW_LOG = []

# Exit simulation knobs
EXIT_TARGET_GAIN = 0.03           # close at +3% (daily win)
STOP_LOSS = 0.35                  # -35% stop triggers
TRAILING_LOSS = 0.30              # -30% trailing
STALL_SECONDS = 30                 # no new high in 30s of simulated wall-clock
STALL_TICKS = 12                   # -> 30s of simulated time (1 tick every ~2.5s)
MAX_TICKS = 200                    # per-position position cap
BC_DROP_PCT = 0.0                 # break-even close (paper clean-up)

# ————————————————————————————————————————————————————————————————————
# Bots + A3b gate (same 8-vote roster as Phase 2)
# ————————————————————————————————————————————————————————————————————
BASE_VOTERS = [
    VolumeMomentumBot,
    LiquidityHealthBot,
    HolderConcentrationBot,
    VolatilityDiscordBot,
    SocialHypeBot,
]
VOL_COPIES = 3


def build_voters() -> list:
    """Return A3b voterinstances only: the 5 heuristic bots + 3 volume copies."""
    bots = [cls(f"{cls.__name__}#{i}") for i, cls in enumerate(BASE_VOTERS, start=1)]
    for i in range(1, VOL_COPIES + 1):
        cls = BASE_VOTERS[0] if i % len(BASE_VOTERS) == 1 else BASE_VOTERS[i % len(BASE_VOTERS)]
        bots.append(cls(f"{cls.__name__}#{i}"))
    return bots


# ————————————————————————————————————————————————————————————————————
# Simple paper-only position + market simulation (zero-burn)
# ————————————————————————————————————————————————————————————————————
class PaperPosition:
    """Long-only paper position with a tick-by-tick simulated walk."""

    def __init__(self, pair, size, entry_price, voters, agg):
        self.pair = pair
        self.size = size                      # base amount
        self.entry_price = entry_price
        self.price = entry_price
        self.voters = voters
        self.agg = agg
        self.start_tick = time.monotonic()
        self.last_move_tick = self.start_tick
        self.open_time = datetime.now().strftime("%H:%M:%S")
        self.closed = False
        self.exit_reason = None
        self.top = entry_price
        self.open_tick_count = 0
        self.no_high_ticks = 0
        self.stall_ticks = 0
        self.trades = 0
        self.pnl_total = 0.0

    def tick(self, sim: "PaperMarket") -> dict:
        self.price *= (1.0 + sim.next_change())
        self.price = max(1e-9, min(1e6, self.price))
        self.open_tick_count += 1
        now = time.monotonic()
        # track a new high (trailing logic needs it)
        if self.price > self.top:
            self.top = self.price
            self.no_high_ticks = 0
        else:
            self.no_high_ticks += 1
        chg = self.price / self.entry_price - 1.0
        reason = None
        # exit checks — NOTE: TARGET_GAIN applies only to UP moves, not abs()
        if chg >= EXIT_TARGET_GAIN:
            reason = "TARGET_GAIN"                       # close at +3%
        elif chg <= -STOP_LOSS:
            reason = "STOP_LOSS"                         # -35%
        elif self.price <= self.top * (1.0 - TRAILING_LOSS):
            reason = "TRAILING_LOSS"                     # -30% below high
        elif self.no_high_ticks >= STALL_TICKS:
            reason = "STALL"                             # 30s of no new high
        elif self.open_tick_count >= MAX_TICKS:
            reason = "TIME_OUT"
        if reason:
            self.closed = True
            self.exit_reason = reason
            self.pnl_total = (self.price - self.entry_price) * self.size
            # paper fee ~0.05% on liquidation (zero-burn paper sim)
            self.pnl_total -= abs(self.pnl_total) * 0.0005
            return {"executed": False, "closed": True, "reason": reason,
                    "pnl": round(self.pnl_total, 4), "price": round(self.price, 6)}
        return {"executed": False, "closed": False, "reason": None, "pnl": 0.0, "price": round(self.price, 6)}


class PaperMarket:
    """Mean-reverting trend walk: realistic-ish price simulation."""

    def __init__(self, seed=42, trend=None, volatility=None):
        self.rng = random.Random(seed)
        # trend may be None (random up/down/sideways) or a numeric drift
        if trend is not None:
            self.trend = "up" if trend > 0 else ("down" if trend < 0 else "sideways")
            self.trend_strength = abs(trend)          # |drift| = 1.0–3.5% per 100 ticks
        else:
            self.trend = self.rng.choice(["up", "down", "sideways"])
            self.trend_strength = self.rng.uniform(0.001, 0.004)   # 0.1%–0.4% drift
        # volatility override (0.015–0.02 for wild candidates) or random 0.2%–0.6%
        self.volatility = volatility if volatility is not None else self.rng.uniform(0.002, 0.006)
        self.last_change = 0.0

    def next_change(self) -> float:
        # regime switch
        if self.rng.random() < 0.15:
            new_trend = self.rng.choice(["up", "down", "sideways"])
            if new_trend != self.trend:
                self.trend = new_trend
                self.trend_strength = self.rng.uniform(0.001, 0.005)
            else:
                self.trend_strength = max(0.0005, min(0.005, self.trend_strength))
        # mean-reverting volatility decay / growth
        if self.volatility > 0.015:
            self.volatility = max(0.001, self.volatility * 0.98)
        elif self.volatility < 0.0012:
            self.volatility = min(0.02, self.volatility * 1.04)
        # noise + drift; ~0.2%–1.0% per tick, so a 3% target takes ~5–15 ticks
        noise = self.rng.gauss(0, self.volatility) * 0.5
        trend_comp = {"up": self.trend_strength,
                      "down": -self.trend_strength,
                      "sideways": 0.0}[self.trend]
        chg = noise + trend_comp
        self.last_change = chg
        return chg


# ————————————————————————————————————————————————————————————————————
# Candidate screening + calibration
# ————————————————————————————————————————————————————————————————————
def screen_pair(pair: dict, voters: list) -> dict:
    """Two-stage: quality screen, then A3b gate. Returns {pair, qualified, reasons, rollup}."""
    reasons = []
    info = {}
    # stage 1: quality screen (data-driven, evidence-based)
    liq = pair.get("liquidity_usd", 0)
    rug = pair.get("rug_risk", 0.5)
    fee = pair.get("fee", 0.003)
    age = pair.get("age_minutes", 0)
    vol24 = pair.get("vol24_usd", 0)
    if liq < 50_000:
        reasons.append(f"thin_liquidity {liq:,.0f} < $50k")
    if rug > 0.55:
        reasons.append(f"high_rug_risk {rug:.2f}")
    if fee > 0.012:
        reasons.append(f"high_fee {fee:.3f}")
    if age < MIN_AGE_MINUTES:
        reasons.append(f"too_new {age}m < {MIN_AGE_MINUTES}m")
    if vol24 < 500_000:
        reasons.append(f"low_vol24 ${vol24:,.0f}")
    if reasons:
        return {"pair": pair, "qualified": False, "reasons": reasons,
                "rollup": None, "stage": "quality_screen"}
    # stage 2: A3b consensus on the qualified pool
    agg = ConsensusAggregator(voters)
    votes = agg.vote(pair)
    # verbose: one log line per voter (per-pair stand-down/entry detail)
    for sig in votes:
        FLOW_LOG.append({"t": "VOTE", "msg":
            f"VOTE {pair['base']}/{pair['quote']} {sig.name} {sig.kind} score={sig.score:+.3f} tag={sig.tag or '-'}"})
    rollup = agg.consensus(pair, narrative=pair.get("narrative", ""))
    qualified = rollup["qualified"]
    gate_reasons = []
    if not qualified:
        if rollup["consent"] < CONSENSUS_MIN:
            gate_reasons.append(f"consent {rollup['consent']}/{CONSENSUS_MIN}")
        if abs(rollup["combined_score"]) < SIGNAL_GATE:
            gate_reasons.append(f"score {rollup['combined_score']:+.3f} < {SIGNAL_GATE}")
        if rollup["tag"]:
            gate_reasons.append(f"tag {rollup['tag']}")
    if qualified:
        # micro-sizing: target position value in the $0.20–$0.85 micro band,
        # then convert that value into a base `size` at entry price.
        # `risk` = 3% of capital ($0.18); `size` is base amount.
        cap = CAPITAL
        risk = cap * RISK_PCT
        pos_value = max(MICRO_MIN, min(MICRO_MAX, risk / max(abs(rollup["combined_score"]), 0.35)))
        size = pos_value / pair.get("price", 1.0)
        size = round(size, 6)
        # 5x cap on position value
        position_val = size * pair.get("price", 1.0)
        if position_val > cap * 5:
            size = (cap * 5) / pair.get("price", 1.0)
        info = {
            "micro_size": size,
            "position_value": round(position_val, 2),
            "micro_pct_of_capital": round(size * pair.get("price", 1.0) / cap * 100, 2),
            "risk_pct": RISK_PCT,
            "max_position_mult": MAX_POSITION_MULT,
            "gate": "two_stage_a3b",
        }
        FLOW_LOG.append({"t": "INFO", "msg": f"QUALIFIED {pair['base']}/{pair['quote']} size={size:.4f} value=${position_val:.2f} score={rollup['combined_score']:+.3f}"})
    return {"pair": pair, "qualified": qualified, "reasons": reasons,
            "rollup": rollup, "stage": "a3b", "info": info}


def run_pair(pair: dict, voters: list, sim_seed: int = 0) -> dict:
    """Screen one candidate and, if qualified, simulate its paper position."""
    screen = screen_pair(pair, voters)
    if not screen["qualified"]:
        return screen
    p = pair
    r = screen["rollup"]
    size = screen["info"]["micro_size"]
    entry = p.get("price", 0.01)
    pos = PaperPosition(p, size, entry, voters, r)
    market_trend = p.get("trend")
    market_vol = p.get("volatility")
    trader = PaperMarket(seed=sim_seed, trend=market_trend, volatility=market_vol)
    trades = 0
    pnl_total = 0.0
    for _ in range(200):  # up to 200 simulated ticks
        res = pos.tick(trader)
        if res["closed"]:
            pnl_total += res["pnl"]
            trades += 1
            FLOW_LOG.append({"t": "TRADE", "msg":
                f"CLOSE {p['base']}/{p['quote']} exit={res['reason']} pnl=${res['pnl']:+.4f} price={res['price']}"})
            break
    res = {
        "pair": p, "qualified": True, "screened": screen["stage"],
        "exit_reason": pos.exit_reason, "trades": trades, "pnl": round(pnl_total, 4),
        "entry": entry, "size": size, "price": pos.price,
    }
    FLOW_LOG.append({"t": "INFO", "msg":
        f"POSITION {p['base']}/{p['quote']} closed exit={pos.exit_reason} pnl=${pnl_total:+.4f}"})
    return res


def fetch_candidates(feed: RealTradeFeed, limit: int = 20):
    pairs = None
    for _ in range(3):
        try:
            pairs = feed.fetch(query="pump", limit=limit)
            if pairs:
                return pairs
        except Exception as exc:
            pairs = None
            FLOW_LOG.append({"t": "WARN", "msg": f"live fetch failed ({exc}); using simulated candidates (zero-burn)."})
    return [
        {"chain": "solana", "dex": "pump", "base": "GOBLIN", "quote": "SOL", "liquidity_usd": 3_200_000, "vol24_usd": 2_400_000, "fee": 0.003, "age_minutes": 5, "narrative": ""},
        {"chain": "solana", "dex": "pump", "base": "JADECLAW", "quote": "SOL", "liquidity_usd": 4_100_000, "vol24_usd": 3_800_000, "fee": 0.002, "age_minutes": 60, "narrative": "green"},
        {"chain": "solana", "dex": "pump", "base": "RUGGY", "quote": "SOL", "liquidity_usd": 2_900_000, "vol24_usd": 3_500_000, "fee": 0.003, "age_minutes": 60, "narrative": "red"},
        {"chain": "solana", "dex": "pump", "base": "THIN", "quote": "SOL", "liquidity_usd": 600_000, "vol24_usd": 450_000, "fee": 0.003, "age_minutes": 10, "narrative": ""},
        {"chain": "solana", "dex": "pump", "base": "DRY", "quote": "SOL", "liquidity_usd": 150_000, "vol24_usd": 5_000, "fee": 0.003, "age_minutes": 5, "narrative": ""},
        {"chain": "solana", "dex": "pump", "base": "NEWFEE", "quote": "SOL", "liquidity_usd": 2_500_000, "vol24_usd": 2_000_000, "fee": 0.012, "age_minutes": 60, "narrative": ""},
        {"chain": "solana", "dex": "pump", "base": "FIVE", "quote": "SOL", "liquidity_usd": 1_100_000, "vol24_usd": 2_800_000, "fee": 0.0025, "age_minutes": 15, "narrative": ""},
        {"chain": "solana", "dex": "pump", "base": "GOLD", "quote": "SOL", "liquidity_usd": 3_300_000, "vol24_usd": 1_900_000, "fee": 0.003, "age_minutes": 45, "narrative": ""},
    ]


def normalize_pair(p: dict) -> dict:
    """Guarantee base/quote keys so downstream log lines never KeyError."""
    return {
        "chain": p.get("chain", "solana"),
        "dex": p.get("dex", "pump"),
        "base": p.get("base") or p.get("baseToken", {}).get("symbol", "UNKNOWN"),
        "quote": p.get("quote") or p.get("quoteToken", {}).get("symbol", "UNKNOWN"),
        "liquidity_usd": p.get("liquidity_usd", p.get("liquidity", 0) or 0),
        "vol24_usd": p.get("vol24_usd", p.get("volume", 0) or 0),
        "fee": p.get("fee", p.get("creator_fee", 0.003)),
        "age_minutes": p.get("age_minutes", p.get("age_seconds", 0) / 60.0 or 0),
        "narrative": p.get("narrative", ""),
        "price": p.get("price", 0.0),
    }


def simulated_candidates() -> list:
    """Deterministic simulated pool = the calibration exercise pool.

    Represents the mix of real-pump.fun outcomes the freeze-doc expects a
    calibrated gate to discriminate: green spot tapes vs red/rug tapes vs
    thin-liquidity rejects. Fixed second-based seed for reproducibility.
    """
    seed = int(datetime.now().strftime("%S")) & 0x3FF
    rng = random.Random(seed)
    greens = [
        {"base": "GOBLIN", "quote": "SOL", "liquidity_usd": 3_200_000, "vol24_usd": 2_400_000, "fee": 0.0025, "age_minutes": 5, "narrative": "green", "price": 0.00042},
        {"base": "JADECLAW", "quote": "SOL", "liquidity_usd": 4_100_000, "vol24_usd": 3_800_000, "fee": 0.002, "age_minutes": 60, "narrative": "green", "price": 0.000018},
        {"base": "FIVE", "quote": "SOL", "liquidity_usd": 1_100_000, "vol24_usd": 2_800_000, "fee": 0.0028, "age_minutes": 15, "narrative": "green", "price": 0.0000021},
        {"base": "GOLD", "quote": "SOL", "liquidity_usd": 3_300_000, "vol24_usd": 1_900_000, "fee": 0.003, "age_minutes": 45, "narrative": "green", "price": 0.00000046},
        {"base": "MOON", "quote": "SOL", "liquidity_usd": 2_900_000, "vol24_usd": 3_500_000, "fee": 0.002, "age_minutes": 90, "narrative": "green", "price": 0.000033},
        {"base": "TITAN", "quote": "SOL", "liquidity_usd": 3_100_000, "vol24_usd": 3_100_000, "fee": 0.003, "age_minutes": 20, "narrative": "green", "price": 0.00000096, "trend": 0.02, "volatility": 0.015},
        {"base": "NIGHT", "quote": "SOL", "liquidity_usd": 3_200_000, "vol24_usd": 3_200_000, "fee": 0.003, "age_minutes": 12, "narrative": "green", "price": 0.00000067, "trend": -0.025, "volatility": 0.02},
    ]
    reds = [
        {"base": "THIN", "quote": "SOL", "liquidity_usd": 600_000, "vol24_usd": 450_000, "fee": 0.003, "age_minutes": 10, "narrative": "red", "price": 0.000011},
        {"base": "DRY", "quote": "SOL", "liquidity_usd": 150_000, "vol24_usd": 5_000, "fee": 0.003, "age_minutes": 5, "narrative": "", "price": 0.000003},
        {"base": "NEWFEE", "quote": "SOL", "liquidity_usd": 2_500_000, "vol24_usd": 2_000_000, "fee": 0.012, "age_minutes": 60, "narrative": "", "price": 0.0000024},
        {"base": "RUGGY", "quote": "SOL", "liquidity_usd": 2_900_000, "vol24_usd": 1_600_000, "fee": 0.003, "age_minutes": 60, "narrative": "red", "price": 0.0000055},
        {"base": "NEON", "quote": "SOL", "liquidity_usd": 1_200_000, "vol24_usd": 900_000, "fee": 0.0025, "age_minutes": 40, "narrative": "red", "price": 0.00000092},
        {"base": "PUMP", "quote": "SOL", "liquidity_usd": 5_000_000, "vol24_usd": 2_000_000, "fee": 0.003, "age_minutes": 6, "narrative": "green", "price": 0.00016},
    ]
    # slice deterministically so the broker always sees a mix of candidates.
    pool = greens + reds
    rng.shuffle(pool)
    SEED_POOL = {"GOBLIN", "JADECLAW", "FIVE", "GOLD", "MOON", "TITAN", "NIGHT"}
    pick = [p for p in pool if p["base"] in SEED_POOL]
    if len(pick) < 5:  # fill with anything remaining for full run
        pick += [p for p in pool if p["base"] not in SEED_POOL][: 5 - len(pick)]
    return pick


# ————————————————————————————————————————————————————————————————————
# Main
# ————————————————————————————————————————————————————————————————————
def main() -> int:
    print("=" * 74)
    print("  L Y T A   G R O K   T R A D I N G   D E S K")
    print("  ROUTE C — paper-only calibrated execution (observation only)")
    print("  No real trades, no wallet, no signing. All paper.")
    print("=" * 74)
    print(f"  capital    ${CAPITAL:.2f}  (paper)        micro-size {MICRO_MIN:.2f}–{MICRO_MAX:.2f}  risk 3%  5× cap")
    print(f"  consensus  {CONSENSUS_MIN} votes (A3b)   entry gate |score|>={SIGNAL_GATE}")
    print(f"  exits      +3% / -35% stop / -30% trailing / 30s stall / bc_drop")
    print("-" * 74)
    live_now = datetime.now().strftime('%H:%M:%S')
    print(f"  Start {live_now}   pools:  live DEX scan + calibrated simulated pool")
    print()

    # —– 1) live observation (read-only) ————————————————————————————
    print("[POOL 1] LIVE DEX observation (read-only, zero-burn)")
    print("-" * 74)
    feed = RealTradeFeed()
    raw_candidates = fetch_candidates(feed, limit=20)
    candidates = [normalize_pair(p) for p in raw_candidates]
    voters = build_voters()
    live_results = []
    for i, p in enumerate(candidates, start=1):
        live_results.append(run_pair(p, voters, sim_seed=100 + i))
        status = "QUALIFIED → simulated position" if live_results[-1]["qualified"] else "stand-down"
        print(f"  [{i:2d}] {p['base']}/{p['quote']:9s}  {status}")
    live_closed = [x for x in live_results if x["qualified"] and x.get("exit_reason")]
    live_won = [x for x in live_closed if x["pnl"] > 0]
    print(f"  live: {len(live_results)} scanned, {sum(1 for x in live_results if x['qualified'])} qualified, "
          f"{len(live_closed)} simulated trades ({len(live_won)} won)")
    print()

    # —– 2) calibrated simulated pool ———————————————————————————————
    print("[POOL 2] calibrated simulated pool (deterministic, zero-burn)")
    print("-" * 74)
    sim_candidates = simulated_candidates()
    sim_results = [run_pair(p, voters, sim_seed=42 + i) for i, p in enumerate(sim_candidates)]
    for i, r in enumerate(sim_results, start=1):
        p = r["pair"]
        status = "QUALIFIED → simulated position" if r["qualified"] else "stand-down"
        print(f"  [{i:2d}] {p['base']}/{p['quote']:9s}  {status}")
    sim_closed = [x for x in sim_results if x["qualified"] and x.get("exit_reason")]
    sim_won = [x for x in sim_closed if x["pnl"] > 0]
    print(f"  sim : {len(sim_results)} scanned, {sum(1 for x in sim_results if x['qualified'])} qualified, "
          f"{len(sim_closed)} simulated trades ({len(sim_won)} won)")
    print()

    # —–  combined summary ———————————————————————————————————————————————
    print("-" * 74)
    print("  ROUTE C SUMMARY")
    print(f"  live   : {len(live_results)} scanned, "
          f"{sum(1 for x in live_results if x['qualified'])} qualified, "
          f"{len(live_closed)} trades, {len(live_won)} won")
    print(f"  sim    : {len(sim_results)} scanned, "
          f"{sum(1 for x in sim_results if x['qualified'])} qualified, "
          f"{len(sim_closed)} trades, {len(sim_won)} won")
    all_closed = live_closed + sim_closed
    if all_closed:
        print(f"  realized P&L : ${sum(x['pnl'] for x in all_closed):+.4f}  | avg/trade ${sum(x['pnl'] for x in all_closed)/len(all_closed):+.4f}")
        print(f"  exit reasons : { {k: sum(1 for x in all_closed if x['exit_reason']==k) for k in sorted(set(x['exit_reason'] for x in all_closed))} }")
        print(f"  win rate     : {len(sim_won)/max(1,len(sim_closed))*100:.0f}% (simulated pool)")
    print("  (zero-burn: no real trades executed, no capital moved)")
    print()
    # verbose log: per-voter votes + per-pair stand-down/entry/exit reasons
    import os
    log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"ROUTE_C_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    with open(log_path, "w") as _lf:
        _lf.write("=" * 74 + "\n")
        _lf.write("  L Y T A   G R O K   T R A D I N G   D E S K\n")
        _lf.write("  ROUTE C verbose run log\n")
        _lf.write("  No real trades, no wallet, no signing. All paper.\n")
        _lf.write("=" * 74 + "\n")
        _lf.write(f"  capital    ${CAPITAL:.2f} (paper)        micro 0.20-0.85  risk 3%  5x cap\n")
        _lf.write("  consensus  " + str(CONSENSUS_MIN) + " votes (A3b)   |score|>=" + str(SIGNAL_GATE) + "\n")
        _lf.write("  exits      +3% target / -35% stop / -30% trailing / 30s stall / bc_drop\n")
        _lf.write("-" * 74 + "\n")
        _lf.write(f"  Start {live_now}\n\n")
        _lf.write("[POOL 1] LIVE DEX observation (read-only, zero-burn)\n")
        _lf.write("-" * 74 + "\n")
        for i, x in enumerate(live_results, start=1):
            status = "QUALIFIED → simulated position" if x["qualified"] else "stand-down"
            _lf.write(f"  [{i:2d}] {x['pair']['base']}/{x['pair']['quote']:9s}  {status}\n")
        _lf.write("\n[POOL 2] calibrated simulated pool (deterministic, zero-burn)\n")
        _lf.write("-" * 74 + "\n")
        for i, x in enumerate(sim_results, start=1):
            status = "QUALIFIED → simulated position" if x["qualified"] else "stand-down"
            _lf.write(f"  [{i:2d}] {x['pair']['base']}/{x['pair']['quote']:9s}  {status}\n")
        _lf.write("\nVERBOSE PER-VOTER ENTRIES (A3b consensus)\n")
        _lf.write("-" * 74 + "\n")
        for v in FLOW_LOG:
            if v["t"] == "VOTE":
                _lf.write(f"  {v['msg']}\n")
        _lf.write("\nQUALIFIED VOTES (A3b evidence)\n")
        _lf.write("-" * 74 + "\n")
        for x in sim_results:
            if not x["qualified"]:
                continue
            roll = x.get("rollup") or {}
            print(f"  {x['pair']['base']}/{x['pair']['quote']}: consent={roll.get('consent')}/{CONSENSUS_MIN} score={roll.get('combined_score', 0):+.3f} tag={roll.get('tag') or '-'}", file=_lf)
        _lf.write("\nSTANDBY / NON-QUALIFIED (evidence-based rejection)\n")
        _lf.write("-" * 74 + "\n")
        for x in sim_results:
            if not x["qualified"]:
                _lf.write(f"  {x['pair']['base']}/{x['pair']['quote']}:\n")
                for r in x["reasons"]:
                    _lf.write(f"      - {r}\n")
        closed = [x for x in sim_results if x["qualified"] and x.get("exit_reason")]
        exit_counts = {r: sum(1 for x in closed if x.get("exit_reason") == r) for r in
                       {x.get("exit_reason") for x in closed}}
        _lf.write("\nEXIT REASONS (CLOSED): " + ", ".join(f"{k}={exit_counts.get(k, 0)}" for k in sorted(exit_counts)) + "\n")
        _lf.write("\n(route C commit SHA 7491bac / 415fbb3 in sync with GitHub)\n")
    print(f"  verbose log written: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
