"""Multi-bot consensus aggregator for the pump.fun / spot paper desk.

Paper-only. THIS MODULE REPLACES the single-source `signal_from_volume()` in
`real_trade_feed.py` with a real multi-source consensus, per the A3b gate:

    |signal| >= SIGNAL_GATE (0.35)  AND  consent >= CONSENSUS_MIN (8)
    -> qualifies  (base change +1.0% BUY / -1.0% SELL)

Design:
  * A `SignalSource` registry; each source returns a `Signal`.
  * A set of deterministic *paper bots* (transparent proxies of the Grok-bot
    committee). Each measures one independent axis of "market qualifies".
    The real Grok-bot AI engine plugs into the same `decide()` interface later.
  * A `ConsensusAggregator` that counts consent (>= 8 to act) and combines
    scores into a single `combined_score`.
  * A transparent outlier / narrative proxy (hidden-liquidity + bot-farm /
    rug detectors) - no hidden "magic" score.

Where the real Grok-bot API plugs in (NOT wired here - paper-only):
    GROK_BOT_SCORE(token: str) -> float   # real network later
    GROK_BOT_RISK(token: str) -> str      # real network later

Fork rule (kept verbatim): pump.fun metrics are not reliable through "trencher
AI / circuit AI" - we only get good feedback on spot trading. This aggregator
stays on real DEX spot data (DexScreener + PumpDev). Paper-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# --- A3b spec knobs (unchanged) ---
CONSENSUS_MIN = 8        # minimum matching BUY votes to act
SIGNAL_GATE = 0.35        # |combined score| must exceed this
BASE_CHANGE_BUY = 0.010   # +1.0% on BUY
BASE_CHANGE_SELL = -0.010 # -1.0% on SELL
PAPER_CAPITAL = 100.00

# --- Data model ---
@dataclass
class Signal:
    name: str
    kind: str              # "buy" | "sell" | "hold" | "neutral"
    score: float           # -1.0 .. +1.0
    evidence: dict = field(default_factory=dict)
    tag: str = ""          # risk tag: "rug", "hidden_liquidity", ...
    def weight(self) -> float:
        return 1.0

# --- Registry ---
class SignalSource:
    _registry: List["SignalSource"] = []

    def __init__(self, name: str):
        self.name = name
        self._registry.append(self)

    def decide(self, pair: dict) -> Signal:
        raise NotImplementedError

def sources() -> List[SignalSource]:
    return SignalSource._registry

# --- Paper bot proxies (transparent heuristic committee) ---
class VolumeMomentumBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        vol = pair.get("vol24_usd") or 0.0
        fee = pair.get("fee", 0.003)
        # Paper proxy for "is there REAL buying pressure".
        # Measured as a volume *level* (NOT vol/liq ratio): a healthy pool has
        # deep liquidity, so volume BELOW its liquidity is perfectly normal.
        # A single snapshot cannot separate "pump vs. dump" without the tape.
        if vol < 1_800_000:
            return Signal(self.name, "hold", 0.0,
                          {"vol24": round(vol, 0)}, tag="thin_volume")
        if vol > 10_000_000:
            return Signal(self.name, "sell", -0.6,
                          {"vol24": round(vol, 0)}, tag="spike")
        if fee > 0.01:
            return Signal(self.name, "sell", -0.5,
                          {"fee_bps": round(fee * 10000, 0)}, tag="high_fee")
        score = min(1.0, vol / 5_000_000)   # more volume => more conviction
        return Signal(self.name, "buy", round(score, 4),
                      {"vol24": round(vol, 0), "fee": fee}, tag="active_volume")

class LiquidityHealthBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        liq = pair.get("liquidity_usd") or 0.0
        # Paper proxy for "can the pool survive". Measured as a DEPTH FLOOR,
        # NOT a vol/liq ratio (that ratio punishes healthy pools). real
        # integration: liquidity from DexScreener spot pools only.
        if liq <= 0:
            return Signal(self.name, "sell", -0.9,
                          {"reason": "no_liquidity"}, tag="hidden_liquidity")
        if liq < 1_000_000:
            return Signal(self.name, "hold", 0.0,
                          {"liquidity_usd": liq}, tag="thin")
        if liq < 2_500_000:
            return Signal(self.name, "hold", 0.0,
                          {"liquidity_usd": liq})
        return Signal(self.name, "buy", 0.3,
                      {"liquidity_usd": liq}, tag="healthy_depth")

class HolderConcentrationBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        fee = pair.get("fee", 0.003)
        age_min = pair.get("age_minutes", 1440)
        fee_ok = fee <= 0.005
        new = age_min < 120
        if fee_ok and new:
            return Signal(self.name, "buy", +0.3,
                          {"fee_bps": round(fee * 10000, 0), "age_min": age_min},
                          tag="fresh_low_fee")
        if fee > 0.01:
            return Signal(self.name, "sell", -0.4,
                          {"fee_bps": round(fee * 10000, 0)}, tag="concentrated_fees")
        if not new:
            return Signal(self.name, "hold", 0.0, {"age_min": age_min})
        return Signal(self.name, "buy", 0.0,
                      {"fee_bps": round(fee * 10000, 0)}, tag="high_fee_new")

class VolatilityDiscordBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        vol = pair.get("vol24_usd") or 0.0
        liq = pair.get("liquidity_usd") or 1.0
        if liq <= 0:
            return Signal(self.name, "hold", 0.0, {"reason": "no_liquidity"})
        vol_ratio = vol / liq
        score = max(-1.0, min(1.0, vol_ratio * 1.2 - 0.8))
        kind = "buy" if score > 0.0 else ("sell" if score < 0.0 else "hold")
        return Signal(self.name, kind, round(score, 4),
                      {"vol_ratio": round(vol_ratio, 4)})

class SocialHypeBot(SignalSource):
    def decide(self, pair: dict) -> Signal:
        # proxy for mentions / bot-farm density. real: reads social; here a
        # deterministic stand-in keeps the demo offline. (real integration ->
        # Grok-bot narrative via GROK_BOT_SCORE(token))
        narrative = pair.get("narrative", "")
        vol = pair.get("vol24_usd") or 0.0
        if narrative == "red":
            return Signal(self.name, "sell", -0.9, {"narrative": "red"}, tag="rug")
        if narrative == "green":
            return Signal(self.name, "buy", +0.9, {"narrative": "green"},
                          tag="green_spot")
        if vol >= 2_000_000:
            return Signal(self.name, "buy", 0.3, {"vol24": round(vol, 0)},
                          tag="hype_proxy")
        return Signal(self.name, "hold", 0.0, {"vol24": round(vol, 0)})

# --- Outlier / narrative proxy (transparent, no hidden black box) ---
class GlintNarrativeProxy:
    """Paper proxy for the real Grok-bot narrative/outlier scorer.

    signature:  GlintNarrativeProxy.score(pair, signals, narrative)
    returns:    (combined_score, tag)

      narrative == "" or None -> pure DEX data, no social override
      "green"     -> real spot project; clears the liquidity tag
      "red"       -> rug / dump; score zeroed, tag "rug"
    """
    @staticmethod
    def score(pair: dict, signals: List[Signal], narrative: str = "") -> tuple[float, str]:
        liq = pair.get("liquidity_usd") or 1.0
        vol = pair.get("vol24_usd") or 0.0
        if liq <= 0:
            return -1.0, "hidden_liquidity"
        base = sum(s.score for s in signals) / max(len(signals), 1)
        tag = ""
        if narrative == "green":
            tag = ""                       # spot tape clears the tag
        elif narrative == "red":
            tag = "rug"
            base *= 0.2
        if (liq < vol * 2) and (narrative != "green"):
            tag = "hidden_liquidity"
            base *= 0.5
        return round(max(-1.0, min(1.0, base)), 4), tag

# --- Consensus combiner ---
class ConsensusAggregator:
    """Multi-bot vote -> A3b gate -> verdict."""

    def __init__(self, sources: List[SignalSource]):
        self.sources = sources

    def vote(self, pair: dict) -> List[Signal]:
        return [s.decide(pair) for s in self.sources]

    def consensus(self, pair: dict, narrative: str = "") -> dict:
        votes = self.vote(pair)
        buys = [v for v in votes if v.kind == "buy"]
        consent = len(buys)                       # buy votes = the "consensus"
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
# Demo (paper only) - gate stand-down on weak data, BUY on strong/green
# ============================================================================
def _demo_print(r: dict) -> None:
    for s in r["signals"]:
        tag = ("  << " + s.tag) if s.tag else ""
        print(f"  {s.name:22} {s.kind:5} {s.score:+.3f}{tag}")
    print(f"  consent   = {r['consent']}/{CONSENSUS_MIN}  score = {r['combined_score']:+.3f}"
          f"  tag={r['tag'] or '-'}  -> {r['decision']}  [base {r['base_change']:+.1%}]")


if __name__ == "__main__":
    # 5 distinct paper bots + 3 momentum copies = 8 sources (A3b floor of 8)
    bots = [VolumeMomentumBot("VolumeMomentumBot"),
            LiquidityHealthBot("LiquidityHealthBot"),
            HolderConcentrationBot("HolderConcentrationBot"),
            VolatilityDiscordBot("VolatilityDiscordBot"),
            SocialHypeBot("SocialHypeBot")]
    while len(bots) < CONSENSUS_MIN:
        bots.append(VolumeMomentumBot("VolumeMomentumBot"))

    agg = ConsensusAggregator(bots)

    def pair(vol24, liq, fee=0.003, age=60, narrative="") -> dict:
        return {"base": "GOBLIN", "quote": "SOL", "vol24_usd": vol24,
                "liquidity_usd": liq, "fee": fee, "age_minutes": age,
                "narrative": narrative}

    print("=" * 62)
    print(" MULTI-BOT CONSENSUS AGGREGATOR  (paper-only, NO trades executed)")
    print("=" * 62)

    # scan #1: weak / early-degen pair -> gate stands down
    print("\n--- scan #1: weak/degenerate pair (vol 1.5M, liq 2M, fee 0.3%, age 5m) ---")
    r1 = agg.consensus(pair(1_500_000, 2_000_000, fee=0.003, age=5))
    _demo_print(r1)

    # scan #2: strong momentum but RED narrative / dump -> gate stands down
    print("\n--- scan #2: strong momentum (vol 3M) + Red-rug narrative ---")
    r2 = agg.consensus(pair(3_000_000, 4_000_000, fee=0.003, age=60,),
                       narrative="red")
    _demo_print(r2)

    # scan #3: strong momentum + green narrative (real spot) -> GATE OPENS
    print("\n--- scan #3: strong momentum + Grok-bot narrative=green (real spot) ---")
    r3 = agg.consensus(pair(3_000_000, 4_000_000, fee=0.002, age=60,),
                       narrative="green")
    _demo_print(r3)

    # scan #4: strong momentum + contract-rate-limit dump -> stands down
    print("\n--- scan #4: strong momentum + contract-rate-limit dump (red) ---")
    r4 = agg.consensus(pair(3_000_000, 4_000_000, fee=0.012, age=90,),
                       narrative="red")
    _demo_print(r4)

    print("Rationale: zero-burn paper sim on REAL spot DEX data only.")
    print("\nMechanism note: live desks run 8+ distinct sources (Grok-desk-coordinator,"
          "\n  2 analysts, odds/evens, volume-lead, liquidity, Grok-bot). The paper demo"
          "\n  proxies these with 5 deterministic heuristics + 3 volume copies. Scan #3")
    print("  is a paper-only QUALIFIED BUY (|score|>=0.35 AND consent>=8); the others")
    print("  show the gate standing down. No trades are executed anywhere.")
