#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 - pump.fun Adapter Extension run (calibrated engine, observation only)
===============================================================================

This run is observation only. No trades executed.

Zero-burn, paper-only runtime. No live trades, no real capital, no live Grok Bot
workshop execution, no live exchange writes. Every candidate is screened through
the verified 8-vote A3b consensus gate, and when qualified, through the verified
adaptive paper simulation loop (micro sizing $0.20-$0.85, 3% risk, 5x cap, exit rules).

Purpose
  Extend the adapter path from the synthetic ADAP1/ADAP2 demo to a
  deterministic, clearly-labelled pump.dev-format pump.fun candidate feed, and
  exercise the full chain once more end-to-end:
    pump.dev /v1/stats candidate -> PumpFunDataAdapter.adapt() -> engine schema
    -> 8-vote A3b gate -> (qualified) paper simulation loop
  This is the "extend adapter path to real pump.dev candidates" freeze-safe lane.

Environment note
  The sandbox cannot reach the live pump.dev /v1/stats JSON endpoint, so this run
  uses a deterministic pump.dev-format candidate pool (representative of what the
  /v1/stats feed returns) routed through PumpFunDataAdapter, plus a read-only
  live DexScreener pump-pair cross-check. Everything is offline/zero-burn.
  No live pump.dev or live-token data is pulled.

Outputs
  * <run>_p2adapter_ext_<YYYYMMDD_HHMMSS>.log  - header, per-candidate traces,
                                                   adapter verdicts, paper results
  * exit code 0 on success
"""
from __future__ import annotations

import sys
from datetime import datetime

REPO_ROOT = "/Users/test/projects/lyta-grokbot-multi"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# --------------------------------------------------------------------------
# Verified Phase 2 / Route C engine pieces
# --------------------------------------------------------------------------
from consensus_aggregator import (
    ConsensusAggregator,
    HolderConcentrationBot,
    LiquidityHealthBot,
    SocialHypeBot,
    VolumeMomentumBot,
    VolatilityDiscordBot,
    CONSENSUS_MIN,
    SIGNAL_GATE,
)
from pumpfun_adapter import PumpFunDataAdapter
from real_trade_feed import RealTradeFeed
from pumpfun_phase3_calibrated_run import (
    FLOW_LOG,
    MICRO_MAX,
    MICRO_MIN,
    RISK_PCT,
    MAX_POSITION_MULT,
    MAX_TICKS,
    STALL_SECONDS,
    STALL_TICKS,
    STOP_LOSS,
    EXIT_TARGET_GAIN,
    TRAILING_LOSS,
    CAPITAL,
    run_pair,
)

# --------------------------------------------------------------------------
# Phase 2 paper configuration (zero-burn)
# --------------------------------------------------------------------------
PAPER_CAPITAL = 6.00
PAPER_MICRO_MIN = 0.20
PAPER_MICRO_MAX = 0.85
PAPER_RISK_PCT = 0.03

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_NAME = f"p2adapter_ext_{RUN_ID}.log"

# verbose trace log for this run (console + log file)
traces: list[str] = []


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def flow_log(msg: str) -> None:
    """Verbose one-line logger used by every vote / gate / exit reason."""
    print(msg)
    traces.append(msg)


def build_voters() -> list:
    """Verified 8-vote A3b roster: 5 heuristic bots + 3 volume clones."""
    base = [
        VolumeMomentumBot("VolumeMomentumBot"),
        LiquidityHealthBot("LiquidityHealthBot"),
        HolderConcentrationBot("HolderConcentrationBot"),
        VolatilityDiscordBot("VolatilityDiscordBot"),
        SocialHypeBot("SocialHypeBot"),
    ]
    return (base
            + [VolumeMomentumBot("VolumeMomentumBot"),
               VolumeMomentumBot("VolumeMomentumBot"),
               VolumeMomentumBot("VolumeMomentumBot")])


def to_engine_pair(p: dict, src: str = "pumpfun_adapter") -> dict:
    """Normalize a pump.dev-format pump.fun candidate into the engine schema.

    p is the raw candidate as returned by pump.dev /v1/stats. PumpFunDataAdapter
    adapts it into the desk schema; we then overlay the fields the A3b gate and
    paper loop read (base/quote/price/liquidity/vol24/fee/age/rug/narrative).
    """
    md = PumpFunDataAdapter.adapt(p)
    narrative = str(md.get("narrative", p.get("narrative", "")))
    if "green" in narrative.lower():
        narrative = "green"
    elif "red" in narrative.lower():
        narrative = "red"
    elif "thin" in narrative.lower():
        narrative = "thin"
    return {
        "chain": p.get("chain", "solana"),
        "dex": p.get("dex", "pump"),
        "base": md.get("asset") or p.get("name") or "UNKNOWN",
        "quote": p.get("quote", "SOL"),
        "price": md.get("price", p.get("price", 0.0)),
        "liquidity_usd": md.get("liquidity_usd") or p.get("liquidity_usd", 0),
        "vol24_usd": p.get("vol_24h", p.get("vol24_usd", 0)) or 0,
        "fee": p.get("fee", 0.003),
        "age_minutes": p.get("age_minutes", p.get("age_seconds", 0) / 60.0 or 0),
        "rug_risk": md.get("rug_risk", 0.5),
        "narrative": narrative,
        "src": src,
        "raw": {"adapted": md, "pumpdev_raw": p},
    }


def stand_down_reasons(r: dict, pair: dict) -> list:
    """Verbose reason codes from the A3b gate verdict (verbatim engine fields)."""
    reasons = []
    if not r.get("qualified"):
        if r.get("consent", 0) < CONSENSUS_MIN:
            reasons.append("consensus_min")
        if abs(r.get("combined_score", 0.0)) < SIGNAL_GATE:
            reasons.append("signal_gate")
        if r.get("tag") in ("hidden_liquidity", "rug",
                            "low_signal", "thin_book", "closed_loop"):
            reasons.append("tag")
    return reasons


# --------------------------------------------------------------------------
# Deterministic pump.dev-format pump.fun candidate feed
#    (representative of a /v1/stats page; clearly labelled offline)
# --------------------------------------------------------------------------
# green  : healthy launch (high analyst score, low rug, healthy liquidity)
# red    : curated rug pattern (high rug risk, strong sell pressure)
# thin   : thin-liquidity tape
# low_liq: sub-desk-floor liquidity
# mixed  : mix for narrative diversity
DESC = {
    "green_ape": ("ApeCoin", "green", "ApeCoin memecoin riding green tape"),
    "green_aur": ("Aurora", "green", "Aurora pump.fun green launch"),
    "red_rug": ("RugPull", "red", "curated rug candidate: high rug risk, red)."),
    "red_rep": ("Reposter", "red", "reposter candidate: down in the past hour"),
    "thin_dry": ("DryPowder", "thin", "thin-liquidity candidate"),
    "low_liq_dust": ("DustCoin", "low_liq", "liquidity below desk floor"),
}


def pumpfun_candidate_pool() -> list[dict]:
    """Deterministic pump.dev /v1/stats-format candidate pool (offline).

    Extended from the original 6 to 24 candidates for a >=20-position
    observation-only paper round (freeze-safe lane 2). Mix: green (healthy
    launches), red (curated rug/reposter), thin (thin-liquidity tape) and
    low_liq (below desk floor). All clearly labelled offline; no live data.
    """
    return [
        # --- green (healthy) ---
        {"name": "ApeCoin", "symbol": "APE", "pair": "0xape1", "price": 0.0012,
         "fee": 0.003, "age_minutes": 35, "age_seconds": 2100,
         "liquidity_usd": 250_000, "vol_24h": 2_400_000, "rug_risk": 0.12,
         "narrative": "green"},
        {"name": "Aurora", "symbol": "AUR", "pair": "0.aur1", "price": 0.00085,
         "fee": 0.0025, "age_minutes": 52, "age_seconds": 3120,
         "liquidity_usd": 180_000, "vol_24h": 1_500_000, "rug_risk": 0.18,
         "narrative": "green"},
        {"name": "Cobalt", "symbol": "COB", "pair": "0xcob1", "price": 0.00025,
         "fee": 0.003, "age_minutes": 41, "age_seconds": 2460,
         "liquidity_usd": 340_000, "vol_24h": 1_200_000, "rug_risk": 0.11,
         "narrative": "green"},
        {"name": "Lumen", "symbol": "LUM", "pair": "0xlum1", "price": 0.00018,
         "fee": 0.0028, "age_minutes": 38, "age_seconds": 2280,
         "liquidity_usd": 260_000, "vol_24h": 980_000, "rug_risk": 0.14,
         "narrative": "green"},
        {"name": "Vex", "symbol": "VEX", "pair": "0xvex1", "price": 0.000062,
         "fee": 0.003, "age_minutes": 29, "age_seconds": 1740,
         "liquidity_usd": 150_000, "vol_24h": 710_000, "rug_risk": 0.19,
         "narrative": "green"},
        {"name": "Etherion", "symbol": "ETH1", "pair": "0xeth1", "price": 0.000009,
         "fee": 0.0035, "age_minutes": 55, "age_seconds": 3300,
         "liquidity_usd": 480_000, "vol_24h": 2_100_000, "rug_risk": 0.08,
         "narrative": "green"},
        {"name": "Zenith", "symbol": "ZEN", "pair": "0xzen1", "price": 0.0032,
         "fee": 0.003, "age_minutes": 68, "age_seconds": 4080,
         "liquidity_usd": 95_000, "vol_24h": 390_000, "rug_risk": 0.22,
         "narrative": "green"},
        {"name": "Ovation", "symbol": "OVA", "pair": "0xova1", "price": 0.00044,
         "fee": 0.0025, "age_minutes": 19, "age_seconds": 1140,
         "liquidity_usd": 610_000, "vol_24h": 2_800_000, "rug_risk": 0.13,
         "narrative": "green"},
        {"name": "Ely", "symbol": "ELY", "pair": "0xely1", "price": 0.000021,
         "fee": 0.003, "age_minutes": 72, "age_seconds": 4320,
         "liquidity_usd": 120_000, "vol_24h": 440_000, "rug_risk": 0.09,
         "narrative": "green"},
        {"name": "FoxCore", "symbol": "FOX", "pair": "0xfox1", "price": 0.0051,
         "fee": 0.003, "age_minutes": 44, "age_seconds": 2640,
         "liquidity_usd": 220_000, "vol_24h": 1_050_000, "rug_risk": 0.16,
         "narrative": "green"},
        {"name": "Nexus", "symbol": "NXS", "pair": "0xnxs1", "price": 0.0000033,
         "fee": 0.0027, "age_minutes": 33, "age_seconds": 1980,
         "liquidity_usd": 88_000, "vol_24h": 260_000, "rug_risk": 0.12,
         "narrative": "green"},
        # --- red (curated rug / reposter) ---
        {"name": "RugPull", "symbol": "RUG", "pair": "0xrug1", "price": 0.0004,
         "fee": 0.004, "age_minutes": 15, "age_seconds": 900,
         "liquidity_usd": 18_000, "vol_24h": 320_000, "rug_risk": 0.88,
         "narrative": "red"},
        {"name": "Reposter", "symbol": "REP", "pair": "0xrep1", "price": 0.00012,
         "fee": 0.003, "age_minutes": 28, "age_seconds": 1680,
         "liquidity_usd": 96_000, "vol_24h": 410_000, "rug_risk": 0.31,
         "narrative": "red"},
        {"name": "Gutter", "symbol": "GUT", "pair": "0xgut1", "price": 0.00029,
         "fee": 0.003, "age_minutes": 21, "age_seconds": 1260,
         "liquidity_usd": 44_000, "vol_24h": 82_000, "rug_risk": 0.74,
         "narrative": "red"},
        {"name": "Paste", "symbol": "PLT", "pair": "0xplt1", "price": 0.000041,
         "fee": 0.0035, "age_minutes": 31, "age_seconds": 1860,
         "liquidity_usd": 18_000, "vol_24h": 33_000, "rug_risk": 0.91,
         "narrative": "red"},
        {"name": "Nightmare", "symbol": "NMR", "pair": "0xnmr1", "price": 0.0011,
         "fee": 0.003, "age_minutes": 52, "age_seconds": 3120,
         "liquidity_usd": 26_000, "vol_24h": 150_000, "rug_risk": 0.83,
         "narrative": "red"},
        {"name": "JetFuel", "symbol": "JET", "pair": "0xjet1", "price": 0.000015,
         "fee": 0.003, "age_minutes": 14, "age_seconds": 840,
         "liquidity_usd": 9_000, "vol_24h": 12_000, "rug_risk": 0.79,
         "narrative": "red"},
        # --- thin (thin-liquidity tape) ---
        {"name": "DryPowder", "symbol": "DRY", "pair": "0xdry1", "price": 0.0009,
         "fee": 0.003, "age_minutes": 8, "age_seconds": 480,
         "liquidity_usd": 42_000, "vol_24h": 62_000, "rug_risk": 0.25,
         "narrative": "thin"},
        {"name": "DustCoin", "symbol": "DUST", "pair": "0xdust1", "price": 0.0003,
         "fee": 0.003, "age_minutes": 6, "age_seconds": 360,
         "liquidity_usd": 32_000, "vol_24h": 15_000, "rug_risk": 0.41,
         "narrative": ""},
        {"name": "Hydroponics", "symbol": "HYD", "pair": "0xhyd1", "price": 0.00037,
         "fee": 0.003, "age_minutes": 12, "age_seconds": 720,
         "liquidity_usd": 31_000, "vol_24h": 44_000, "rug_risk": 0.31,
         "narrative": "thin"},
        {"name": "ChipCoin", "symbol": "CIP", "pair": "0xcip1", "price": 0.000008,
         "fee": 0.003, "age_minutes": 8, "age_seconds": 480,
         "liquidity_usd": 7_000, "vol_24h": 9_000, "rug_risk": 0.29,
         "narrative": "thin"},
        # --- low_liq (below desk floor) ---
        {"name": "DustCoin", "symbol": "DUST", "pair": "0xdust1", "price": 0.0003,
         "fee": 0.003, "age_minutes": 6, "age_seconds": 360,
         "liquidity_usd": 32_000, "vol_24h": 15_000, "rug_risk": 0.41,
         "narrative": ""},
        {"name": "Chemist", "symbol": "CMT", "pair": "0xcmt1", "price": 0.000053,
         "fee": 0.003, "age_minutes": 47, "age_seconds": 2820,
         "liquidity_usd": 28_000, "vol_24h": 61_000, "rug_risk": 0.35,
         "narrative": "low_liq"},
        {"name": "Rusty", "symbol": "RSY", "pair": "0xrsy1", "price": 0.00041,
         "fee": 0.004, "age_minutes": 24, "age_seconds": 1440,
         "liquidity_usd": 22_000, "vol_24h": 38_000, "rug_risk": 0.52,
         "narrative": "low_liq"},
        # ---- round-11 expansion: +24 candidates (offline, labelled) ----
        {"name": "Nova", "symbol": "NVA", "pair": "0xnva1", "price": 0.00012,
         "fee": 0.003, "age_minutes": 38, "age_seconds": 2280,
         "liquidity_usd": 320_000, "vol_24h": 7_200_000, "rug_risk": 0.08,
         "narrative": "green"},
        {"name": "Vega", "symbol": "VGA", "pair": "0xvega1", "price": 0.00007,
         "fee": 0.003, "age_minutes": 21, "age_seconds": 1260,
         "liquidity_usd": 150_000, "vol_24h": 9_600_000, "rug_risk": 0.10,
         "narrative": "green"},
        {"name": "Kinetix", "symbol": "KIX", "pair": "0xkix1", "price": 0.00023,
         "fee": 0.003, "age_minutes": 52, "age_seconds": 3120,
         "liquidity_usd": 540_000, "vol_24h": 4_800_000, "rug_risk": 0.15,
         "narrative": "green"},
        {"name": "Obfus", "symbol": "OBF", "pair": "0xobf1", "price": 0.00002,
         "fee": 0.003, "age_minutes": 14, "age_seconds": 840,
         "liquidity_usd": 41_000, "vol_24h": 2_300_000, "rug_risk": 0.22,
         "narrative": "thin"},
        {"name": "Phobe", "symbol": "PHB", "pair": "0xphb1", "price": 0.00009,
         "fee": 0.003, "age_minutes": 61, "age_seconds": 3660,
         "liquidity_usd": 18_000, "vol_24h": 1_100_000, "rug_risk": 0.44,
         "narrative": "low_liq"},
        {"name": "Qwip", "symbol": "QWP", "pair": "0xqwp1", "price": 0.00031,
         "fee": 0.0025, "age_minutes": 27, "age_seconds": 1620,
         "liquidity_usd": 63_000, "vol_24h": 770_000, "rug_risk": 0.38,
         "narrative": "low_liq"},
        {"name": "Rex", "symbol": "REX", "pair": "0xrex1", "price": 0.00001,
         "fee": 0.004, "age_minutes": 9, "age_seconds": 540,
         "liquidity_usd": 9_000, "vol_24h": 410_000, "rug_risk": 0.61,
         "narrative": "thin"},
        {"name": "Syscoin", "symbol": "SYS", "pair": "0xsys1", "price": 0.00028,
         "fee": 0.003, "age_minutes": 44, "age_seconds": 2640,
         "liquidity_usd": 265_000, "vol_24h": 6_500_000, "rug_risk": 0.09,
         "narrative": "green"},
        {"name": "Yorda", "symbol": "YRD", "pair": "0xyrd1", "price": 0.00017,
         "fee": 0.003, "age_minutes": 33, "age_seconds": 1980,
         "liquidity_usd": 220_000, "vol_24h": 2_000_000, "rug_risk": 0.12,
         "narrative": "green"},
        {"name": "Zep", "symbol": "ZEP", "pair": "0xzep1", "price": 0.00055,
         "fee": 0.003, "age_minutes": 78, "age_seconds": 4680,
         "liquidity_usd": 390_000, "vol_24h": 1_600_000, "rug_risk": 0.18,
         "narrative": "green"},
        {"name": "Storm", "symbol": "STM", "pair": "0xstm1", "price": 0.00004,
         "fee": 0.0025, "age_minutes": 17, "age_seconds": 1020,
         "liquidity_usd": 34_000, "vol_24h": 920_000, "rug_risk": 0.41,
         "narrative": "thin"},
        {"name": "Alchem", "symbol": "ALM", "pair": "0xalm1", "price": 0.00019,
         "fee": 0.003, "age_minutes": 41, "age_seconds": 2460,
         "liquidity_usd": 27_000, "vol_24h": 3_400_000, "rug_risk": 0.33,
         "narrative": "low_liq"},
        {"name": "Birch", "symbol": "BRC", "pair": "0xbrc1", "price": 0.00011,
         "fee": 0.003, "age_minutes": 26, "age_seconds": 1560,
         "liquidity_usd": 200_000, "vol_24h": 1_300_000, "rug_risk": 0.14,
         "narrative": "green"},
        {"name": "Nimbus", "symbol": "NMB", "pair": "0xnmb1", "price": 0.00006,
         "fee": 0.0025, "age_minutes": 12, "age_seconds": 720,
         "liquidity_usd": 15_000, "vol_24h": 600_000, "rug_risk": 0.50,
         "narrative": "thin"},
        {"name": "Elara", "symbol": "ELR", "pair": "0xelr1", "price": 0.00024,
         "fee": 0.003, "age_minutes": 36, "age_seconds": 2160,
         "liquidity_usd": 175_000, "vol_24h": 4_200_000, "rug_risk": 0.11,
         "narrative": "green"},
        {"name": "Fathom", "symbol": "FHM", "pair": "0xfhm1", "price": 0.00003,
         "fee": 0.004, "age_minutes": 8, "age_seconds": 480,
         "liquidity_usd": 7_000, "vol_24h": 290_000, "rug_risk": 0.66,
         "narrative": "thin"},
        {"name": "Cascade", "symbol": "CSD", "pair": "0xcsd1", "price": 0.00015,
         "fee": 0.003, "age_minutes": 31, "age_seconds": 1860,
         "liquidity_usd": 240_000, "vol_24h": 2_900_000, "rug_risk": 0.13,
         "narrative": "green"},
        {"name": "Dune", "symbol": "DNE", "pair": "0xdne1", "price": 0.00044,
         "fee": 0.0025, "age_minutes": 49, "age_seconds": 2940,
         "liquidity_usd": 350_000, "vol_24h": 2_700_000, "rug_risk": 0.16,
         "narrative": "green"},
        {"name": "Flux", "symbol": "FXS", "pair": "0xfxs1", "price": 0.00008,
         "fee": 0.003, "age_minutes": 22, "age_seconds": 1320,
         "liquidity_usd": 48_000, "vol_24h": 880_000, "rug_risk": 0.36,
         "narrative": "low_liq"},
        {"name": "Helios", "symbol": "HLS", "pair": "0xhl1", "price": 0.00027,
         "fee": 0.003, "age_minutes": 55, "age_seconds": 3300,
         "liquidity_usd": 410_000, "vol_24h": 3_100_000, "rug_risk": 0.19,
         "narrative": "green"},
        {"name": "Iridium", "symbol": "IRD", "pair": "0xir1", "price": 0.00001,
         "fee": 0.004, "age_minutes": 6, "age_seconds": 360,
         "liquidity_usd": 6_000, "vol_24h": 180_000, "rug_risk": 0.72,
         "narrative": "thin"},
        # ---- round-12 expansion: +15 more candidates (offline, labelled) ----
        {"name": "Argent", "symbol": "ARG", "pair": "0xarg1", "price": 0.00013,
         "fee": 0.003, "age_minutes": 29, "age_seconds": 1740,
         "liquidity_usd": 210_000, "vol_24h": 3_100_000, "rug_risk": 0.12,
         "narrative": "green"},
        {"name": "Borax", "symbol": "BRX", "pair": "0xbrx1", "price": 0.00005,
         "fee": 0.0025, "age_minutes": 16, "age_seconds": 960,
         "liquidity_usd": 31_000, "vol_24h": 520_000, "rug_risk": 0.42,
         "narrative": "low_liq"},
        {"name": "Cols", "symbol": "CLS", "pair": "0xcls1", "price": 0.00029,
         "fee": 0.003, "age_minutes": 50, "age_seconds": 3000,
         "liquidity_usd": 285_000, "vol_24h": 1_900_000, "rug_risk": 0.17,
         "narrative": "green"},
        {"name": "Dray", "symbol": "DRY", "pair": "0xdry1", "price": 0.00003,
         "fee": 0.004, "age_minutes": 11, "age_seconds": 660,
         "liquidity_usd": 14_000, "vol_24h": 430_000, "rug_risk": 0.55,
         "narrative": "thin"},
        {"name": "Envy", "symbol": "ENV", "pair": "0xenv1", "price": 0.00016,
         "fee": 0.003, "age_minutes": 34, "age_seconds": 2040,
         "liquidity_usd": 235_000, "vol_24h": 2_400_000, "rug_risk": 0.14,
         "narrative": "green"},
        {"name": "Fable", "symbol": "FBL", "pair": "0xfbl1", "price": 0.0001,
         "fee": 0.003, "age_minutes": 25, "age_seconds": 1500,
         "liquidity_usd": 160_000, "vol_24h": 1_000_000, "rug_risk": 0.13,
         "narrative": "green"},
        {"name": "Glint", "symbol": "GLT", "pair": "0xgl1", "price": 0.00034,
         "fee": 0.0025, "age_minutes": 46, "age_seconds": 2760,
         "liquidity_usd": 300_000, "vol_24h": 3_500_000, "rug_risk": 0.10,
         "narrative": "green"},
        {"name": "Halcyon", "symbol": "HLC", "pair": "0xhlc1", "price": 0.00007,
         "fee": 0.003, "age_minutes": 19, "age_seconds": 1140,
         "liquidity_usd": 52_000, "vol_24h": 700_000, "rug_risk": 0.35,
         "narrative": "thin"},
        {"name": "Ink", "symbol": "INK", "pair": "0xink1", "price": 0.00022,
         "fee": 0.003, "age_minutes": 42, "age_seconds": 2520,
         "liquidity_usd": 245_000, "vol_24h": 1_700_000, "rug_risk": 0.15,
         "narrative": "green"},
        {"name": "Jolt", "symbol": "JLT", "pair": "0xjl1", "price": 0.00004,
         "fee": 0.0025, "age_minutes": 13, "age_seconds": 780,
         "liquidity_usd": 20_000, "vol_24h": 390_000, "rug_risk": 0.48,
         "narrative": "thin"},
        {"name": "Koda", "symbol": "KOD", "pair": "0xkod1", "price": 0.00018,
         "fee": 0.003, "age_minutes": 37, "age_seconds": 2220,
         "liquidity_usd": 260_000, "vol_24h": 2_100_000, "rug_risk": 0.11,
         "narrative": "green"},
        {"name": "Lenz", "symbol": "LNZ", "pair": "0xlnz1", "price": 0.00009,
         "fee": 0.003, "age_minutes": 23, "age_seconds": 1380,
         "liquidity_usd": 190_000, "vol_24h": 1_200_000, "rug_risk": 0.16,
         "narrative": "green"},
        {"name": "Mire", "symbol": "MIR", "pair": "0xmir1", "price": 0.00011,
         "fee": 0.003, "age_minutes": 28, "age_seconds": 1680,
         "liquidity_usd": 44_000, "vol_24h": 960_000, "rug_risk": 0.37,
         "narrative": "low_liq"},
        {"name": "Nyle", "symbol": "NYL", "pair": "0xny1", "price": 0.00025,
         "fee": 0.003, "age_minutes": 48, "age_seconds": 2880,
         "liquidity_usd": 330_000, "vol_24h": 2_600_000, "rug_risk": 0.14,
         "narrative": "green"},
        {"name": "Obsidian", "symbol": "OBS", "pair": "0xob1", "price": 0.00002,
         "fee": 0.004, "age_minutes": 7, "age_seconds": 420,
         "liquidity_usd": 8_000, "vol_24h": 250_000, "rug_risk": 0.64,
         "narrative": "thin"},
    ]


# --------------------------------------------------------------------------
# Demo + run
# --------------------------------------------------------------------------
def demo_adapter_bridge(agg: ConsensusAggregator) -> None:
    """Wiring demo: one representative pump.dev /v1/stats payload through
    PumpFunDataAdapter -> engine schema -> A3b verdict. Synthetic but the exact
    live-chain the Phase 2 loop uses (offline, zero-burn)."""
    print("\n[ADAPTER] wiring demo (single representative pump.dev /v1/stats payload):")
    p = {
        "name": "DemoPump", "symbol": "DEM", "pair": "0xdem1", "price": 0.001,
        "fee": 0.003, "age_minutes": 22, "liquidity_usd": 400_000,
        "vol_24h": 3_100_000, "rug_risk": 0.15, "narrative": "green",
        "chain": "solana", "dex": "pump", "quote": "SOL",
    }
    md = PumpFunDataAdapter.adapt(p)
    pair_demo = to_engine_pair({"price": md["price"], "liquidity_usd": md["liquidity_usd"],
                                "rug_risk": md["rug_risk"], "narrative": md.get("narrative",""),
                                "age_minutes": p["age_minutes"], "vol_24h": p["vol_24h"],
                                "fee": p["fee"], "quote": p["quote"], "chain": p["chain"],
                                "dex": p["dex"], "name": md["asset"], "pair": md["pair"]},
                               src="pumpfun_adapter")
    r = agg.consensus(pair_demo, narrative="")
    print(f"  pump.dev payload: asset={md['asset']} price=${md['price']} "
          f"liquidity_usd=${md['liquidity_usd']:,} rug_risk={md['rug_risk']}")
    print(f"  adapter -> base={pair_demo['base']} price=${pair_demo['price']:.4f} "
          f"liquidity_usd=${pair_demo['liquidity_usd']:,}")
    print(f"  GATE    -> qualified={r.get('qualified')} consent={r.get('consent', 0)}/{CONSENSUS_MIN} "
          f"score={r.get('combined_score', 0):+.2f} tag={r.get('tag')} decision={r.get('decision')}")


def run_candidates(candidates: list[dict]) -> dict:
    voters = build_voters()
    agg = ConsensusAggregator(voters)

    results = {"candidates": 0, "gate_qualified": 0, "paper_executed": 0,
               "stand_down": 0, "paper_pnl": 0.0, "paper_trades": 0,
               "exit_reasons": {}, "stand_down_reasons": {}}

    for i, p in enumerate(candidates, start=1):
        # pool entries always carry name; live DexScreener entries are name-safe
        # thanks to the guard in main(), but keep the fallback here too.
        name = f"{p.get('name', 'UNKNOWN')}/{p.get('symbol', p.get('name', 'UNKNOWN'))}"
        pair = to_engine_pair(p)
        results["candidates"] += 1

        # per-bot votes
        vote_map = {}
        for b in voters:
            s = b.decide(pair)
            v = float(s.score)
            kind = getattr(s, "kind", "?")
            vote_map[b.name] = round(v, 3)
            flow_log(f"VOTE {b.name} {kind} {v:+.2f} pair={name} "
                     f"src={pair.get('src', 'pump')}")

        r = agg.consensus(pair, narrative="")

        q = bool(r.get("qualified"))
        console_q = "QUALIFIED" if q else "stand-down"
        flow_log(f"[{i:02d}/{len(candidates)}] GATE {console_q} {name} "
                 f"consent={r.get('consent', 0)}/{CONSENSUS_MIN} "
                 f"score={r.get('combined_score', 0):+.2f} "
                 f"base={r.get('base_change', 0.0):+.1%} "
                 f"tag={r.get('tag')} decision={r.get('decision')}")

        if not q:
            reasons = stand_down_reasons(r, pair)
            if reasons:
                key = "; ".join(reasons)
                results["stand_down_reasons"][key] = results["stand_down_reasons"].get(key, 0) + 1
            results["stand_down"] += 1
            FLOW_LOG.append({"t": "STAND_DOWN", "msg": f"STAND-DOWN {name} -> "
                                        f"{'; '.join(reasons) if reasons else 'no signal'}"})
            continue

        results["gate_qualified"] += 1
        res = run_pair(pair, voters, sim_seed=(i * 101 + i))
        results["paper_executed"] += 1
        results["paper_pnl"] += res.get("pnl", 0.0)
        results["paper_trades"] += res.get("trades", 0)
        er = res.get("exit_reason", "NO_EXIT")
        results["exit_reasons"][er] = results["exit_reasons"].get(er, 0) + 1

        flow_log(f"CLOSE {pair['base']}/{pair['quote']} exit={er} pnl=${res.get('pnl', 0.0):+.4f}")

    return results


def main() -> int:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = [
        f"P2 ADAPTER EXTENSION  pump.dev-format pump.fun candidates  ({ts})",
        "This run is observation only. No trades executed.",
        "paper-only: no live trades, no real capital, no live Grok Bot, "
        "no live exchange writes",
        f"capital=${PAPER_CAPITAL:.2f}  micro=${PAPER_MICRO_MIN}-{PAPER_MICRO_MAX}  "
        f"risk={PAPER_RISK_PCT:.0%}  5x cap  "
        f"exit: +{EXIT_TARGET_GAIN:.0%}/-{STOP_LOSS:.0%}/trail-{TRAILING_LOSS:.0%}",
        f"consensus: {len(build_voters())} votes (A3b, 5 heuristic + 3 volume)",
        f"consensus min: {CONSENSUS_MIN} votes  signal gate: |score|>={SIGNAL_GATE}",
        "sources: deterministic pump.dev-format pump.fun candidate pool (offline) + "
        "read-only DexScreener cross-check",
        "verifying: adapter path (PumpFunDataAdapter -> engine schema) + A3b gate",
    ]
    for line in header:
        print(line)

    log_path = f"/Users/test/projects/lyta-grokbot-multi/{LOG_NAME}"
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header) + "\n\n")

    # ---- demo ----
    demo_adapter_bridge(ConsensusAggregator(build_voters()))

    # ---- candidates ----
    candidates = pumpfun_candidate_pool()
    # read-only live cross-check (offline: shows what live DexScreener would return)
    feed = RealTradeFeed()
    try:
        live = feed.fetch(query="pump", limit=1)
        if live:
            live_pair = to_engine_pair(live[0], src="dex")
            # live pump pairs carry base/quote, not a pump.fun "name":
            # only run the pool plus a nameable live candidate, never a bare
            # raw feed dict, so the gate loop can never KeyError on p['name'].
            if isinstance(live_pair, dict) and live_pair.get("name"):
                candidates = candidates + [live_pair]
            else:
                flow_log(f"WARN live DexScreener cross-check returned an unnamed "
                         f"candidate; pool only (offline, zero-burn).")
    except Exception as exc:
        flow_log(f"WARN live DexScreener cross-check failed ({exc}); using "
                 f"deterministic pump.dev-format pool only (offline, zero-burn).")

    results = run_candidates(candidates)

    # ---- observation banners ----
    print("\n--- ADAPTER EXTENSION OBSERVATION (per-position CLOSE log) ---")
    closes = [m for m in FLOW_LOG if isinstance(m, dict) and m.get("t") == "CLOSE"]
    for c in closes:
        print(c["msg"])
    if not closes:
        print("(none — zero paper fills; all candidates stood down)")

    print("\n--- ADAPTER EXTENSION SUMMARY ---")
    print(f"candidates screened       : {results['candidates']}")
    print(f"gate qualified            : {results['gate_qualified']}")
    print(f"paper executed            : {results['paper_executed']}")
    print(f"paper pnl / trades        : ${results['paper_pnl']:+.4f} / {results['paper_trades']}")
    print(f"stand-down reasons        : {results['stand_down_reasons']}")
    print(f"exit reasons              : {results['exit_reasons']}")
    print("This run is observation only. No trades executed.")
    print("zero-burn: no live trades, no real capital, no live Grok Bot, no live "
          "exchange writes - observation only")

    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header) + "\n\n")
        fh.write("TRACE LOG\n")
        for line in traces:
            fh.write(line + "\n")
        fh.write("\nSUMMARY\n")
        fh.write(f"candidates={results['candidates']} gate_qualified="
                 f"{results['gate_qualified']} paper_executed="
                 f"{results['paper_executed']} paper_pnl={results['paper_pnl']:+.4f} "
                 f"paper_trades={results['paper_trades']}\n")
        fh.write("exit_reasons=" + ", ".join(f"{k}:{v}" for k, v in
                                           sorted(results["exit_reasons"].items())) + "\n")
        fh.write("stand_down_reasons=" + ", ".join(f"{k}:{v}" for k, v in
                                                  sorted(results["stand_down_reasons"].items())) + "\n")
        fh.write("This run is observation only. No trades executed.\n")

    ok = results["candidates"] > 0
    print(f"LOG_FILE: {log_path}")
    print(f"zero-burn adapter extension run completed: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
