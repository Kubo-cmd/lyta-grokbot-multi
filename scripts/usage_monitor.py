#!/usr/bin/env python3
"""
LYTA GROKBOT USAGE MONITOR
~~~~~~~~~~~~~~~~~~~~~~~~~
Tracks weekly Grok bot usage and alerts when it approaches the 100% cap.

The Grok bot (xAI agentic AI) weekly usage resets Friday at 2:05 AM ET.
Recent throttling (Nov 1, 2026) has caused users to hit 100% unexpectedly
fast. This monitor logs usage % at the start and end of each run, warns
when usage exceeds thresholds, and recommends chunking when close to the cap.

USAGE:
    from usage_monitor import UsageMonitor, check_grok_usage

    monitor = UsageMonitor()
    monitor.log_run_start()
    # ... do your work ...
    monitor.log_run_end()
    monitor.check_thresholds()

CONFIG:
    GROK_USAGE_URL - Endpoint or API to check Grok bot usage (optional)
    USAGE_MONITOR_COOLDOWN - Minimum seconds between threshold checks

NOTES:
    This is a monitoring/simulation utility. Grok bot usage is typically
    tracked via the Grok web UI or API. Adapt check_grok_usage() to your
    actual usage tracking method.
"""

import json
import os
import time
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# Load from openbot.grok or grokbot_multi config if present
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG = {
    "GROK_USAGE_URL": None,  # e.g. "https://grok.com/api/usage" or local file path
    "USAGE_MONITOR_COOLDOWN": 300,  # seconds before re-check
    "THRESHOLD_WARN": 0.90,  # warn at 90% usage
    "THRESHOLD_CRITICAL": 0.95,  # critical at 95% usage
    "CHUNK_THRESHOLD": 0.80,  # recommend chunking below 80%
    "LOCAL_FALLBACK": "paper_desk_simulator",  # default local fallback
    "LOG_FILE": os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "usage_log.jsonl"
    ),
}

# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class UsageRecord:
    timestamp: str
    run_id: str
    start_usage_pct: float
    end_usage_pct: float
    duration_seconds: float
    action: str  # "start" | "end" | "check"
    alert: Optional[str] = None
    notes: str = ""

@dataclass
class UsageMonitor:
    run_id: str = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    start_usage: Optional[float] = None
    end_usage: Optional[float] = None
    log_path: str = None

    def __post_init__(self):
        self.run_id = self.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = CONFIG["LOG_FILE"]
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Create the log file with header if it doesn't exist."""
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                f.write("# Usage log for LYTA GrokBot paper trading desk\n")
                f.write("# Format: timestamp, run_id, action, start_pct, end_pct, duration, alert, notes\n")

    def _append_log(self, record: UsageRecord):
        with open(self.log_path, "a") as f:
            f.write(f"{record.timestamp},{record.run_id},{record.action},"
                    f"{record.start_usage_pct},{record.end_usage_pct},"
                    f"{record.duration_seconds},{record.alert or ''},{record.notes}\n")

    # ── Public API ─────────────────────────────────────────────────────────

    def log_run_start(self):
        """Called at the start of each Grok bot run."""
        self.start_time = datetime.now(timezone.utc)
        self.start_usage = self._get_current_usage()
        record = UsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=self.run_id,
            action="start",
            start_usage_pct=self.start_usage,
            end_usage_pct=0.0,
            duration_seconds=0,
            notes="Run started"
        )
        self._append_log(record)
        return self.start_usage

    def log_run_end(self):
        """Called at the end of each Grok bot run."""
        self.end_time = datetime.now(timezone.utc)
        self.end_usage = self._get_current_usage()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        record = UsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=self.run_id,
            action="end",
            start_usage_pct=self.start_usage or 0,
            end_usage_pct=self.end_usage or 0,
            duration_seconds=duration,
            notes="Run ended"
        )
        self._append_log(record)
        return self.end_usage

    def check_thresholds(self) -> dict:
        """
        Check current usage against thresholds and return alert info.
        Returns dict with alert level, message, and recommended action.
        """
        current = self._get_current_usage()
        current_time = datetime.now(timezone.utc).isoformat()

        if current >= CONFIG["THRESHOLD_CRITICAL"]:
            alert = "CRITICAL"
            msg = f"Grok bot usage at {current*100:.1f}% — CRITICAL. Quota nearly exhausted."
            action = "PAUSE remote agent; fallback to local simulator"
        elif current >= CONFIG["THRESHOLD_WARN"]:
            alert = "WARNING"
            msg = f"Grok bot usage at {current*100:.1f}% — approaching cap."
            action = "Limit remote agent; chunk remaining work"
        elif current >= CONFIG["CHUNK_THRESHOLD"]:
            alert = "ADVISE"
            msg = f"Grok bot usage at {current*100:.1f}% — near quota."
            action = "Consider chunking; remote agent at risk of hitting cap"
        else:
            alert = None
            msg = f"Grok bot usage at {current*100:.1f}% — healthy."
            action = "Continue remote agent work"

        record = UsageRecord(
            timestamp=current_time,
            run_id=self.run_id,
            action="check",
            start_usage_pct=self.start_usage or 0,
            end_usage_pct=current,
            duration_seconds=0,
            alert=alert,
            notes=msg
        )
        self._append_log(record)

        return {
            "alert": alert,
            "message": msg,
            "action": action,
            "current_usage": current,
            "threshold_warn": CONFIG["THRESHOLD_WARN"],
            "threshold_critical": CONFIG["THRESHOLD_CRITICAL"],
        }

    # ── Internal ────────────────────────────────────────────────────────────

    def _get_current_usage(self) -> float:
        """
        Get current Grok bot usage percentage (0.0 to 1.0).

        Override this method to connect to your actual Grok bot usage tracking.
        If CONFIG['GROK_USAGE_URL'] is set, fetch from there.
        Otherwise return a simulated value that drifts toward 100% over time.
        """
        if CONFIG["GROK_USAGE_URL"]:
            # Try to fetch from URL (JSON API)
            try:
                import urllib.request
                req = urllib.request.Request(
                    CONFIG["GROK_USAGE_URL"],
                    headers={"User-Agent": "LYTA-GrokBot-Monitor/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    # Adapt to your API response format
                    if isinstance(data, dict) and "usage" in data:
                        return float(data["usage"])
                    elif isinstance(data, dict) and "percent" in data:
                        return float(data["percent"]) / 100.0
            except Exception:
                pass

        # Fallback: simulated usage (just for demo/testing)
        # In production, replace with your actual usage tracking
        return self._simulated_usage()

    def _simulated_usage(self) -> float:
        """
        Simulated usage for paper-only environments.
        Returns a value between 0.0 and 1.0 that increases over time.
        """
        # Read last recorded usage to continue trend
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path) as f:
                    lines = f.readlines()
                if len(lines) > 2:
                    last_line = lines[-1]
                    parts = last_line.split(",")
                    if len(parts) >= 5:
                        try:
                            return min(float(parts[4]), 1.0)
                        except:
                            pass
            except:
                pass

        # Simulated usage: starts at 0.2 and increases toward 0.97
        # (paper-only: no real Grok bot usage, but shows how the monitor works)
        import random
        seed = hash(self.run_id) % 1000
        random.seed(seed)
        simulated = 0.20 + (0.77 * random.random())
        return min(simulated, 0.97)


# ── Convenience functions ─────────────────────────────────────────────────────

def check_grok_usage(monitor: Optional[UsageMonitor] = None) -> dict:
    """
    Convenience function: check Grok bot usage and return alert info.
    Creates a throwaway monitor if none provided.
    """
    if monitor is None:
        monitor = UsageMonitor()
    return monitor.check_thresholds()


def get_usage_log() -> list:
    """Read and return all usage log entries."""
    if not os.path.exists(CONFIG["LOG_FILE"]):
        return []
    with open(CONFIG["LOG_FILE"]) as f:
        return f.readlines()
