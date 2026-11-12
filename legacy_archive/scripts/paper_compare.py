
import sys
sys.path.insert(0, "/Users/test/projects/lyta-grokbot-multi")
import paper_desk_simulator as pds

# Modify CONFIG with each preset
presets = {
    "scalper": {
        "PO_STOP_LOSS": 0.10, "PO_TRAIL": 2.0, "PO_TRAIL_DD": 0.10,
        "PO_SLIPPAGE_ENTRY": 0.10, "PO_SLIPPAGE_EXIT": 0.03
    },
    "fusion": {
        "PO_STOP_LOSS": 0.10, "PO_TRAIL": 2.5, "PO_TRAIL_DD": 0.15,
        "PO_SLIPPAGE_ENTRY": 0.15, "PO_SLIPPAGE_EXIT": 0.05
    },
    "meanreversion": {
        "PO_STOP_LOSS": 0.20, "PO_TRAIL": 3.0, "PO_TRAIL_DD": 0.25,
        "PO_SLIPPAGE_ENTRY": 0.15, "PO_SLIPPAGE_EXIT": 0.05
    }
}

for preset_name, preset_params in presets.items():
    # Apply preset to config
    c = dict(pds.CONFIG)
    c.update(preset_params)
    c["PO_BNavy"] = 0.05
    c["PO_ENTRY_MIN"] = 8
    c["PO_ENTRY_MAX"] = 70
    c["PO_MIN_WALLETS"] = 15
    c["PO_MIN_BUYS"] = 3
    c["PO_MIN_HOLDERS"] = 30
    c["PO_MAX_POOL_FEE"] = 0.04
    c["PO_STALE"] = 120
    c["PO_DEAD"] = 300
    c["PO_HOLD_GRAD"] = True
    c["PO_MINT_AUTH_REQUIRED"] = True
    c["PO_RISKY_EXT_BLOCK"] = True
    c["PO_24_7"] = True
    c["PO_PNL_LIMITS"] = False
    c["_ab_test_name"] = preset_name
    pds.CONFIG = c
    
    # Run a limited number of iterations
    import threading
    results = {}
    def run_with_limits():
        pds.run_paper_desk(collateral=501.0, asset="GOBLIN", verbose=False)
    t = threading.Thread(target=run_with_limits, daemon=True)
    t.start()
    t.join(timeout=60)
    print(f"=== Preset: {preset_name} done ===")
