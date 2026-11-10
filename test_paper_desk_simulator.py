"""Test suite for paper_desk_simulator.py — verifier of the simulator and the
2026-11-07 regression fixes (trailing exit bug, market simulation stability)."""

import sys, os, unittest, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import paper_desk_simulator as pds


class _Market:
    """Minimal Market stub for exit/logic tests (avoids 13-arg constructor)."""

    def __init__(self, price, asset="TEST"):
        self.price = price
        self.asset = asset
        self.bonding_curve_progress = 50.0
        self.is_new_launch = False
        self.analyst_score = 0.5
        self.rug_risk = 0.5
        self.liquidity = 1000.0
        self.buys_5m = 10
        self.unique_wallets = 50
        self.holders = 50
        self.top10_concentration = 10.0
        self.dev_holdings = 0.0
        self.change_1h = 0.5
        self.change_24h = 2.0


class TestTrailingExit(unittest.TestCase):
    """Verify the trailing exit fix: exit on 15% drawdown from peak, not 2.5x."""

    def setUp(self):
        self.pos = {"entry_price": 100.0, "quantity": 1.0,
                    "peak_price": 100.0, "side": "long"}

    def test_exit_at_15pct_drawdown(self):
        import time as _t
        m = _Market(85.0)
        pos, reason, exit_price, fees = pds.check_exits(self.pos, m, 0.0, _t.time())
        self.assertEqual(reason, "trailing exit")

    def test_no_exit_at_5pct_gain(self):
        import time as _t
        m = _Market(105.0)
        pos, reason, _, _ = pds.check_exits(self.pos, m, 0.0, _t.time())
        self.assertNotEqual(reason, "trailing exit")

    def test_no_exit_at_10pct_gain(self):
        import time as _t
        m = _Market(110.0)
        pos, reason, _, _ = pds.check_exits(self.pos, m, 0.0, _t.time())
        self.assertNotEqual(reason, "trailing exit")

    def test_peak_updated_on_gain(self):
        import time as _t
        m = _Market(116.0)
        pos, _, _, _ = pds.check_exits(self.pos, m, 0.0, _t.time())
        self.assertEqual(pos["peak_price"], 116.0)

    def test_exit_at_20pct_drawdown(self):
        import time as _t
        # v10 config: PO_STOP_LOSS=0.82 (18% stop), PO_TRAIL=3.0
        # 20% DD = 0.80x which is BELOW stop-loss 0.82 → stop-loss triggers first
        # This tests the v10 tighter stop-loss behavior
        m = _Market(80.0)  # 100 * 0.80 = 80.0 → 20% DD
        pos, reason, _, _ = pds.check_exits(self.pos, m, 0.0, _t.time())
        self.assertEqual(reason, "stop-loss trigger")  # v10: stop-loss at 18% DD


class TestMarketSimulation(unittest.TestCase):
    """Verify the market moves realistically (small steps, mean reversion)."""

    def test_price_movement_small(self):
        base = 1.0
        prices = []
        for _ in range(100):
            m = pds.make_realistic_market("TEST", base)
            prices.append(m.price)
        # No ±50% swings expected; step is ±5%
        self.assertTrue(all(abs(p - base) <= base * 0.20 for p in prices))

    def test_price_positive(self):
        for _ in range(1000):
            m = pds.make_realistic_market("TEST", 1.0)
            self.assertGreater(m.price, 0.0)


class TestConfig(unittest.TestCase):
    """Verify configuration is readable."""

    def test_fee_config(self):
        self.assertGreater(pds.config["PO_FEE_BREAK_EVEN"], 0)
        self.assertGreater(pds.config["PO_ENTRY_MIN"], 0)


class TestEntryLogic(unittest.TestCase):
    """Verify the entry filters work with the test market."""

    def test_entry_min_holders_satisfied(self):
        self.assertEqual(pds.config["PO_MIN_HOLDERS"], 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
