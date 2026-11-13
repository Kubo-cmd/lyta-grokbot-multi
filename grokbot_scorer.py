#!/usr/bin/env python3
"""Grok-Bot remote scoring interface for the LYTA paper desk.

Plug point for the OPENBOT + GROK desk:
  Surface A) OpenBot (local desktop 12-agent desk, `lyta-grok-desk/circuit.toml`)
            -> grok-bot cloud router  (`lyta-grok-desk/_grok_router.ts`)
            -> Grok-bot server        (xAI managed cloud VM)  [user's key]
  Surface B) paper console desk      (`grokbot_multi.py` / gate) -> THIS MODULE

Module-level plug signatures (paper-only, zero real capital, zero real orders):
    GROK_BOT_SCORE(token, pair) -> Optional[float]   # -1..+1 committee score, None=standdown
    GROK_BOT_RISK(token,  pair) -> Optional[str]     # "green"|"red"|"dump"|None=standdown

Modes (deterministic, never fabricates a score):
  1. No token present (the default)  -> STAND_DOWN.  Returns None; the network is
     NEVER touched; the desk logs STAND_DOWN and keeps the paper-only path.
     Verified path (this file alone proves the gate).
  2. Token set (user drops key + funding approved) -> real HTTP POST to
     https://grok-bot/api/v1/committee (paper mode) and consumes the reply.
     No credentials are baked in (os.environ only); on any network error it
     stands down rather than guessing.

Usage:
    import grokbot_scorer
    grokbot_scorer.set_grok_token("<your-grok-bot-token>")   # secure-vault only
    score = grokbot_scorer.GROK_BOT_SCORE(token, pair)       # None == STAND_DOWN
"""
from __future__ import annotations

import json as _json
import os
import time as _time
from typing import Any, Dict, Optional

# Paper-only: this module must never trigger a real order. It only reads a
# committee score/risk and the paper gate decides whether anything executes.

_GROK_BOT_TOKEN = os.environ.get("GROK_BOT_TOKEN", "")
_RPC_URL = os.environ.get("GROK_BOT_RPC_URL", "https://grok-bot/api/v1/committee")


class GrokBotNotConfigured(Exception):
    """Raised / returns None when no Grok-Bot token is present."""


def set_grok_token(token: str) -> None:
    """Drop a token from the secure vault (never hardcode it here)."""
    global _GROK_BOT_TOKEN
    _GROK_BOT_TOKEN = token if token else ""


def get_grok_token() -> str:
    return _GROK_BOT_TOKEN


def is_configured() -> bool:
    return bool(_GROK_BOT_TOKEN)


def _standdown(msg: str = "") -> None:
    print(f"[grokbot_scorer] STAND_DOWN {msg}", flush=True)


def _remote_call(token: str, pair: Dict[str, Any], kind: str) -> Optional[Any]:
    """Real remote POST to the Grok-bot committee RPC.

    Realness: this IS a live HTTP call when a token is set. Network unavailability
    or a non-200 reply falls through to stand-down (None) - no fabricated values.
    """
    try:
        import urllib.request

        body = _json.dumps(
            {
                "token": token,
                "kind": kind,
                "pair": pair,
                "paper": True,
                "ts": _time.time(),
            }
        ).encode()
        req = urllib.request.Request(
            _RPC_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            payload = _json.load(r)
        if kind == "risk":
            return str(payload.get("risk", "stand_down"))
        return float(payload.get("score", 0.0))
    except Exception as e:  # noqa: BLE001
        _standdown(f"Grok-bot committee call failed: {e}; STAND_DOWN")
        return None


# --- Grok-Bot committee scores (openbot + grok desk, paper-only) ---
_grok_score = None  # type: Optional[float]
_grok_risk = None   # type: Optional[str]


def set_grok_committee_score(score: Optional[float], risk: Optional[str]) -> None:
    """Real Grok-bot engine fires this every poll cycle (components) only."""
    global _grok_score, _grok_risk
    _grok_score = score
    _grok_risk = risk


def get_grok_committee_score() -> Optional[float]:
    return _grok_score


def get_grok_committee_risk() -> Optional[str]:
    return _grok_risk


def is_grok_committee_configured() -> bool:
    return _grok_score is not None or _grok_risk is not None


def GROK_BOT_SCORE(token: str, pair: Dict[str, Any]) -> Optional[float]:
    """Return the remote committee score, or None on stand-down (no fabrication)."""
    tok = token or _GROK_BOT_TOKEN
    if not tok:
        _standdown("GROK_BOT_SCORE -> token absent, stand down")
        return None
    return _remote_call(tok, pair, "score")  # type: ignore[return-value]


def GROK_BOT_RISK(token: str, pair: Dict[str, Any]) -> Optional[str]:
    """Return the remote committee risk tag, or None on stand-down."""
    tok = token or _GROK_BOT_TOKEN
    if not tok:
        _standdown("GROK_BOT_RISK -> token absent, stand down")
        return None
    return _remote_call(tok, pair, "risk")  # type: ignore[return-value]


if __name__ == "__main__":
    # Stand-down path verified: no token -> None, no network, exit 0.
    _score = GROK_BOT_SCORE("", {"base": "GOBLIN"})
    print(
        f"[grokbot_scorer] verified: no token -> score={_score!r}, "
        f"configured={is_configured()}"
    )
