"""OPTION C — your own way (custom strategy).

Plug your strategy into the shared PaperDesk engine WITHOUT rebuilding the
gate, the paper-only capital guard, or the stand-down logging. The engine is
shared verbatim between OpenBot (A) and GrokBot (B): you only replace the
advice/vote/execute columns.

PLUGGABLE POINTS (all on the shared engine):
  1. advice_fn  — your scoring of a pair given the current votes.
     Returns a float (composite advisory).  Default: OpenBot spot heuristics.
  2. vote_fn    — your list of per-bot votes.  Defaults to the 12 OpenBot agents.
     Returns {name: Signal} or {name: (kind, score, tag)}.
  3. execute_fn — your paper buy/exit logic.  Defaults to the paper position
     sizing in _default_execute (min(capital*0.01, 5.0), trigger-only).

RUN NAVIGATION:
    cd /Users/test/projects/lyta-grokbot-multi
    python3 lyta-grok-desk/option_c_template.py --minutes 0.3 --interval 1

Then compare against:
    A. python3 paper_run.py        (OpenBot 12-agent)
    B. python3 grokbot_multi.py    (GrokBot 11-agent committee)
"""


def YOUR_STRATEGY_HERE(pair, votes):
    """REPLACE THIS BODY with your own scoring logic.

    Inputs:
      pair     -- the market pair dict (symbol, base, quote, price, pair_type, ...)
      votes    -- engine's normalized votes: {name: {"sym","name","kind","score","tag"}}

    Return: a float advisory score (positive = bias toward buy, negative = sell,
            near zero = stand down).  Keep it honest and library-only; no key or
            live wallet is used on the paper path.

    EXAMPLE 1 -- 3-factor custom scout (trend, liquidity, rug):
        trend = pair.get("trend", 0.0)
        liq   = pair.get("liquidity", 0.0)
        rug   = pair.get("rug_risk", 0.0)
        return (trend * 0.6) + (liq * 0.3) - (rug * 0.4)

    EXAMPLE 2 -- momentum + contrarian hybrid, scaled to desk capital:
        snap = votes.get("SCOUT", {}).get("score", 0.0)
        wave = votes.get("CONTRARIAN", {}).get("score", 0.0)
        return (snap + wave) * 0.5
    """
    # ---- BEGIN YOUR CODE HERE ----
    # Default placeholder: score = net consensus of buy vs sell votes.
    # Replace with your own strategy — e.g. pull trend/liquidity/rug from
    # `pair` and combine with vote scores. Handles Signal objects or dicts.
    def _score(v):
        if isinstance(v, dict):
            return v.get("score", 0.0), v.get("kind")
        return v.score, v.kind

    buy_score = sum(s for s, k in (_score(v) for v in votes.values()) if k == "buy")
    sell_score = sum(s for s, k in (_score(v) for v in votes.values()) if k == "sell")
    return buy_score - sell_score
    # ---- END YOUR CODE HERE ----


def MY_VOTE_FN(pair):
    """REPLACE with your own set of voting agents if you do not want the
    default 12 OpenBot agents.  Returns {name: Signal}."""
    from lyta_grok_desk_paper_core import Signal
    default_votes = {
        "SCOUT":      Signal(name="SCOUT", kind="buy", score=0.62, tag="scout"),
        "FILTER":     Signal(name="FILTER", kind="buy", score=0.58, tag="filter"),
        "ANALYST":    Signal(name="ANALYST", kind="buy", score=0.71, tag="analyst"),
        "DEV_WATCH":  Signal(name="DEV_WATCH", kind="buy", score=0.45, tag="devwatch"),
        "CONVICTION": Signal(name="CONVICTION", kind="buy", score=0.68, tag="conviction"),
        "MOMENTUM":   Signal(name="MOMENTUM", kind="buy", score=0.77, tag="momentum"),
        "SCALPER":    Signal(name="SCALPER", kind="buy", score=0.52, tag="scalper"),
        "CONTRARIAN": Signal(name="CONTRARIAN", kind="sell", score=-0.41, tag="contrarian"),
        "TREND":      Signal(name="TREND", kind="buy", score=0.66, tag="trend"),
        "RESEARCHER": Signal(name="RESEARCHER", kind="buy", score=0.59, tag="researcher"),
        "PORTFOLIO":  Signal(name="PORTFOLIO", kind="buy", score=0.64, tag="portfolio"),
    }
    # ---- BEGIN YOUR CODE HERE ----
    # Return your own {name: Signal} dict, or extend the defaults:
    # default_votes["YOUR_AGENT"] = Signal(name="YOUR_AGENT", kind="buy", score=0.70, tag="your")
    # ---- END YOUR CODE HERE ----
    return default_votes


def MY_EXECUTE_FN(pair, direction, gate):
    """REPLACE with your own paper execution (size, stop, trail, re-gate).

    Default sample: trigger-only, single paper trade sized from the gate score.
    Returns a dict (paper fill) or None (stand down) when the gate is not met.
    """
    size = min(gate["combined_score"] * 0.5, 0.85)
    pnl_pct = min(abs(gate["combined_score"]) * 8.0, 60.0)
    if gate["qualified"]:
        return {"side": direction, "size": round(size, 4),
                "pnl_pct": round(pnl_pct, 2), "executed": True}
    return None


def main(command_line=None):
    import importlib.util, os, sys
    root = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    core_path = os.path.join(root, "paper_run_core.py")
    spec = importlib.util.spec_from_file_location("lyta_grok_desk_paper_core", core_path)
    core = importlib.util.module_from_spec(spec)
    sys.modules["lyta_grok_desk_paper_core"] = core
    spec.loader.exec_module(core)

    from lyta_grok_desk_paper_core import PaperDesk, PAPER_CAPITAL

    desk = PaperDesk(name="YourWay", capital=PAPER_CAPITAL)
    desk.vote_fn = MY_VOTE_FN
    desk.advice_fn = YOUR_STRATEGY_HERE
    desk.execute_fn = MY_EXECUTE_FN

    # Mirror paper_run.py's loop:  --minutes / --interval / verbose
    class _NS:
        minutes = 0.3
        interval = 1.0
        verbose = True
        market = {"symbol": "LOCAL#01", "trend": "bull", "change24h": 1.2,
                  "rug_risk": 0.0, "liquidity": 0.4, "score": 60}
    for tick_no in range(1, 18):
        result = desk.run_tick(_NS.market, narrative="option-c sample")
        if result and result.get("executed"):
            t = result.get("trade") or {}
            print("  [{}] PAPER side={} size={} pnl={} | consent {}/8 | score {:.3f}".format(
                tick_no,
                t.get("side"), t.get("size"), t.get("pnl_pct"),
                result["consent"], result["combined_score"]))
        else:
            print("  [{}] STAND DOWN: {}".format(
                tick_no, result.get("stand_down_reason") if result else "gate not met"))
        if tick_no % 3 == 0:
            print(f"  capital ${desk.equity:.2f} | stand-downs {desk.stand_downs}")
        import time; time.sleep(_NS.interval)

    print()
    print("=== OPTION C COMPLETE ===")
    print("  capital ${:.2f} | trades {} | stand-downs {}".format(
        desk.equity, len(desk.trades), desk.stand_downs))
    print("  advisory samples {}".format(desk.grok_committee_advice[-3:]))
    print("  last_signal {}".format(desk.signals[-1] if desk.signals else "n/a"))


if __name__ == "__main__":
    main()
