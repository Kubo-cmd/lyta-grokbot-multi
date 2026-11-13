"""Real trade-info feed for the pump.fun / spot paper desk.

Paper-only: NO real trades are executed. This module pulls REAL pump.fun /
spot data from two verified sources and runs the SAME A3b paper logic as
paper_run.py:

  Source 1 - DexScreener REST (free, no key): live pair quotes
            GET https://api.dexscreener.com/latest/dex/search?q={q}&limit={n}

  Source 2 - PumpDev WebSocket (free, no key): real-time pump.fun events
            wss://pumpdev.io/ws
            methods: subscribeNewToken, subscribeTokenTrade (need a mint)

Specification replicated here (unchanged from paper_run.py):
  config v3 | asset GOBLIN | capital $100.00 | PAPER-ONLY
  CONSENSUS_MIN = 8      | |signal| >= 0.35  -> qualifies
  BASE_CHANGE_BUY = +0.010 (+1.0%) | BASE_CHANGE_SELL = -0.010 (-1.0%)

REPLACEMENT NOTICE (consensus): paper_run.py's real multi-bot buy-vote
(>=5 consent) cannot be reproduced from a single data source. The proxy in
signal_from_volume() returns a derived signal and a single "present" tick.
Wire the Grok-bot / coingecko outlier aggregator here to restore the real
multi-bot consensus. Live events (Source 2) give real mint-trade signals.
"""
import json
import subprocess
import urllib.parse
import urllib.request

DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"

# === A3b paper knobs (unchanged from paper_run.py) ===
CONSENSUS_MIN = 8
SIGNAL_GATE = 0.35      # |signal| >= 0.35 qualifies for a trade
BASE_CHANGE_BUY = 0.010 # +1.0% on BUY
BASE_CHANGE_SELL = -0.010 # -1.0% on SELL
PAPER_CAPITAL = 100.00
ASSET = "GOBLIN"


# --------------------------------------------------------------------------
# Source 1: DexScreener REST (real pair quotes)
# --------------------------------------------------------------------------
def fetch_pairs(query="pump", limit=20):
    cmd = [
        "curl", "-s", "--max-time", "20",
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "-H", "Accept: application/json",
        f"{DEXSCREENER_BASE}/search?q={urllib.parse.quote(query)}&limit={limit}",
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return _parse_pairs(json.loads(out))


def _parse_pairs(raw):
    out = []
    for p in raw.get("pairs", []):
        out.append({
            "chain": p.get("chainId"),
            "dex": p.get("dexId"),
            "pair_id": p.get("pairAddress"),
            "base": p.get("baseToken", {}).get("symbol"),
            "quote": p.get("quoteToken", {}).get("symbol"),
            "price_usd": float(p.get("priceUsd") or 0.0),
            "liquidity_usd": float(p.get("liquidity", {}).get("usd") or 0.0),
            "vol24_usd": float((p.get("volume") or {}).get("h24") or 0.0),
        })
    return sorted(out, key=lambda x: x["liquidity_usd"], reverse=True)


# --------------------------------------------------------------------------
# Source 2: PumpDev WebSocket (real-time pump.fun events)
# --------------------------------------------------------------------------
class PumpDevStream:
    """Subscribe to live pump.fun events (new tokens / trades) via WS."""

    def __init__(self, on_event, max_events=20, timeout=30.0):
        self.on_event = on_event
        self.max_events = max_events
        self.timeout = timeout

    async def _listen(self):
        import asyncio
        import websockets
        async with websockets.connect("wss://pumpdev.io/ws", ping_interval=None) as ws:
            await ws.send(json.dumps({"method": "subscribeNewToken"}))
            count = 0
            while count < self.max_events:
                msg = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
                ev = json.loads(msg)
                if "result" not in ev:
                    self.on_event(ev)
                    count += 1

    def listen(self):
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(self._listen())
        except Exception as e:
            print(f"[feed] WS error: {e}")


# --------------------------------------------------------------------------
# A3b paper signal gate (applied to real data)
# --------------------------------------------------------------------------
def signal_from_volume(pair):
    """Paper-only signal proxy. REPLACEMENT NOTICE applies; single tick."""
    if pair["liquidity_usd"] <= 0:
        return {"signal": 0.0, "consensus": 0, "pair": pair,
                "reason": "no_liquidity"}
    momentum = min(pair["vol24_usd"] / max(pair["liquidity_usd"], 1.0), 5.0)
    signal = round(max(-1.0, min(1.0, (momentum - 1.0) * 0.5)), 4)
    return {"signal": signal, "consensus": 1, "pair": pair}


def qualify(pair, verbose=True):
    s = signal_from_volume(pair)
    reasons = []
    if abs(s["signal"]) < SIGNAL_GATE:
        reasons.append(f"signal_gate ({s['signal']:+.2f} < {SIGNAL_GATE})")
        s["gate_reasons"] = reasons
        if verbose:
            print(f"    [STAND DOWN] {pair['dex']} {pair['base']}/{pair['quote']}"
                  f" signal={s['signal']:+.3f} | {', '.join(reasons)}")
        return s
    if s["consensus"] < CONSENSUS_MIN:
        reasons.append(f"consensus_min ({s['consensus']}/{CONSENSUS_MIN})")
        s["gate_reasons"] = reasons
        if verbose:
            print(f"    [STAND DOWN] {pair['dex']} {pair['base']}/{pair['quote']}"
                  f" signal={s['signal']:+.3f} consensus={s['consensus']}"
                  f" | {', '.join(reasons)}")
        return s
    return s


class RealTradeFeed:
    """Live real-data wrapper around the A3b paper logic (paper-only)."""

    def __init__(self, paper_capital=PAPER_CAPITAL, config="v3", asset=ASSET):
        self.paper_capital = paper_capital
        self.config = config
        self.asset = asset

    def fetch(self, query="pump", limit=20):
        return fetch_pairs(query=query, limit=limit)

    def qualify(self, pair):
        return qualify(pair)
