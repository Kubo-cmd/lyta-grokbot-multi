
#!/usr/bin/env python3
"""
LYTA Grok Desk - Multi-Version Combined Execution System (v1-v9)
===============================================================
VERSION STRATEGY: "Use all the v and make them separate and run them all in one"

This system:
1. Maintains separate parameter profiles for each bot version (v1-v9)
2. Runs all versions in parallel (one process per version)
3. Tracks each version's performance independently
4. Provides combined metrics for version comparison
5. Identifies the best performer for promotion

Architecture:
    +------------------+
    |  Config Loader   |  <- Loads v1-v9 parameter profiles
    +--------+---------+
             |
    +--------v---------+       +------------------+
    |  Version Runner  | ----> |  Wrapper 1 (v1)  |
    +------------------+       +------------------+
             |
    +--------v---------+       +------------------+
    |  Version Runner  | ----> |  Wrapper 2 (v2)  |
    +------------------+       +------------------+
             |
    +--------v---------+       +------------------+
    |  Version Runner  | ----> |  Wrapper 3 (v3)  |
    +------------------+       +------------------+
             |   ...           +------------------+
             |
    +--------v---------+       +------------------+
    |  Version Runner  | ----> |  Wrapper 9 (v9)  |
    +------------------+       +------------------+
             |
    +--------v---------+
    |  Results Aggregator |
    +-------------------+
             |
    +--------v---------+
    |  Version Report   |
    +-------------------+
"""

import os
import sys
import json
import time
import threading
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent))

# Inspect if we can import the sim
try:
    import paper_desk_simulator as pfs
    print("[INFO] paper_desk_simulator.py imported successfully")
except ImportError:
    print("ERROR: paper_desk_simulator.py not found in workspace")
    sys.exit(1)


@dataclass
class VersionProfile:
    """Container for a bot version's parameter profile."""
    version_id: str
    description: str
    config: Dict[str, Any]

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        return {
            'version_id': self.version_id,
            'description': self.description,
            'config': self.config
        }


@dataclass
class VersionOutcome:
    """Stores the outcome of running one bot version."""
    version_id: str
    description: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    buy_count: int = 0
    sell_count: int = 0
    realized_pnl: float = 0.0
    start_balance: float = 0.0
    end_balance: float = 0.0
    win_rate: float = 0.0
    avg_pnl_per_trade: float = 0.0
    max_drawdown: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    exit_reasons: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    running: bool = False

    @property
    def is_better_than_default(self) -> bool:
        return self.realized_pnl > 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version_id': self.version_id,
            'description': self.description,
            'trades': self.trades,
            'wins': self.wins,
            'losses': self.losses,
            'buy_count': self.buy_count,
            'sell_count': self.sell_count,
            'realized_pnl': self.realized_pnl,
            'start_balance': self.start_balance,
            'end_balance': self.end_balance,
            'win_rate': self.win_rate,
            'avg_pnl_per_trade': self.avg_pnl_per_trade,
            'max_drawdown': self.max_drawdown,
            'best_trade': self.best_trade,
            'worst_trade': self.worst_trade,
            'exit_reasons': self.exit_reasons,
            'is_better_than_default': self.is_better_than_default
        }


class VersionRunner(threading.Thread):
    """
    Runs a single bot version with its parameter profile.
    Each version runs as a separate process, isolated from others.
    """

    def __init__(self, version_id: str, profile: VersionProfile, rounds: int = 50):
        super().__init__()
        self.version_id = version_id
        self.profile = profile
        self.rounds = rounds
        self.outcome = VersionOutcome(
            version_id=version_id,
            description=profile.description
        )
        self.stop_event = threading.Event()
        self.running = False

    def run(self):
        """Execute the version-specific trading as a separate subprocess."""
        import tempfile
        import subprocess

        try:
            # Create a config file for this specific version
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                # Merge global config with version-specific overrides
                version_config = {
                    **self.profile.config,
                    'version_id': self.version_id,
                    'rounds': self.rounds
                }
                json.dump(version_config, f, indent=2)
                temp_config = f.name

            # Build command: run the simulator as a subprocess with version config
            cmd = [
                sys.executable, str(Path(__file__).parent / 'paper_desk_simulator.py'),
                '--test-mode',
                '--test-iterations', str(self.rounds),
                '--config', temp_config
            ]

            print(f"\n  [RUN] Version {self.version_id} (subprocess)")
            print(f"        Command: {' '.join(cmd)}")

            # Run the subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per version
            )

            # Parse the results from stdout
            stdout = result.stdout
            stderr = result.stderr

            # Extract key metrics from the output
            self._parse_output(stdout, stderr)

            print(f"  [DONE] Version {self.version_id}")
            print(f"         Result: {self.outcome.trades} trades, "
                  f"{self.outcome.wins}W/{self.outcome.losses}L, "
                  f"PnL={self.outcome.realized_pnl:+.4f}")

            # Clean up temp config
            os.unlink(temp_config)

        except subprocess.TimeoutExpired:
            print(f"  [ERROR] Version {self.version_id}: Timeout after 300s")
            self.outcome.error = "Timeout"
        except Exception as e:
            print(f"  [ERROR] Version {self.version_id}: {e}")
            self.outcome.error = str(e)

    def _parse_output(self, stdout: str, stderr: str):
        """Parse the simulator output for key metrics."""
        # Initialize defaults
        self.outcome.trades = 0
        self.outcome.wins = 0
        self.outcome.losses = 0
        self.outcome.realized_pnl = 0.0
        self.outcome.win_rate = 0.0
        self.outcome.buy_count = 0
        self.outcome.sell_count = 0

        # Look for common patterns in the output
        import re

        # Find trade counts
        trade_pattern = re.search(r'(\d+)\s+trade', stdout)
        if trade_pattern:
            self.outcome.trades = int(trade_pattern.group(1))

        # Find wins/losses
        win_pattern = re.search(r'(\d+)\s+win', stdout)
        loss_pattern = re.search(r'(\d+)\s+loss', stdout)
        if win_pattern:
            self.outcome.wins = int(win_pattern.group(1))
        if loss_pattern:
            self.outcome.losses = int(loss_pattern.group(1))

        # Find PnL
        pnl_pattern = re.search(r'PnL[:\s]*([-+]?\d+\.\d+)', stdout)
        if pnl_pattern:
            self.outcome.realized_pnl = float(pnl_pattern.group(1))

        # Find win rate
        wr_pattern = re.search(r'win\s+r?a?te[:\s]*([-\d.]+)%', stdout)
        if wr_pattern:
            self.outcome.win_rate = float(wr_pattern.group(1)) / 100

        # Find buys/sells
        buy_pattern = re.search(r'(\d+)\s+buy', stdout)
        sell_pattern = re.search(r'(\d+)\s+sell', stdout)
        if buy_pattern:
            self.outcome.buy_count = int(buy_pattern.group(1))
        if sell_pattern:
            self.outcome.sell_count = int(sell_pattern.group(1))
        if buy_pattern:
            self.outcome.buy_count = int(buy_pattern.group(1))
        if sell_pattern:
            self.outcome.sell_count = int(sell_pattern.group(1))

    def stop(self):
        self.stop_event.set()
        self.running = False


class MultiVersionRunner:
    """
    Manages all bot versions running simultaneously.
    - Runs all versions in parallel
    - Tracks each version's performance separately
    - Aggregates results for comparison
    - Provides a combined dashboard view
    """

    def __init__(self, versions: List[VersionProfile] = None):
        self.versions = versions or []
        self.runners: Dict[str, VersionRunner] = {}
        self.outcomes: Dict[str, VersionOutcome] = {}
        self.lock = threading.Lock()

    def register_version(self, version_id: str, profile: VersionProfile):
        """Register a bot version with its profile."""
        runner = VersionRunner(version_id, profile)
        self.runners[version_id] = runner
        self.outcomes[version_id] = runner.outcome

    def start_all(self):
        """Start all registered versions in parallel."""
        print(f"\n{'='*60}")
        print(f"STARTING MULTI-VERSION EXECUTION ({len(self.versions)} versions)")
        print(f"{'='*60}")

        for v_id, runner in self.runners.items():
            runner.start()

        # Wait for all to complete
        for v_id, runner in self.runners.items():
            runner.join()
            print(f"  [COMPLETE] Version {v_id} finished")

    def stop_all(self):
        """Stop all running versions."""
        print("\n[STOP] Stopping all versions...")
        for v_id, runner in self.runners.items():
            runner.stop()
        print("[DONE] All versions stopped")

    def get_combined_metrics(self) -> Dict[str, Any]:
        """Aggregate results across all versions."""
        total_trades = sum(o.trades for o in self.outcomes.values())
        total_wins = sum(o.wins for o in self.outcomes.values())
        total_losses = sum(o.losses for o in self.outcomes.values())
        total_pnl = sum(o.realized_pnl for o in self.outcomes.values())

        # Best version
        best = None
        best_pnl = float('-inf')
        for v_id, outcome in self.outcomes.items():
            if outcome.realized_pnl > best_pnl:
                best_pnl = outcome.realized_pnl
                best = outcome

        return {
            "total_versions": len(self.outcomes),
            "total_trades": total_trades,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "total_pnl": total_pnl,
            "overall_win_rate": total_wins / max(total_trades, 1),
            "avg_pnl_per_trade": total_pnl / max(total_trades, 1),
            "per_version": {
                v: {
                    "trades": o.trades,
                    "wins": o.wins,
                    "losses": o.losses,
                    "pnl": o.realized_pnl,
                    "win_rate": o.win_rate,
                    "end_balance": o.end_balance,
                    "buy_count": o.buy_count,
                    "sell_count": o.sell_count,
                    "is_better_than_default": o.is_better_than_default,
                    "exit_reasons": o.exit_reasons
                } for v, o in self.outcomes.items()
            },
            "best_version": best.to_dict() if best else None,
            "active_versions": list(self.runners.keys())
        }

    def save_results(self, filepath: Path):
        """Save all results to a JSON file."""
        stats = self.get_combined_metrics()
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"\n[RESULTS] Saved to {filepath}")

    def print_combined_report(self):
        """Print a formatted combined report."""
        stats = self.get_combined_metrics()

        print("\n" + "="*60)
        print("MULTI-VERSION COMPARISON REPORT")
        print("="*60)
        print(f"\nTotal: {stats['total_versions']} versions | "
              f"Trades: {stats['total_trades']} | "
              f"Win rate: {stats['overall_win_rate']:.1%} | "
              f"PnL: {stats['total_pnl']:+.4f} SOL")

        print("\nPer-Version Results:")
        print("-"*60)
        for v_id, v_data in stats['per_version'].items():
            print(f"  {v_id:5s}: {v_data['trades']:3d} trades | "
                  f"{v_data['wins']}W/{v_data['losses']}L | "
                  f"win_rate={v_data['win_rate']:.1%} | "
                  f"PnL={v_data['pnl']:+.4f} SOL | "
                  f"End={v_data['end_balance']:.2f}")

        print("\n" + "-"*60)
        best = stats['best_version']
        if best:
            print(f"BEST VERSION: {best['version_id']} ({best['description']})")
            print(f"  PnL: {best['pnl']:+.4f} SOL | "
                  f"Win rate: {best['win_rate']:.1%} | "
                  f"End balance: {best['end_balance']:.2f}")
            print(f"  Exits: {best['exit_reasons']}")

        print("="*60 + "\n")


def create_version_profiles(config_path: Path) -> List[VersionProfile]:
    """
    Create VersionProfile objects from the bot_versions_config.json file.
    """
    with open(config_path) as f:
        config = json.load(f)

    profiles = []
    for v_id, v_config in config.get('version_profiles', {}).items():
        profile = VersionProfile(
            version_id=v_id,
            description=v_config.get('description', f'Version {v_id}'),
            config=v_config
        )
        profiles.append(profile)

    return profiles


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Version Bot Runner - Run all bot versions in parallel"
    )
    parser.add_argument(
        "--versions",
        type=str,
        default=None,
        help="Specific versions to run (v1,v2,v3) - default: all"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=50,
        help="Rounds per version (default: 50)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="bot_versions_config.json",
        help="Path to config file (default: bot_versions_config.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="multi_version_results.json",
        help="Output results file (default: multi_version_results.json)"
    )
    parser.add_argument(
        "--stop-all",
        action="store_true",
        help="Stop all running versions and exit"
    )
    args = parser.parse_args()

    workspace = Path(__file__).parent
    config_path = workspace / args.config

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    # Create version profiles
    profiles = create_version_profiles(config_path)
    print(f"Loaded {len(profiles)} version profiles: "
          f"{[p.version_id for p in profiles]}")

    # Filter by requested versions
    if args.versions:
        requested = [v.strip() for v in args.versions.split(',')]
        profiles = [p for p in profiles if p.version_id in requested]
        print(f"Running versions: {[p.version_id for p in profiles]}")

    # Create and configure runner
    runner = MultiVersionRunner(profiles)

    # Start all versions
    runner.start_all()

    # Generate combined report
    runner.print_combined_report()

    # Save results
    output_path = workspace / args.output
    runner.save_results(output_path)

    # Determine best version for promotion
    stats = runner.get_combined_metrics()
    best = stats['best_version']
    if best:
        print(f"\n[PROMOTION] Recommend promoting {best['version_id']} "
              f"based on PnL: {best['pnl']:+.4f} SOL")

    return stats


if __name__ == "__main__":
    main()
