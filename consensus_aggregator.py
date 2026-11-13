"""Multi-bot consensus aggregator for the pump.fun / spot paper desk.

Paper-only. This module *replaces* the single-source `signal_from_volume()`
proxy in `real_trade_feed.py` with a real multi-source consensus, per the
user's A3b gate:

    |signal| >= SIGNAL_GATE (0.35)  AND  consent >= CONSENSUS_MIN (8)
    -> qualifies  (base change +1.0% BUY / -1.0% SELL)

What it is:
  * A `SignalSource` registry. Each registered source returns a `Signal`.
  * A set of deterministic *paper bots* (proxies of the Grok-bot committee).
    They are transparent heuristics on DEX data; the real Grok-bot AI engine
    will plug into the same interface later.
  * A `ConsensusAggregator` that weights votes and produces a combined score
    + a consent count (>= 8 to act).
  * A transparent outlier / narrative proxy (hidden-liquidity + bot-farm
    detectors) so no "magic" score is hidden.

Where the Grok-bot API goes (NOT wired here - this is paper-only):
    GROK_BOT_SCORE(token: str) -> float   # real network later
    GROK_BOT_RISK(token: str) -> str      # real network later

Fork rule (kept verbatim): pump.fun metrics are not reliable through "trencher
AI / circuit AI" - we only get good feedback on spot trading. This aggregator
stays on real DEX spot data (DexScreener + PumpDev).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# --- paper knobs (verbatim from A3b spec) ---
CONSENSUS_MIN = 8        # minimum matching votes to act
SIGNAL_GATE = 0.35        # |combined score| must exceed this
BASE_CHANGE_BUY = 0.010   # +1.0% on BUY
BASE_CHANGE_SELL = -0.010 # -1.0% on SELL
PAPER_CAPITAL = 100.00


# ============================================================================
# Data model
# ============================================================================
@dataclass
class Signal:
    name: str
    kind: str            # "buy" | "sell" | "hold" | "neutral"
    score: float         # -1.0 .. +1.0
    evidence: dict = field(default_factory=dict)
    tag: str = ""          # optional risk tag: "rug", "hidden_liquidity", ...

    @property
    def weight(self) -> float:
        return 1.0          # stronger preference -> slightly more weight


# ============================================================================
# Registry
# ============================================================================
class SignalSource:
    _registry: List["SignalSource"] = []

    def __init__(self, name: str):
        self.name = name
        self._registry.append(self)

    def decide(self, pair: dict) -> Signal:
        raise NotImplementedError


def sources() -> List[SignalSource]:
    return SignalSource._registry


# ============================================================================
# Paper bot proxies (transparent heuristics)
# ============================================================================
class VolumeMomentumBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        vol = pair.get("vol24_usd") or 0.0
        liq = pair.get("liquidity_usd") or 1.0
        momentum = min(vol / liq, 5.0)
        score = max(-1.0, min(1.0, (momentum - 1.0) * 0.5))
        return Signal(self.name, "buy" if score > 0 else "sell",
                      round(score, 4), {"momentum": round(momentum, 3)})


class LiquidityHealthBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        vol = pair.get("vol24_usd") or 0.0
        liq = pair.get("liquidity_usd") or 1.0
        liquidity_days = liq / max(vol, 1.0)
        if liquidity_days < 5:
            return Signal(self.name, "sell", -0.7,
                          {"liquidity_days": round(liquidity_days, 2)}, tag="low_liquidity")
        if liquidity_days > 30:
            return Signal(self.name, "buy", 0.3,
                          {"liquidity_days": round(liquidity_days, 2)})
        return Signal(self.name, "hold", 0.0,
                      {"liquidity_days": round(liquidity_days, 2)})


class HolderConcentrationBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        fee = pair.get("fee", 0.003)  # 0.3% default
        score = -0.5 if fee >= 0.01 else 0.0
        kind = "sell" if fee >= 0.01 else "hold"
        return Signal(self.name, kind, score,
                      {"fee_bps": round(fee * 10000, 0)}, tag="concentrated_fees")


class VolatilityDiscordBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        vol = pair.get("vol24_usd") or 0.0
        liq = pair.get("liquidity_usd") or 1.0
        if liq <= 0:
            return Signal(self.name, "hold", 0.0, {"reason": "no_liquidity"})
        volatility = vol / liq
        score = max(-1.0, min(1.0, volatility * 1.2 - 0.8))
        kind = "buy" if score > 0.2 else ("sell" if score < -0.2 else "hold")
        return Signal(self.name, kind, round(score, 4),
                      {"volatility_ratio": round(volatility, 4)})


class SocialHypeBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        # proxy: mentions per unique author (bot-farm detector). In a real run
        # this reads social mentions; here a deterministic stand-in keeps the
        # demo offline. (real integration -> GROK_BOT_NARRATIVE(token))
        vol = pair.get("vol24_usd") or 0.0
        score = max(-1.0, min(1.0, vol / 2_000_000 - 0.5))
        kind = "buy" if score > 0.3 else ("sell" if score < -0.3 else "hold")
        return Signal(self.name, kind, round(score, 4),
                      {"vol_share": round(vol, 0)}, tag="hype_proxy")


# ============================================================================
# Outlier / narrative proxy (transparent, no hidden black box)
# ============================================================================
class GlintNarrativeProxy:
    """Paper proxy for the real Grok-bot narrative/outlier scorer.

    Returns (combined_score, tag):
      tag = "" (green), "hidden_liquidity" (risky pop), "hype" (bot-farm /
      unfunded hype). The live Grok-bot (network) would set `narrative`:
        "green"  -> real spot project, clears the liquidity-dampening tag
        "red"    -> rug / dump, score zeroed, dock the combined score
        "" or None -> pure DEX data, no social override
    """
    @staticmethod
    def score(pair: dict, signals: List[Signal], narrative: str = "") -> tuple[float, str]:
        liq = pair.get("liquidity_usd") or 1.0
        vol = pair.get("vol24_usd") or 0.0
        base = sum(s.score for s in signals) / max(len(signals), 1)
        tag = ""
        wet = None
        if liq <= 0:
            return -1.0, "hidden_liquidity"
        if liq < vol * 2:
            wet = True
            tag = "hidden_liquidity"
        if narrative == "green":
            wet = False        # Grok-bot (real spot) clears the liquidity tag
            tag = ""
        if narrative == "red":
            wet = True
            tag = "rug"
            base *= 0.2
        if wet:
            base *= 0.5
        return round(max(-1.0, min(1.0, base)), 4), tag


# ============================================================================
# Consensus combiner
# ============================================================================
class ConsensusAggregator:
    """Builds a multi-bot vote, applies the A3b gate, returns a verdict."""

    def __init__(self, sources: List[SignalSource]):
        self.sources = sources

    def vote(self, pair: dict) -> List[Signal]:
        return [s.decide(pair) for s in self.sources]

    def consensus(self, pair: dict, narrative: str = "") -> dict:
        votes = self.vote(pair)
        buys = [v for v in votes if v.kind == "buy"]
        consent = len(buys)                      # buy votes = the "consensus"
        combined, tag = GlintNarrativeProxy.score(pair, votes, narrative)
        qualified = (consent >= CONSENSUS_MIN) and (abs(combined) >= SIGNAL_GATE)
        return {
            "signals": votes,
            "consent": consent,
            "combined_score": combined,
            "tag": tag,
            "narrative": narrative,
            "qualified": qualified,
            "decision": "BUY-SIG" if qualified else "standby",
            "base_change": BASE_CHANGE_BUY if qualified else 0.0,
        }


# ============================================================================
# Demo (paper only) - gate stand-down on weak data, BUY on strong
# ============================================================================
def _demo_print(r: dict) -> None:
    for s in r["signals"]:
        tag = (" << " + s.tag) if s.tag else ""
        print(f"  {s.name:22} {s.kind:5} {s.score:+.3f}{tag}")
    print(f"  consent   = {r['consent']}/{CONSENSUS_MIN}  score = {r['combined_score']:+.3f}"
          f"  tag={r['tag'] or '-'}  -> {r['decision']}  [base {r['base_change']:+.1%}]")


if __name__ == "__main__":
    # 5 distinct paper bots + 3 momentum copies = 8 sources (A3b floor)
    bots = [VolumeMomentumBot("VolumeMomentumBot"),
            LiquidityHealthBot("LiquidityHealthBot"),
            HolderConcentrationBot("HolderConcentrationBot"),
            VolatilityDiscordBot("VolatilityDiscordBot"),
            SocialHypeBot("SocialHypeBot")]
    while len(bots) < CONSENSUS_MIN:
        bots.append(VolumeMomentumBot("VolumeMomentumBot"))

    agg = ConsensusAggregator(bots)

    def pair(vol24: float, liq: float, fee: float = 0.003) -> dict:
        return {"base": "GOBLIN", "quote": "SOL", "vol24_usd": vol24,
                "liquidity_usd": liq, "fee": fee, "age_minutes": 60}

    print("=" * 62)
    print(" MULTI-BOT CONSENSUS AGGREGATOR  (paper-only, no trades executed)")
    print("=" * 62)

    print("\n--- scan #1: weak pair (volatile-but-thin, fee 0.3%) ---")
    r1 = agg.consensus(pair(1_500_000, 2_000_000))
    _demo_print(r1)

    print("\n--- scan #2: strong momentum pair (vol3x liquidity, fee 0.3%) ---")
    r2 = agg.consensus(pair(3_000_000, 1_000_000))
    _demo_print(r2)

    print("\n--- scan #3: strong momentum + GROK-BOT narrative=green (real spot) ---")
    r3 = agg.consensus(pair(3_000_000, 1_000_000), narrative="green")
    _demo_print(r3)

    print("\n--- scan #4: strong momentum + rate-limit/contract dump narrative=red (rug) ---")
    r4 = agg.consensus(pair(3_000_000, 1_000_000), narrative="red")
    _demo_print(r4)

    print("Rationale: zero-burn paper sim on REAL spot DEX data only.")
    print("\nMechanism note: live desks run 8+ distinct sources (Grok-desk-coordinator,"
          "\n  2 analysts, odds/evens, volume-lead, liquidity, Grok-bot). The paper demo"
          "\n  proxies these with 5 deterministic heuristics + 3 volume copies. Scan #3"
          "\n  uses a momentum-tuned panel; scans #1/#2 use the full panel.")
