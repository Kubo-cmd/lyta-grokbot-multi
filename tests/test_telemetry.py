#!/usr/bin/env python3
"""Unit checks for tools/telemetry.py and tools/make_eval_dataset.py.

Zero-burn: no network, no keys, no live orders. Run:
    python3 tests/test_telemetry.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import make_eval_dataset as ed  # noqa: E402
import telemetry as te  # noqa: E402


def _event(event, **payload):
    return {"ts": "2026-11-15T10:00:00.000000000+00:00", "run_id": "r-demo", "level": "INFO",
            "event": event, "payload": payload}


class TestTelemetryBase(unittest.TestCase):
    """Shared setup: intercept the telemetry file writes into a temp dir."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_root = te.REPO_ROOT
        te.REPO_ROOT = Path(self.tmp.name)
        self.out_dir = Path(self.tmp.name) / "eval"

    def tearDown(self):
        te.REPO_ROOT = self.old_root


class TestTelemetry(TestTelemetryBase):
    def test_run_cycle(self):
        run_id = te.init_run("test-run")
        lines = Path(self.tmp.name) / "telemetry" / f"{run_id}.jsonl"
        self.assertTrue(lines.is_file())
        te.finish_run()
        te.finish_run()  # idempotent
        text = lines.read_text(encoding="utf-8")
        self.assertIn('{"event": "run_start"', text)
        self.assertIn('{"event": "run_end"', text)

        def test_record_and_convenience(self):
            rid = te.init_run("demo")
            te.record("INFO", "custom", x=1, y="two")
            te.decision("GOBLIN/SOL", latency_s=0.0001, cost_tokens=0, pnl_pct=0.5, verdict="compounding",
                        decision="BUY-SIG", consent=8, combined_score=0.5, qualified=True, paper_size=0.05)
            te.stand_down("GOBLIN/SOL", latency_s=0.2, reason="too slow", consent=5)
            te.ledger_snapshot(decisions=1, avg_latency_s=0.0001, avg_cost_tokens=0.0, avg_pnl_pct=0.5,
                               per_layer={"runtime": 0.0001, "infrastructure": 0.0, "tooling": 0.0})
            te.paper_state(capital=6.0, positions=1, paper_size=0.05)
            te.error(ValueError("boom"))
            text = Path(self.tmp.name, "telemetry", rid + ".jsonl").read_text(encoding="utf-8")
            self.assertIn('"event": "decision"', text)
            self.assertIn('"verdict": "compounding"', text)
            self.assertIn('"verdict": "stand-down"', text)
            self.assertIn('"event": "error"', text)
            self.assertIn('"exc_type": "ValueError"', text)
            te.finish_run(rid)

        def test_trace_context(self):
            rid = te.init_run("trace-test")
            with te.trace("my-call"):
                pass
            with te.trace("failing-call"):
                raise RuntimeError("ouch")
            text = Path(self.tmp.name, "telemetry", rid + ".jsonl").read_text(encoding="utf-8")
            self.assertIn('"state": "start"', text)
            self.assertIn('"state": "end"', text)
            self.assertIn('"error": true', text)
            te.finish_run(rid)

        def test_event_shape(self):
            rid = te.init_run("shape")
            te.record("WARN", "stand_down", pair="A/B", reason="thin")
            text = Path(self.tmp.name, "telemetry", rid + ".jsonl").read_text(encoding="utf-8")
            obj = json.loads(text.strip().splitlines()[-1])
            self.assertEqual(obj["level"], "WARN")
            self.assertEqual(obj["run_id"], rid)
            self.assertEqual(obj["event"], "stand_down")
            te.finish_run(rid)


class TestMakeEvalDataset(TestTelemetryBase):
    """Runs the eval dataset builder against tiny synthetic telemetry files."""

    def _write_telemetry(self, events, name="demo.jsonl"):
        p = Path(self.tmp.name) / name
        p.write_text("\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n", encoding="utf-8")
        return p

    def _event(self, event, **payload):
        return _event(event, **payload)

    def build(self, input_path, window=2, output_dir=None):
        return ed.build_dataset([input_path], output_dir or self.out_dir, window, seed=42)

    def test_build_one_run(self):
        ev = [
            self._event("decision", pair="GOBLIN/SOL", paper_size=0.05, latency_s=0.001,
                        cost_tokens=0, pnl_pct=0.5, verdict="compounding", latency_ok=True,
                        cost_ok=True, pnl_ok=True, decision="BUY-SIG", consent=8,
                        combined_score=0.5, qualified=True),
            self._event("decision", pair="GOBLIN/SOL", paper_size=0.05, latency_s=0.002,
                        cost_tokens=0, pnl_pct=0.1, verdict="compounding", latency_ok=True,
                        cost_ok=True, pnl_ok=True, decision="BUY-SIG", consent=8,
                        combined_score=0.5, qualified=True),
            self._event("decision", pair="GOBLIN/SOL", paper_size=0.05, latency_s=0.003,
                        cost_tokens=0, pnl_pct=-0.1, verdict="stand-down", latency_ok=True,
                        cost_ok=True, pnl_ok=False, decision="STAND_DOWN", consent=None,
                        combined_score=None, qualified=False),
        ]
        src = self._write_telemetry(ev)
        out = self.build(src, window=2)
        self.assertEqual(out["total_rows"], 1)
        rows = json.loads(Path(out["output"]).read_text(encoding="utf-8"))
        self.assertEqual(rows[0]["features"]["verdict"], "compounding")
        self.assertEqual(rows[0]["features"]["latency_s"], round((0.001 + 0.002) / 2, 6))
        self.assertEqual(rows[0]["target"]["success"], True)

    def test_window_steps_and_targets(self):
        # 5 distinct decisions (unique latency per step) -> sliding windows of
        # 3 over 5 steps = 3 eval rows; none contains a stand-down verdict.
        ev = [self._event("decision", pair="A/B", paper_size=0.05, latency_s=0.001 * (i + 1),
                           cost_tokens=0, pnl_pct=None, verdict="compounding",
                           decision="PASS")
              for i in range(5)]
        src = self._write_telemetry(ev)
        out_path = self.build(src, window=3)["output"]
        rows = json.loads(Path(out_path).read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 3)  # 5 - 3 + 1
        self.assertFalse(rows[0]["target"]["closed_trade"])  # pnl None -> not closed
        self.assertTrue(rows[1]["target"]["success"])

    def test_window_too_large(self):
        src = self._write_telemetry([self._event("decision")])
        with self.assertRaises(ValueError):
            ed.build_dataset([src], self.out_dir, window=0, seed=1)

    def test_determinism(self):
        ev = [self._event("decision", pair="A/B", paper_size=0.05, latency_s=0.001,
                           cost_tokens=0, pnl_pct=0.5, verdict="compounding", decision="PASS")]
        src = self._write_telemetry(ev)
        a = self.build(src, window=1)
        b = self.build(src, window=1)
        self.assertEqual(a["hash"], b["hash"])
        self.assertEqual(
            Path(a["output"]).read_bytes(), Path(b["output"]).read_bytes())

    def test_malformed_lines_skipped(self):
        src = self._write_telemetry([{"not": "json"}, self._event("decision",
                                          pair="X", paper_size=0.05)])
        out = self.build(src, window=1)
        self.assertEqual(out["total_decisions"], 1)

    def test_missing_input(self):
        out = ed.build_dataset([], self.out_dir, window=1, seed=1)
        self.assertEqual(out["total_decisions"], 0)
        self.assertEqual(out["total_rows"], 0)
        self.assertTrue((self.out_dir / "dataset.jsonl").exists())

    def test_non_decision_events_ignored(self):
        ev = [self._event("stand_down", reason="slow"),
              self._event("decision", pair="X", paper_size=0.05)]
        src = self._write_telemetry(ev)
        out = self.build(src, window=1)
        self.assertEqual(out["total_decisions"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
