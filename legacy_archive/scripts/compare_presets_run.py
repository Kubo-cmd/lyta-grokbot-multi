
import sys, time, json
sys.path.insert(0, "/Users/test/projects/lyta-grokbot-multi")
import paper_desk_simulator as pds

# Presets from STRATEGY_PRESETS
presets = {
    "scalper": {
        "name": "Scalper (Trenches v4 precision)",
        "PO_MIN_HOLDERS": 45, "PO_TOP10_MAX": 25, "PO_LIQUIDITY_FLOOR": 50000.0,
        "PO_MIN_WALLETS": 20, "PO_MIN_BUYS": 5, "PO_STOP_LOSS": 0.10,
        "PO_MAX_POS_PCT": 0.20, "PO_PNL_LIMITS": True, "PO_STAGGERED_EXITS": True,
        "PO_EXIT_1": [2.0, 0.50], "PO_EXIT_2": [3.0, 0.50],
        "PO_TRAIL": 2.0, "PO_TRAIL_DD": 0.10,
        "PO_SLIPPAGE_ENTRY": 0.10, "PO_SLIPPAGE_EXIT": 0.03,
        "PO_DYNAMIC_SLIPPAGE": True, "PO_SLIPPAGE_BACKTEST_ADJ": 0.50,
        "PO_BNavy": 0.05, "PO_STALE": 60, "PO_DEAD": 120,
        "PO_HOLD_GRAD": False, "PO_WORKING": True,
    },
    "fusion": {
        "name": "Fusion (Circuit + Trenches hybrid)",
        "PO_MIN_HOLDERS": 40, "PO_TOP10_MAX": 25, "PO_LIQUIDITY_FLOOR": 60000.0,
        "PO_MIN_WALLETS": 15, "PO_MIN_BUYS": 4, "PO_STOP_LOSS": 0.10,
        "PO_MAX_POS_PCT": 0.25, "PO_PNL_LIMITS": True, "PO_STAGGERED_EXITS": True,
        "PO_EXIT_1": [2.0, 0.50], "PO_EXIT_2": [3.0, 1.00],
        "PO_TRAIL": 2.5, "PO_TRAIL_DD": 0.15,
        "PO_SLIPPAGE_ENTRY": 0.15, "PO_SLIPPAGE_EXIT": 0.05,
        "PO_DYNAMIC_SLIPPAGE": True, "PO_SLIPPAGE_BACKTEST_ADJ": 0.50,
        "PO_BNavy": 0.05, "PO_STALE": 120, "PO_DEAD": 300,
        "PO_HOLD_GRAD": True, "PO_WORKING": True,
    },
    "meanreversion": {
        "name": "MeanReversion (Circuit PAPR delta-neutral swing)",
        "PO_MIN_HOLDERS": 30, "PO_TOP10_MAX": 30, "PO_LIQUIDITY_FLOOR": 30000.0,
        "PO_MIN_WALLETS": 10, "PO_MIN_BUYS": 3, "PO_STOP_LOSS": 0.20,
        "PO_MAX_POS_PCT": 0.40, "PO_PNL_LIMITS": True, "PO_STAGGERED_EXITS": False,
        "PO_EXIT_1": [2.0, 0.50], "PO_EXIT_2": [3.0, 1.00],
        "PO_TRAIL": 3.0, "PO_TRAIL_DD": 0.25,
        "PO_SLIPPAGE_ENTRY": 0.15, "PO_SLIPPAGE_EXIT": 0.05,
        "PO_DYNAMIC_SLIPPAGE": False, "PO_SLIPPAGE_BACKTEST_ADJ": 0.0,
        "PO_BNavy": 0.05, "PO_STALE": 300, "PO_DEAD": 600,
        "PO_HOLD_GRAD": True, "PO_WORKING": True,
    },
}

# Apply paper v9 config as base, then preset overrides
base_config = {
    "PO_BNavy": 0.05, "PO_ENTRY_MIN": 8, "PO_ENTRY_MAX": 70,
    "PO_MIN_WALLETS": 15, "PO_MIN_BUYS": 3, "PO_MIN_HOLDERS": 30,
    "PO_MAX_POOL_FEE": 0.04, "PO_STALE": 120, "PO_DEAD": 300,
    "PO_HOLD_GRAD": True, "PO_SLIPPAGE_ENTRY": 0.15, "PO_SLIPPAGE_EXIT": 0.05,
    "_ab_test_name": "v9_base",
    "_ab_test_config": {},
}

results = {}
print("=" * 70)
print("BEST-ROUTE A/B COMPARISON - paper_desk_simulator.py presets")
print(f"Paper capital: $501 simulated | Time: 1h window | Exit: ladder 50%@2x/rest@3x, fallback -8%")
print("=" * 70)

for preset_name, preset_params in presets.items():
    print(f"\n{'='*50}")
    print(f"RUNNING: {preset_name} — {preset_params.get('name', preset_name)}")
    print(f"{'='*50}")
    
    # Start with base config (v9 paper config)
    c = dict(base_config)
    c.update(preset_params)
    
    original_config = pds.CONFIG
    pds.CONFIG = c
    
    # Limit to 15 positions max
    import importlib
    original_run = pds.run_paper_desk
    position_count = [0]
    sell_legs_count = [0]
    realized_pnl = [0.0]
    market_flips = [0]
    buy_signals = [0]
    
    def limited_run(collateral=501.0, asset="GOBLIN", verbose=False, max_positions=15):
        c_local = dict(pds.CONFIG)
        c_local["_ab_test_name"] = preset_name
        c_local["_ab_test_config"] = preset_params
        PO_BNavy = c_local["PO_BNavy"]
        PO_STALE = c_local["PO_STALE"]
        PO_DEAD = c_local["PO_DEAD"]
        PO_STAGGERED_EXITS = c_local.get("PO_STAGGERED_EXITS", False)
        PO_EXIT_1 = c_local.get("PO_EXIT_1", [2.0, 0.50])
        PO_EXIT_2 = c_local.get("PO_EXIT_2", [3.0, 1.00])
        PO_TRAIL = c_local.get("PO_TRAIL", 2.5)
        PO_TRAIL_DD = c_local.get("PO_TRAIL_DD", 0.15)
        PO_STOP_LOSS = c_local.get("PO_STOP_LOSS", 0.10)
        PO_SLIPPAGE_ENTRY = c_local.get("PO_SLIPPAGE_ENTRY", 0.15)
        PO_SLIPPAGE_EXIT = c_local.get("PO_SLIPPAGE_EXIT", 0.05)
        PO_PROTOCOL_FEE = c_local.get("PO_PROTOCOL_FEE", 0.01)
        PO_FLAT_FEE_PER_LEG = c_local.get("PO_FLAT_FEE_PER_LEG", 0.001015)
        PO_LIQUIDITY_FLOOR = c_local.get("PO_LIQUIDITY_FLOOR", 0)
        PO_MIN_WALLETS = c_local.get("PO_MIN_WALLETS", 15)
        PO_MIN_BUYS = c_local.get("PO_MIN_BUYS", 3)
        PO_MIN_HOLDERS = c_local.get("PO_MIN_HOLDERS", 30)
        PO_ENTRY_MIN = c_local.get("PO_ENTRY_MIN", 8)
        PO_ENTRY_MAX = c_local.get("PO_ENTRY_MAX", 70)
        PO_MINT_AUTH_REQUIRED = c_local.get("PO_MINT_AUTH_REQUIRED", True)
        PO_RISKY_EXT_BLOCK = c_local.get("PO_RISKY_EXT_BLOCK", True)
        PO_24_7 = c_local.get("PO_24_7", True)
        PO_PNL_LIMITS = c_local.get("PO_PNL_LIMITS", False)
        total_cost = PO_BNavy + PO_BNavy * PO_PROTOCOL_FEE + PO_FLAT_FEE_PER_LEG
        
        pos = None
        entry_price = None
        last_update = time.time()
        hold_start = None
        position_count_local = [0]
        sell_legs_local = [0]
        realized_pnl_local = [0.0]
        flips = [0]
        buys = [0]
        
        while position_count_local[0] < max_positions:
            market = pds.make_realistic_market(asset, 41.20)
            flips[0] += 1
            
            # Paper observer decision via signal
            signal = None
            if hasattr(pds, 'paper_observer_enter'):
                signal = pds.paper_observer_enter(market)
            
            if signal is not None and pos is None and position_count_local[0] < max_positions:
                entry_price = market.price
                pos = {
                    "entry_price": entry_price,
                    "size_sol": signal.get("size_sol", PO_BNavy),
                    "asset": market.asset,
                    "peak_price": entry_price,
                    "opened_at": time.time(),
                    "stale_at": time.time() + PO_STALE,
                    "dead_at": time.time() + PO_DEAD,
                }
                buys[0] += 1
                if verbose:
                    print(f"[BUY] {market.asset} | ${entry_price:.4f} | progress {signal.get('progress', 0):.1f}% | liq ${signal.get('liquidity', 0):.0f}")
            
            if pos is not None:
                new_pos, exit_reason, exit_price, frac = pds.check_exits(
                    pos, market, time.time(), last_update
                )
                if exit_reason is not None:
                    sell_legs_local[0] += 1
                    gross_sale_value = PO_BNavy * (exit_price / pos["entry_price"]) * frac
                    if PO_STAGGERED_EXITS:
                        gross_sale_value = gross_sale_value * (1 - PO_SLIPPAGE_ENTRY)
                        exit_slippage = gross_sale_value * PO_SLIPPAGE_EXIT
                    else:
                        exit_slippage = 0.0
                    leg_protocol_fee = gross_sale_value * PO_PROTOCOL_FEE
                    leg_flat_fee = PO_FLAT_FEE_PER_LEG
                    net_proceeds = gross_sale_value - exit_slippage - leg_protocol_fee - leg_flat_fee
                    entry_cost_fraction = total_cost * frac
                    pnl_sol = net_proceeds - entry_cost_fraction
                    pnl_pct = (net_proceeds / entry_cost_fraction - 1) * 100 if entry_cost_fraction > 0 else 0.0
                    realized_pnl_local[0] += pnl_sol
                    position_count_local[0] += 1
                    if verbose:
                        print(f"[EXIT #{position_count_local[0]}] {exit_reason} | PnL {pnl_sol:+.4f} ({pnl_pct:+.1f}%) | entry ${pos['entry_price']:.4f} exit ${exit_price:.4f}")
                    pos = None
                    entry_price = None
                    last_update = time.time()
            
            if verbose:
                print(f"  running: {position_count_local[0]} completed, {buys[0]} buys, realized_pnl={realized_pnl_local[0]:.4f}")
        
        result = {
            "preset": preset_name,
            "positions_completed": position_count_local[0],
            "sell_legs": sell_legs_local[0],
            "realized_pnl_sol": round(realized_pnl_local[0], 4),
            "avg_pnl_per_position": round(realized_pnl_local[0] / max(position_count_local[0], 1), 4),
            "buys": buys[0],
            "market_flips": flips[0],
            "config_name": c_local.get("_ab_test_name", "unknown"),
        }
        return result
    
    try:
        result = limited_run(verbose=False, max_positions=15)
        results[preset_name] = result
        with open(f"/Users/test/projects/lyta-grokbot-multi/scratch_{preset_name}_result.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nRESULT: {json.dumps(result, indent=2)}")
    finally:
        pds.CONFIG = original_config
        pds.run_paper_desk = original_run

print("\n\n" + "=" * 70)
print("COMPARISON SUMMARY")
print("=" * 70)
print(f"{'Preset':20s} | {'Completed':>10s} | {'SellLegs':>8s} | {'PnL(SOL)':>10s} | {'Avg/Pos':>10s}")
for name, r in results.items():
    print(f"{name:20s} | {r['positions_completed']:>10d} | {r['sell_legs']:>8d} | {r['realized_pnl_sol']:>10.4f} | {r['avg_pnl_per_position']:>10.4f}")

with open("/Users/test/projects/lyta-grokbot-multi/best_route_comparison.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nFull results saved to best_route_comparison.json")
