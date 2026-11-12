#!/usr/bin/env python3
"""
LYTA Trading Desk Web Dashboard Server
=======================================
Serves the live trading_desk.html with auto-refresh.
Usage:
    python3 web_dashboard.py              # auto-detects paper_run.py
    python3 web_dashboard.py --port 8888
    python3 web_dashboard.py --paper-run path/to/paper_run.py

The user opens http://localhost:8000 in a browser and watches the
trading desk update in real-time as paper_run.py regenerates HTML.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import webbrowser
from pathlib import Path
from datetime import datetime


def find_paper_run() -> str | None:
    """Find paper_run.py in the repo."""
    for p in [Path.cwd(), Path(__file__).parent]:
        candidate = p / "paper_run.py"
        if candidate.exists():
            return str(candidate)
    # Search upward
    current = Path.cwd()
    for _ in range(5):
        if (current / "paper_run.py").exists():
            return str(current / "paper_run.py")
        current = current.parent
    return None


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LYTA Trading Desk</title>
<script>
// Phase 2 pump.fun config - paper-only mode
window.PHASE = "2";
window.TRADING_MODE = "pumpfun";
window.PAPER_ONLY = true;
window.LIVE_TRADES = false;
window.WALLET_IMPORT = false;
window.SIGNING = false;
window.TELEGRAM_ALERTS = false;
</script>
<style>
  :root {
    --bg: #0f1115;
    --card: #1a1d26;
    --fg: #e1e4ea;
    --muted: #8b90a0;
    --accent: #6366f1;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #f59e0b;
    --border: #2a2d3a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'SF Mono', 'JetBrains Mono', 'Fira Code', monospace;
    background: var(--bg);
    color: var(--fg);
    padding: 16px;
    min-height: 100vh;
  }
  .container { max-width: 1200px; margin: 0 auto; }
  header {
    display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 16px; border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
  }
  h1 { font-size: 1.2rem; font-weight: 600; }
  .status-badge { padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; }
  .status-badge.green { background: rgba(34,197,94,0.15); color: var(--green); }
  .status-badge.yellow { background: rgba(245,158,11,0.15); color: var(--yellow); }
  .status-badge.red { background: rgba(239,68,68,0.15); color: var(--red); }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px; margin-bottom: 12px;
  }
  .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  .metric { text-align: center; padding: 10px; }
  .metric-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
  .metric-value { font-size: 1.3rem; font-weight: 700; margin-top: 4px; }
  .metric-value.pos { color: var(--green); }
  .metric-value.neg { color: var(--red); }
  .metric-value.neutral { color: var(--yellow); }
  .bot-table { overflow-x: auto; }
  .bot-table table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  .bot-table th, .bot-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
  .bot-table th { color: var(--muted); font-weight: 500; font-size: 0.7rem; text-transform: uppercase; }
  .bot-table .buy { color: var(--green); font-weight: 700; }
  .bot-table .sell { color: var(--red); font-weight: 700; }
  .bot-table .pass { color: var(--muted); }
  .bot-table .hold { color: var(--yellow); font-weight: 700; }
  .bot-table .stand_down { color: #a5b4fc; font-style: italic; }
  .alerts { max-height: 200px; overflow-y: auto; }
  .alerts .alert { padding: 8px 10px; border-radius: 4px; margin-bottom: 4px; font-size: 0.85rem; }
  .alerts .alert.info { background: rgba(99,102,241,0.1); color: var(--accent); }
  .alerts .alert.success { background: rgba(34,197,94,0.1); color: var(--green); }
  .alerts .alert.error { background: rgba(239,68,68,0.1); color: var(--red); }
  .alerts .alert.warn { background: rgba(245,158,11,0.1); color: var(--yellow); }
  .pulse { animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
  .live-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--green); margin-right: 6px; animation: pulse 1s infinite; }
  .ctrl { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
  .btn {
    padding: 8px 16px; border-radius: 6px; border: 1px solid var(--border);
    background: var(--card); color: var(--fg); cursor: pointer; font-family: inherit; font-size: 0.9rem;
  }
  .btn:hover { border-color: var(--accent); }
  .btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .footer { text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 16px; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1><span class="live-dot"></span>LYTA Trading Desk</h1>
    <div>
      <span id="clock" class="status-badge green">--:--:--</span>
      <span id="session-status" class="status-badge">Waiting for data...</span>
    </div>
  </header>

  <div class="card">
    <div class="metric-grid">
      <div class="metric">
        <div class="metric-label">Paper Capital</div>
        <div class="metric-value" id="capital">$0.00</div>
      </div>
      <div class="metric">
        <div class="metric-label">Asset</div>
        <div class="metric-value" id="asset">—</div>
      </div>
      <div class="metric">
        <div class="metric-label">Ticks</div>
        <div class="metric-value" id="ticks">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Positions</div>
        <div class="metric-value" id="positions">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Total Votes</div>
        <div class="metric-value" id="total-votes">0</div>
      </div>
      <div class="metric">
        <div class="metric-label">Last Update</div>
        <div class="metric-value" id="last-update">—</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="metric-grid" style="grid-template-columns: 1fr 1fr;">
      <div class="metric" style="text-align:left;">
        <div class="metric-label">Net Signal</div>
        <div class="metric-value" id="net-signal">—</div>
      </div>
      <div class="metric" style="text-align:left;">
        <div class="metric-label">Buy Votes</div>
        <div class="metric-value" id="buy-votes">0</div>
      </div>
      <div class="metric" style="text-align:left;">
        <div class="metric-label">Sell Votes</div>
        <div class="metric-value" id="sell-votes">0</div>
      </div>
      <div class="metric" style="text-align:left;">
        <div class="metric-label">Pass Votes</div>
        <div class="metric-value" id="pass-votes">0</div>
      </div>
      <div class="metric" style="text-align:left;">
        <div class="metric-label">Hold</div>
        <div class="metric-value" id="hold-votes">0</div>
      </div>
      <div class="metric" style="text-align:left;">
        <div class="metric-label">Stand Down</div>
        <div class="metric-value" id="stand-down-votes">0</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2 style="font-size:0.9rem; font-weight:600; margin-bottom:8px;">ABSOLUTE Bot Votes</h2>
    <div class="bot-table">
      <table id="bot-table">
        <thead>
          <tr>
            <th>Bot</th><th>Signal</th><th>Liquidity</th><th>Score</th><th>Rug Risk</th><th>24h Change</th>
          </tr>
        </thead>
        <tbody>
          <tr><td colspan="6" style="color:var(--muted); text-align:center;">Waiting for data...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <h2 style="font-size:0.9rem; font-weight:600; margin-bottom:8px;">Alert Log</h2>
    <div class="alerts" id="alert-log">
      <div class="alert info">System initialized. Waiting for paper_run.py to connect...</div>
    </div>
  </div>

  <div class="ctrl">
    <button class="btn primary" id="refresh-btn" onclick="location.reload()">↻ Refresh Now</button>
    <button class="btn" id="open-btn" onclick="openTradingDesk()">📂 Open in Browser</button>
  </div>

  <div class="footer">
    LIVE | Updated: <span id="sys-time">--:--:--</span> | Paper trading only — no real orders executed
  </div>
</div>

<script>
  // Auto-refresh every 5 seconds
  setInterval(() => {
    fetch('/api/state')
      .then(r => r.json())
      .then(data => updateDashboard(data))
      .catch(() => {});
  }, 5000);

  function updateDashboard(data) {
    if (!data || data.error) { return; }

    document.getElementById('capital').textContent = '$' + (data.capital || 0).toFixed(2);
    document.getElementById('asset').textContent = data.asset || '—';
    document.getElementById('ticks').textContent = data.ticks || 0;
    document.getElementById('positions').textContent = data.positions || 0;
    document.getElementById('total-votes').textContent = data.total_votes || 0;
    document.getElementById('last-update').textContent = data.last_update || '—';

    // Net signal
    const votes = data.votes || {};
    const buy = votes.buy || 0;
    const sell = votes.sell || 0;
    const pass = votes.pass || 0;
    const hold = votes.hold || 0;
    const standDown = votes.stand_down || 0;
    const total = buy + sell + pass + hold + standDown;

    document.getElementById('net-signal').textContent = total > 0 ? (buy > sell ? '✅ BUY' : sell > buy ? '❌ SELL' : '⚖️ HOLD') : '—';
    document.getElementById('buy-votes').textContent = buy;
    document.getElementById('sell-votes').textContent = sell;
    document.getElementById('pass-votes').textContent = pass;
    document.getElementById('hold-votes').textContent = hold;
    document.getElementById('stand-down-votes').textContent = standDown;

    // Bot table
    const table = document.getElementById('bot-table');
    if (data.bots && data.bots.length > 0) {
      table.querySelector('tbody').innerHTML = data.bots.map(bot => {
        const cls = bot.side === 'buy' ? 'buy' : bot.side === 'sell' ? 'sell' : bot.side === 'hold' ? 'hold' : bot.side === 'stand_down' ? 'stand_down' : 'pass';
        return `<tr>
          <td>${bot.bot || ''}</td>
          <td class="${cls}">${bot.side || ''}</td>
          <td>${(bot.liquidity ?? '').toFixed(2)}</td>
          <td>${bot.score ?? ''}</td>
          <td>${bot.rug_risk ?? ''}</td>
          <td>${bot.change24h ?? ''}%</td>
        </tr>`;
      }).join('');
    } else {
      table.querySelector('tbody').innerHTML = '<tr><td colspan="6" style="color:var(--muted); text-align:center;">No bot data yet</td></tr>';
    }

    // Alerts
    const alerts = data.alerts || [];
    const alertLog = document.getElementById('alert-log');
    if (alerts.length > 0) {
      alertLog.innerHTML = alerts.slice(-10).map(a =>
        `<div class="alert ${a.level || 'info'}">${a.message || ''}</div>`
      ).join('');
    }

    // Clock
    document.getElementById('clock').textContent = new Date().toLocaleTimeString();
    document.getElementById('sys-time').textContent = new Date().toLocaleTimeString();

    // Session status
    const status = document.getElementById('session-status');
    status.textContent = data.session_running ? 'Session ACTIVE' : 'Session STOPPED';
    status.className = 'status-badge ' + (data.session_running ? 'green' : 'red');
  }

  // Open in new tab
  function openTradingDesk() {
    window.open('/trading_desk.html', '_blank');
  }

  // Initial load
  fetch('/api/state')
    .then(r => r.json())
    .then(data => updateDashboard(data))
    .catch(() => {
      document.getElementById('alert-log').innerHTML +=
        '<div class="alert error">⚠️ Cannot connect to dashboard server. Make sure paper_run.py is running.</div>';
    });
</script>
</body>
</html>
"""


def find_trading_desk() -> str | None:
    """Find trading_desk.py."""
    for p in [Path.cwd(), Path(__file__).parent]:
        candidate = p / "lyta-grok-desk" / "trading_desk.py"
        if candidate.exists():
            return str(candidate)
    current = Path.cwd()
    for _ in range(5):
        if (current / "lyta-grok-desk" / "trading_desk.py").exists():
            return str(current / "lyta-grok-desk" / "trading_desk.py")
        current = current.parent
    return None


class TradingDeskServer:
    def __init__(self, port: int = 8000, paper_run: str | None = None):
        self.port = port
        self.paper_run = paper_run or find_paper_run()
        self.trading_desk = find_trading_desk()
        self.state_file = Path("trading_desk_state.json")
        self._state = {
            "capital": 100.0, "asset": "GOBLIN", "ticks": 0,
            "positions": 0, "total_votes": 0, "last_update": "",
            "session_running": False, "alerts": [],
            "votes": {"buy": 0, "sell": 0, "pass": 0, "hold": 0, "stand_down": 0},
            "bots": [], "error": None
        }
        self._lock = None

    def get_state(self) -> dict:
        if self.state_file.exists():
            try:
                import json
                return json.loads(self.state_file.read_text())
            except Exception:
                pass
        return {
            "capital": 100.0, "asset": "GOBLIN", "ticks": 0,
            "positions": 0, "total_votes": 0, "last_update": "",
            "session_running": False, "alerts": [],
            "votes": {"buy": 0, "sell": 0, "pass": 0, "hold": 0, "stand_down": 0},
            "bots": [], "error": None
        }

    def update_state(self, updates: dict):
        """Write state to JSON file for web server consumption."""
        import json
        state = self.get_state()
        state.update(updates)
        state["last_update"] = datetime.now().strftime("%H:%M:%S")
        self.state_file.write_text(json.dumps(state, indent=2))

    def render_dashboard(self) -> str:
        return DASHBOARD_HTML

    def start(self):
        if not self.paper_run:
            print("⚠️  Could not find paper_run.py. Running without live updates.")
        if not self.trading_desk:
            print("⚠️  Could not find trading_desk.py")

        print("=" * 56)
        print("  LYTA Trading Desk Web Server")
        print("=" * 56)
        print(f"  Paper runner: {self.paper_run or 'not found'}")
        print(f"  Dashboard:    http://localhost:{self.port}")
        print(f"  State API:    http://localhost:{self.port}/api/state")
        print(f"  Docs:         http://localhost:{self.port}/trading_desk.html")
        print("=" * 56)
        print("  Press Ctrl+C to stop.")
        print()

        # Launch the paper runner in a background thread if found
        if self.paper_run:
            import subprocess
            print(f"  → Launching paper runner: python3 {self.paper_run}")
            print()
            # Use Popen with new session so Ctrl+C doesn't propagate
            proc = subprocess.Popen(
                ["python3", self.paper_run],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            # Stream output to console
            import threading
            def stream_output():
                for line in proc.stdout:
                    print(line, end="")
                    sys.stdout.flush()
            threading.Thread(target=stream_output, daemon=True).start()
            self._proc = proc

        try:
            # Simple HTTP server
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import threading

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    path = self.path.split('?')[0]

                    if path == '/':
                        self.serve_dashboard()
                    elif path == '/trading_desk.html':
                        self.send_file('trading_desk.html')
                    elif path == '/api/state':
                        self.send_json(self.server.desk.get_state())
                    else:
                        self.send_error(404)

                def serve_dashboard(self):
                    html = DASHBOARD_HTML
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(html)))
                    self.end_headers()
                    self.wfile.write(html.encode())

                def send_file(self, filename):
                    path = Path(filename)
                    if path.exists():
                        content = path.read_bytes()
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.send_header('Content-Length', str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                    else:
                        self.send_error(404)

                def send_json(self, data):
                    import json
                    body = json.dumps(data).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, fmt, *args):
                    pass  # Suppress logs

            # Attach server to desk for access from handler
            class Server(HTTPServer):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.desk = self.__dict__.get('desk', self)

            # Create server with desk reference
            server = Server(('127.0.0.1', self.port), Handler)
            server.desk = self
            self._server = server

            print(f"  Server running at http://localhost:{self.port}")
            print(f"  Open in your browser to see the live trading desk.")
            print()
            webbrowser.open(f"http://localhost:{self.port}")

            # Run
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\n\nShutting down...")
                if hasattr(server, 'desk') and hasattr(server.desk, '_proc'):
                    server.desk._proc.terminate()
                server.shutdown()
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LYTA Trading Desk Web Server")
    parser.add_argument("--port", "-P", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--paper-run", "-p", type=str, help="Path to paper_run.py")
    parser.add_argument("--no-open", action="store_true", help="Do not open browser")
    args = parser.parse_args()

    server = TradingDeskServer(port=args.port, paper_run=args.paper_run)
    server.start()
