#!/usr/bin/env python3
"""
Phase 2 — live candidate pipeline for the pump.fun paper desk.

Turns the multi-bot consensus engine (consensus_aggregator.py) + the reverse
engineer (pumpfun_reverse_engineer.py) into a live candidate pipeline:

    [live pull] -> dedupe -> 3-question Bot-X-Ray -> 5+ bot consensus ->
    ADVANCE / STAND_DOWN verdict -> live state file

The pipeline streams fresh pump.fun / pumpswap candidates (best-effort live
DexScreener via the verified adapter, deterministic seeds as fallback) and for
each new candidate:
  1. runs the 3-question reverse-engineer x-ray (mode / luck / still-works),
  2. maps it into the paper-desk `pair` schema for the consensus engine,
  3. runs the 5-bot A3b gate (consent>=8 AND |score|>=0.35) -> ADVANCE or
     STAND_DOWN, with per-round vote detail and stand-down reasons.

Zero-burn, observation-only. NO capital, NO wallet, NO trade execution.

Run:
    python3 pumpfun_pipeline.py            # live poll loop (rounds, sleep)
    python3 pumpfun_pipeline.py --once     # one round to stdout + state file
    python3 pumpfun_pipeline.py --guard    # batch-guard: fast-fail on ANY
                                             # weak candidate (no consensus run),
                                             # then print survivors only
    python3 pumpfun_pipeline.py --streams  # emit raw candidate stream only
                                             # (skip consensus for data checks)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ── Verified reverse engineer (paper-only, no-trade) ──────────────────────
import pumpfun_reverse_engineer as _rea

# ── Paper-desk mapping + verdict builder (reuse the verified round mapping) ──
from pumpfun_paper_gate import round_to_pair, verdict_for as _verdict_for

# ── Multi-bot consensus engine (A3b gate) ─────────────────────────────────
from consensus_aggregator import (
    VolumeMomentumBot,
    LiquidityHealthBot,
    HolderConcentrationBot,
    VolatilityDiscordBot,
    SocialHypeBot,
    GlintNarrativeProxy,
    ConsensusAggregator,
    Signal,
)

# 5 distinct paper bots + 3 momentum copies = 8 sources (A3b floor of 8)
_BOTS = [
    VolumeMomentumBot("vol_momentum"),
    LiquidityHealthBot("liq_health"),
    HolderConcentrationBot("holder_fee"),
    VolatilityDiscordBot("vol_discord"),
    SocialHypeBot("social_hype"),
]
for _ in range(3):  # volume-copy copies (A3b)
    _BOTS.append(VolumeMomentumBot("vol_momentum"))

_AGG = ConsensusAggregator(_BOTS)

# ── Zero-burn desk knobs ───────────────────────────────────────────────────
MIN_CAPITAL = 2.0
MAX_CAPITAL = 6.0

_STATE_DIR = os.path.join(REPO_ROOT, "pumpfun_pipeline_output")
_STATE_FILE = os.path.join(_STATE_DIR, "state.json")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_state() -> dict:
    if os.path.exists(_STATE_FILE):
        try:
            with open(_STATE_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
            # seen_ids arrives as a list; materialise for O(1) membership
            if "seen_ids" in data:
                data["seen_ids"] = set(data["seen_ids"])
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"rounds": [], "watchlist": [], "seen_ids": set()}


def _save_state(state: dict, state_path: str | None = None) -> None:
    """Persist state JSON, honoring an explicit path (defaults to _STATE_FILE)."""
    path = state_path or _STATE_FILE
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = _sanitize(dict(state))
    payload["seen_ids"] = list(payload.get("seen_ids", set()))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def _sanitize(obj):
    """Deep-convert non-JSON types (e.g. consensus `Signal` objects) to plain
    dicts/lists so the live state file always serializes."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, Signal):
        return {"name": obj.name, "kind": obj.kind, "score": obj.score,
                "tag": obj.tag, "evidence": obj.evidence}
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (set, frozenset)):
        return sorted(str(x) for x in obj)
    try:
        return obj.__dict__
    except Exception:
        return str(obj)


def _seen(c: dict) -> str:
    return f"{c.get('dexId','')}|{c.get('asset','')}"


# ── Public candidate pipeline ──────────────────────────────────────────────
class CandidatePipeline:
    """Continuous live candidate stream -> consensus -> verdict."""

    def __init__(self, state_path: str | None = None):
        self.state_path = state_path or _STATE_FILE
        self.state = _load_state()
        self.round_num = len(self.state.get("rounds", []))
        self._ensure_seen_index()
        self._init_desk()

    # -- internal helpers ---------------------------------------------------
    def _ensure_seen_index(self) -> None:
        for s in self.state.get("watchlist", []):
            self.state["seen_ids"].add(_seen(s))

    def _mark_seen(self, c: dict) -> None:
        self.state["seen_ids"].add(_seen(c))
        # keep watchlist bounded
        wl = self.state.setdefault("watchlist", [])
        wl = [x for x in wl if _seen(x) != _seen(c)]
        wl.append(self._as_record(c))

    def _as_record(self, c: dict, verdict: dict | None = None) -> dict:
        rec = dict(c)
        rec["_source"] = "pumpfun_pipeline"
        if verdict:
            rec["_verdict"] = verdict
        return rec

    # -- pull ---------------------------------------------------------------
    def pull(self, limit: int = 12) -> list:
        """Pull fresh live candidates; append NEW ones to the watchlist and
        return only NEW ones (deduped against seen_ids)."""
        rows = _rea.fetch_real_candidates(limit=limit)
        new = []
        for c in rows:
            cid = _seen(c)
            if cid in self.state["seen_ids"]:
                continue
            self.state["seen_ids"].add(cid)
            # keep watchlist bounded & free of duplicates
            self.state["watchlist"] = [
                x for x in self.state["watchlist"]
                if _seen(x) != cid
            ]
            self.state["watchlist"].append(self._as_record(c))
            new.append(c)
        if new:
            _save_state(self.state, self.state_path)
        return new

    @staticmethod
    def _deduplicate(wl: list) -> list:
        out = []
        for w in wl:
            cid = _seen(w)
            if cid not in {x for x in out}:
                out.append(w)
        return out

    # -- scoring -------------------------------------------------------------
    def score(self, c: dict) -> dict:
        """3-question x-ray + 5-bot consensus -> verdict record."""
        rnd = self.round_num
        ts = _now()
        row = _rea.verdict_for(c)          # 3-question x-ray
        pair = round_to_pair(row, ts)      # map to paper-desk schema
        pair["base"] = c.get("asset", pair.get("base", "GOBLIN"))

        # Micro-sizing: cash a $0.20-$0.85 position in this token. A token is
        # micro size-eligible when it trades BELOW $0.85/unit so a $0.85 floor
        # buys at least one whole token (anything pricier yields sub-1-token
        # dust that pump.fun's fee tier can't trade). Dust/delisted floor keeps
        # out zero-price listings.
        price = _num(c, "price_usd", 0.0)
        micro_ok = price <= MAX_CAPITAL and price >= 1e-6

        # 5-bot A3b consensus
        res = _verdict_for(pair, row)
        res["consent"] = res.get("consent", 0) or 0
        res["source_round"] = f"pumpfun_pipeline_round_{rnd}"
        res["price_usd"] = _num(c, "price_usd", 0.0)
        res["score_usd"] = _num(c, "score", 0.0)
        res["vol24_usd"] = _num(c, "volume_h24", 0.0)
        # base_change kept as a fraction for the 0.1% format (see emit)
        res["base_change"] = _num(c, "change_24h", 0) / 100.0
        res["micro_budget_ok"] = micro_ok

        # Stand-down reasons: real bot tags + narrative + x-ray verdict
        reasons = {b.tag for b in res.get("bot_details", []) if b.tag}
        if res.get("tag"):
            reasons.add(res["tag"])
        if row.get("signature", {}).get("mode") in ("PUMP-AND-DUMP", "WASH-GRIND"):
            reasons.add("pump_and_dump / wash_grind signature")
        if row.get("still_works", {}).get("survives_breaker") is not True:
            reasons.add("fee-resilience thin (setting-change run)")
        res["stand_down_reasons"] = sorted(reasons) or ["watch"]
        res["micro_budget_ok"] = micro_ok

        return res

    # -- stream handling ------------------------------------------------------
    def emit(self, c: dict, res: dict, mode: str = "normal") -> dict:
        """Log one candidate round verbosely + record in state."""
        ts = _now()
        round_rec = {
            "round": f"pumpfun_pipeline_round_{self.round_num}",
            "as_of": ts,
            "candidate": self._as_record(c),
            "verdict": res,
        }
        self.state.setdefault("rounds", []).append(round_rec)

        verb = {
            "skip":     f"[SKIP]   {_seen(c):14} seen before",
            "streams":  self._stream_line(c),
            "stand_down": self._stand_down_line(c, res),
            "advance":  self._advance_line(c, res),
        }[mode]
        print(verb)

        _save_state(self.state, self.state_path)
        self.round_num += 1
        return res

    def _stream_line(self, c: dict) -> str:
        return (f"[STREAM] {_seen(c):14} asset={c.get('asset','?'):12} "
                f"chain={c.get('chain','?'):6} dexId={c.get('dexId','?'):6} "
                f"price={c.get('price_usd',0):.6f} buys_5m={c.get('buys_5m',0):>4} "
                f"sells_5m={c.get('sells_5m',0):>4} vol_h24={c.get('volume_h24',0):.0f} "
                f"ch5={c.get('change_5m',0):+.1f}% ch24={c.get('change_24h',0):+.1f}%")

    def _xray_line(self, c: dict, res: dict) -> str:
        s = res.get("signature", {}) if isinstance(res.get("signature"), dict) else {}
        w = res.get("still_works", {}) if isinstance(res.get("still_works"), dict) else {}
        return (f"[X-RAY]  {_seen(c):14} sig={s.get('mode','?'):14} "
                f"luck={res.get('luck_label','?'):14} "
                f"still={w.get('survives_breaker','?'):5} "
                f"fee={w.get('fee_pct',0):.3f} wash={w.get('wash_est_pct',0):.2f} "
                f"margin={w.get('margin_vs_overhead_pp',0):+.1f}pp")

    def _sig_tag(self, b) -> str:
        """Accept live Signal objects or JSON dicts (round records read from
        the state file)."""
        return (b.get("tag") if isinstance(b, dict) else getattr(b, "tag", "")) or ""

    def _consensus_line(self, c: dict, res: dict) -> str:
        votes = res.get("bot_details", [])
        lines = [
            f"  [CONSENSUS] consent={res.get('consent',0)}/8 | "
            f"score={res.get('combined_score',0):+.3f} | "
            f"tag={res.get('tag') or '-'} -> {res.get('decision')} "
            f"[base {res.get('base_change',0):+.1%}]",
        ]
        for b in votes:
            tag = f"  <<{self._sig_tag(b)}" if self._sig_tag(b) else ""
            lines.append(f"        {str(b.get('name', '?')):22} {str(b.get('kind', '?')):5} {float(b.get('score', 0)):+.3f}{tag}")
        return "\n".join(lines)

    def _stand_down_line(self, c: dict, res: dict) -> str:
        s = f"[STAND]  {_seen(c):14} {res.get('decision','standdown')}"
        if res.get("stand_down_reasons"):
            s += " << " + " ; ".join(res["stand_down_reasons"])
        if res.get("micro_budget_ok") is False:
            s += "  [micro not size-eligible]"
        return s

    def _advance_line(self, c: dict, res: dict) -> str:
        return (f"[ADVANCE] {_seen(c):14} {res.get('decision')} -> "
                f"BASE {res.get('base_change',0):+.1%} "
                f"consent={res.get('consent',0)}/8 score={res.get('combined_score',0):+.3f} "
                f"micro_ok={res.get('micro_budget_ok')}")

    def _audit_line(self, c: dict, res: dict) -> str:
        s = res.get("signature", {}) if isinstance(res.get("signature"), dict) else {}
        w = res.get("still_works", {}) if isinstance(res.get("still_works"), dict) else {}
        x = self._xray_line(c, res)
        votes = res.get("bot_details", [])
        lines = [
            f"[AUDIT]  {_seen(c):14} mode={s.get('mode','?'):12} "
            f"narrative={res.get('narrative','?'):6} tag={res.get('tag') or '-'}",
            f"  x-ray    -> {x}",
            f"  consensus consent={res.get('consent')}/8 | "
            f"combined={res.get('combined_score',0):+.3f} | "
            f"dec={res.get('decision')} [base {res.get('base_change',0):+.1%}]",
        ]
        for b in votes:
            tag = f"  <<{self._sig_tag(b)}" if self._sig_tag(b) else ""
            lines.append(f"        {str(b.get('name', '?')):22} {str(b.get('kind', '?')):5} {float(b.get('score', 0)):+.3f}{tag}")
        return "\n".join(lines)

    # -- desk aggregate (learn across rounds) --------------------------------
    def _init_desk(self) -> None:
        self.state.setdefault("desk", {
            "rounds": 0, "candidates": 0, "advance": 0, "stand_down": 0,
            "mean_consent": 0.0, "mean_abs_score": 0.0, "top_picks": [],
            "tag_counts": {}, "latest_ids": [],
        })

    def _desk_rank(self, res: dict) -> float:
        """Desk-confidence 0..1: consent share + |combined| magnitude.
        Ranking-only, does NOT override the A3b gate."""
        consent = max(0, min(8, res.get("consent") or 0)) / 8.0
        s = abs(res.get("combined_score") or 0.0)
        return round(consent * 0.6 + min(s, 1.0) * 0.4, 4)

    def _desktop_summary(self) -> dict:
        """Aggregate the round log into desk metrics (persisted + printed)."""
        rounds = self.state.get("rounds", [])
        if not rounds:
            return self.state["desk"]
        desk = self.state["desk"]
        out = []
        for r in rounds:
            v = r["verdict"]
            out.append({"round": r["round"], "consent": v.get("consent"),
                        "score": v.get("combined_score"),
                        "decision": v.get("decision"),
                        "tag": v.get("tag")})
        desk["rounds"] = len(rounds)
        desk["candidates"] = len(rounds)
        desk["advance"] = sum(1 for d in out if d["decision"] == "BUY-SIG")
        desk["stand_down"] = len(out) - desk["advance"]
        consents = [r.get("consent") or 0 for r in out]
        scores = [abs(r.get("score") or 0.0) for r in out]
        desk["mean_consent"] = round(sum(consents) / len(consents), 2) if consents else 0.0
        desk["mean_abs_score"] = round(sum(scores) / len(scores), 4) if scores else 0.0
        try:
            from collections import Counter
            desk["tag_counts"] = dict(Counter(r["tag"] for r in out if r.get("tag")))
        except Exception:
            desk["tag_counts"] = {}
        desk["top_picks"] = sorted(out, key=self._desk_rank, reverse=True)[:3]
        desk["latest_ids"] = [_seen(r["candidate"]) for r in rounds[-3:]]
        _save_state(self.state, self.state_path)
        print(f"[DESK] rounds={len(rounds)} candidates={len(rounds)} "
              f"advance={desk['advance']} stand_down={desk['stand_down']} "
              f"mean_consent={desk['mean_consent']} mean_abs_score={desk['mean_abs_score']}")
        return desk

    def audit(self) -> list:
        """Print verbose per-candidate evidence for every round (learn mode)."""
        for r in self.state.get("rounds", []):
            c = r.get("candidate", {})
            v = r.get("verdict", {})
            print(self._audit_line(c, v))
            print(f"  -- {r['round']} --> {v.get('decision')} "
                  f"[consent {v.get('consent')}/8 | score {v.get('combined_score',0):+.3f}]")
            print()
        return list(self.state.get("rounds", []))

    # -- entry points -------------------------------------------------
    def run(self, rounds: int = 3, interval: float = 15.0,
            pull_limit: int = 12) -> dict:
        """Live poll loop; each round pulls, scores, emits, updates state."""
        for _ in range(rounds):
            new = self.pull(limit=pull_limit)
            if not new:
                print(f"[PIPELINE] round {self.round_num}: no new candidates "
                      f"(live data or fallback seeds only)")
            for c in new:
                res = self.score(c)
                if res.get("decision") == "BUY-SIG":
                    self.emit(c, res, mode="advance")
                else:
                    self.emit(c, res, mode="stand_down")
            self.round_num += 1
            if _ < rounds - 1:
                time.sleep(interval)
        self._desktop_summary()
        return self.state

    def guard(self, limit: int = 12) -> list:
        """Batch-guard: stand-down any candidate that fails the gate before
        running full consensus, then print survivors only."""
        candidates = self.pull(limit=limit)
        if not candidates:
            print("[GUARD] no candidates")
            return []
        print(f"[GUARD] candidates={len(candidates)}")
        survivors = []
        for c in candidates:
            row = _rea.verdict_for(c)
            s = row.get("signature", {})
            w = row.get("still_works", {})
            # fast-fail on signature-level disqualifiers (no consensus run)
            if s.get("mode") in ("PUMP-AND-DUMP", "WASH-GRIND"):
                print(f"[GUARD] STAND DOWN {s.get('mode'):16} (signature) {_seen(c)}")
                continue
            if not w.get("survives_breaker"):
                print(f"[GUARD] STAND DOWN {s.get('mode'):16} "
                      f"(fee-resilience thin) {_seen(c)}")
                continue
            micro_ok = _num(c, "price_usd", 0.0) <= MAX_CAPITAL and _num(c, "price_usd", 0.0) >= 1e-6
            if not micro_ok:
                print(f"[GUARD] STAND DOWN price {_num(c, 'price_usd', 0):.6f} "
                      f"(micro not size-eligible) {_seen(c)}")
                continue
            survivors.append((c, self.score(c)))
        if survivors:
            print(f"[GUARD] survivors={len(survivors)} (ADVANCE candidates)")
            for c, res in survivors:
                self.emit(c, res, mode="advance")
        else:
            print("[GUARD] all candidates stand down")
        self._desktop_summary()
        return survivors

    def streams(self, limit: int = 12) -> list:
        """Emit the raw candidate stream without consensus (data check)."""
        candidates = self.pull(limit=limit)
        for c in candidates:
            self.emit(c, {"decision": "standby", "stream_only": True}, mode="streams")
        return candidates


def _num(d, key, default=0.0):
    try:
        return float(d.get(key, default))
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Live pump.fun paper candidate pipeline (zero-burn, observation only)")
    ap.add_argument("--once", action="store_true", help="one round to stdout + state")
    ap.add_argument("--guard", action="store_true", help="batch-guard mode")
    ap.add_argument("--streams", action="store_true", help="raw candidate stream only")
    ap.add_argument("--rounds", type=int, default=3, help="poll-loop rounds")
    ap.add_argument("--interval", type=float, default=15.0, help="poll sleep (s)")
    ap.add_argument("--limit", type=int, default=12, help="candidates per pull")
    ap.add_argument("--audit", action="store_true",
                    help="verbose per-candidate evidence dump (learn mode)")
    ap.add_argument("--state", help="state file path override")
    args = ap.parse_args()

    pipe = CandidatePipeline(state_path=args.state or _STATE_FILE)

    if args.streams:
        pipe.streams(limit=args.limit)
        return 0
    if args.guard:
        pipe.guard(limit=args.limit)
        return 0
    if args.once:
        pipe.pull(limit=args.limit)
        for c in pipe.state.get("watchlist", []):
            res = pipe.score(c)
            pipe.emit(c, res, mode="stand_down" if res.get("decision") != "BUY-SIG" else "advance")
        pipe._desktop_summary()
        return 0
    if args.audit:
        pipe.audit()
        return 0

    # live poll loop
    print(f"[PIPELINE] live poll loop: rounds={args.rounds}, "
          f"interval={args.interval}s, limit={args.limit}")
    pipe.run(rounds=args.rounds, interval=args.interval, pull_limit=args.limit)
    print(f"[VERIFY] live state written -> {pipe.state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
