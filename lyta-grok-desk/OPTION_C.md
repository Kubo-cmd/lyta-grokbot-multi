# OPTION C — Your Own Way

**Repo:** `lyta-grokbot-multi`  
**Status:** `1405575` — option-C scaffold committed (template + runner)  
**Date:** 2026-11-13 (PST, America/Los_Angeles)  
**Mode:** Paper-only. No real trades. No real capital. No fabricated scores.

This doc explains **how your custom strategy (option C) plugs into the shared
engine** and how to make it runnable, testable, and open-source-friendly for
reviewers.

---

## 1. What option C is

Option C is your own strategy running on the **same shared paper-only engine**
that OpenBot (A) and GrokBot (B) use. You do **not** rebuild the gate,
the paper-only capital guard, or the stand-down logging. You only replace the
advice/vote/execute columns:

| Pluggable point | Default (A/B) | Your option C |
|---|---|---|
| `advice_fn(pair, votes) -> float` | spot/narrative heuristics (A) or Grok committee plug (B) | your own scoring |
| `vote_fn(pair) -> {name: Signal}` | 12 OpenBot agents | your own or the default 12 |
| `execute_fn(pair, direction, gate) -> dict` | min(capital\*0.01, 5.0) paper fill | your paper buy/exit |

Because A, B, and C share the identical engine, the comparison is apples-to-apples:
any difference in outcome comes **only** from your custom strategy.

---

## 2. How to run it (ready-to-paste)

```bash
cd /Users/test/projects/lyta-grokbot-multi

# single custom run
python3 lyta-grok-desk/option_c_template.py --minutes 0.3 --interval 1

# compare all three on identical paper data
python3 paper_run.py            # option A: OpenBot 12-agent
python3 grokbot_multi.py        # option B: GrokBot 11-agent committee
python3 lyta-grok-desk/option_c_template.py --minutes 0.3 --interval 1   # option C
```

Each run writes a machine-readable paper record:

- `paper_desk_openbot_record.json` — option A
- `paper_trades_autonomous_grok.csv` + `equity_curve_autonomous_grok.csv` — option B
- `paper_desk_<yourdesk>_record.json` (from `run_session` end) — option C

---

## 3. The plug-in template file

`lyta-grok-desk/option_c_template.py` is your drop-in scaffold. It contains
three clearly-marked hooks:

1. **`YOUR_STRATEGY_HERE(pair, votes, desk)`** — your scoring function.
2. **`MY_VOTE_FN(pair)`** — your vote list (replaces the 12 OpenBot agents).
3. **`MY_EXECUTE_FN(pair, direction, gate)`** — your paper execution hook.

Paste your logic into those three bodies. Nothing else needs changing: the
engine, gate, paper guard, stand-down logging, and record export all stay
shared verbatim.

---

## 4. How to make your way the best (honest methodology)

1. **Same engine, same data, same window.** Run all three options on identical
   paper market data for a fixed window (3–10 min). Any difference is your
   custom strategy alone.
2. **Record the right metrics.** First paper trade, max paper equity, final
   paper capital, trades executed, stand-downs per tick, advisory samples.
3. **Define "best" honestly.** Best = the option that earns the first real
   paper trade **and** keeps the highest paper equity without violating the
   paper-only guard.
4. **Keep numbers honest.** Every number is either (a) live-DEX spot data or
   (b) a documented paper construction. No fabricated scores, no real orders.

---

## 5. Open-source review checklist

- [ ] `paper_run_core.py` — shared engine, gate + paper guard + logging
- [ ] `paper_run.py` — option A runner (OpenBot 12-agent)
- [ ] `grokbot_multi.py` — option B runner (GrokBot 11-agent committee)
- [ ] `option_c_template.py` — option C runner (your strategy plug-in)
- [ ] `PROMPTS.md` — ready-to-paste templates (Template C = option C)
- [ ] `lyta-grok-desk/three_options_comparison.json` — the A/B/C decision table
- [ ] `lyta-grok-desk/paper_run_core.py` — importable by path (hyphen dir is not
      a Python import name; both desks load it via `importlib`)

Run `python3 lyta-grok-desk/option_c_template.py --minutes 0.3 --interval 1`
and it should exit 0, print per-tick paper stand-downs, and write the paper
record — no key, no wallet, no real capital.
