# LYTA Pump.fun Grok Bot Trading Desk

**Phase 1 & 2 Trading Desk Experiment — OpenBot Platform**

> Platform: OpenBot | Agents: 7 (paper + pumpfun + signal + analyst + trader + risk + grok-bot) | Mode: Paper-only simulation

---

## 📊 Platform Comparison: Grok Bot vs OpenBot

| Criterion | **Grok Bot** | **OpenBot** | **Winner** |
|---|---|---|---|
| **Role** | Primary routing bot (Grok CLI) | Full desktop agent platform + CLI | OpenBot |
| **Agents configured** | 1 (Grok Bot itself) | **7** (paper, pumpfun, signal, analyst, trader, risk, grok-bot) | OpenBot |
| **Paper-only mode** | Not configured | All 7 agents paper-only with guards | OpenBot |
| **Trading desk logic** | Routing only | 12-bot voting, consensus, micro-sizing, risk layers | OpenBot |
| **Platform** | Hermes + Grok CLI (interactive TUI) | OpenBot desktop app + CLI (port 4132) | OpenBot |
| **Migration to Hermes** | `hermes import-agent grok-bot` | `hermes migrate openbot` | OpenBot |
| **MCP servers** | No | Yes (connector/network layer) | OpenBot |
| **Connectors** | No | Yes (pump.fun, Circuit, finance) | OpenBot |
| **GUI interface** | No (TUI only) | **Yes** (full desktop GUI) | OpenBot |
| **Sub-agent creation** | No | Yes (7 agents in projection_agents) | OpenBot |
| **Open-sourcing** | Partial (export JSON only) | **Full** (agent configs + db + prompts) | OpenBot |

### Verdict: **OpenBot is the best platform for the pump.fun trading desk experiment**

OpenBot provides the complete agent suite, paper-only mode documentation, full workflow management (MCP servers, connectors, channels), GUI interface, and the migration path to Hermes. It is the only platform that supports the full trading desk architecture.

---

## 🎯 Project Goal

Build a 12-bot trading desk experiment for the Lyta platform with:
- **Phase 1:** Circuit paper trading (BTC/ETH, ~$6 micro capital, paper-only)
- **Phase 2:** Adapt to actual pump.fun memecoin trading (awaiting platform data)

All agents are **paper-only**:
- No wallet import
- No signing
- No order execution
- No real trades

---

## 🧱 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    OpenBot Desktop (GUI)                │
│  Agents:  lyta-grok-desk-paper │ pumpfun │ signal │      │
│           analyst  │ trader  │ risk  │ grok-bot          │
└────────────────────────┬────────────────────────────────┘
                         │ sqlite3 (openbot.db)
┌────────────────────────▼────────────────────────────────┐
│                    Hermes (orchestration)               │
│  grok-bot (primary router)                              │
│  grok-acp (active model provider)                       │
│  grok CLI (v1.0.70) + LLM (grok-4.7)                    │
└─────────────────────────────────────────────────────────┘
                         │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   Pump.fun        Circuit Papertrade   MCP/Connectors
   /v1/stats       (BTC/ETH perps)      (finance, github)
```

---

## 📦 Phase 1 — Circuit Paper Trading (Ready)

### Agents Configured
- **lyta-grok-desk-paper** — 12-bot voting, consensus bar (5/12), micro-sizing ($0.20-$0.85), 3% risk, 5x max, paper-only

### Key Files
- `lyta-grok-desk/circuit.toml` — Circuit project config (papertrade, risk 3%, max lev 5)
- `lyta-grok-desk/index.ts` — TypeScript agent with 12-bot desk logic
- `lyta-grok-desk/CIRCUIT_PAPER_PROMPT.txt` — Copy-paste prompt for Circuit Builder

### Agent Flow
```
Market Data → 12 Bots Vote → Consensus Check (5/12) → Micro Size → Paper Trade
```

### Trading Desk Logic
| Setting | Value |
|---|---|
| Risk per trade | 3% |
| Max leverage | 5x |
| Micro sizing | $0.20 - $0.85 |
| Consensus bar | 5/12 bots |
| Paper-only | ✅ |
| No wallet import | ✅ |
| No signing | ✅ |
| No order execution | ✅ |

---

## 🚀 Phase 2 — Pump.fun Memecoin Trading (Awaiting Data)

### Agents Configured
- **lyta-grok-desk-pumpfun** — Phase 2 pump.fun memecoin trading (awaiting platform data)
- **lyta-grok-desk-signal** — Signal generation (no execution)
- **lyta-grok-desk-analyst** — Analytics (analyst_score, rug_risk, liquidity)
- **lyta-grok-desk-trader** — Execution (paper-only, micro sizing)
- **lyta-grok-desk-risk** — Risk management (3% risk, 5x max, stand-down)

### Data Flow
```
pump.fun /v1/stats → PumpFunDataAdapter → Market Schema → 12-Bot Voting Engine
```

### Key Files
- `pumpfun_adapter.py` — Normalizes pump.fun payload to desk internal schema
- `pumpfun_desk_simulator.py` — Full paper trading simulator for pump.fun

### Awaiting Data
- Platform data for pump.fun trading metrics
- Paper simulation metrics for Phase 2 validation

---

## 🛠️ Setup & Migration

### Step 1: Install OpenBot
```bash
# macOS, download DMG from GitHub releases
curl -sL "https://github.com/nightly-labs/openbot/releases/download/v0.60.0/OpenBot-0.60.0-arm64.dmg" -o /tmp/OpenBot-0.60.0-arm64.dmg
hdiutil attach /tmp/OpenBot-0.60.0-arm64.dmg
cp -R "/Volumes/OpenBot 0.60.0/OpenBot.app" /Applications/
open "/Applications/OpenBot.app"
```

### Step 2: Migrate to Hermes
```bash
hermes migrate openbot --source /Users/test/Library/Application\ Support/OpenBot --yes
```

### Step 3: Verify Agents
```bash
sqlite3 /Users/test/Library/Application\ Support/OpenBot/openbot.db "SELECT agent_id FROM projection_agents ORDER BY sort_order"
# Should show 7 agents: paper, pumpfun, signal, analyst, trader, risk, grok-bot
```

### Step 4: Run Grok Bot
```bash
# In Hermes, use grok-bot as primary router
# The grok CLI is at /opt/homebrew/bin/grok (v1.0.70, logged in as kubo100x@proton.me)
```

---

## 📊 Agent Suite

| Agent | ID | Role | Mode |
|---|---|---|---|
| Lyta Grok Desk - Circuit Paper | `lyta-grok-desk-paper` | Paper trading (BTC/ETH) | Paper-only |
| Lyta Grok Desk - PumpFun Phase 2 | `lyta-grok-desk-pumpfun` | Pump.fun trading | Paper-only |
| Grok Bot | `grok-bot` | Primary routing | Live |
| Lyta Grok Desk - Signal | `lyta-grok-desk-signal` | Signal generation | Paper-only |
| Lyta Grok Desk - Analyst | `lyta-grok-desk-analyst` | Analytics | Paper-only |
| Lyta Grok Desk - Trader | `lyta-grok-desk-trader` | Execution | Paper-only |
| Lyta Grok Desk - Risk | `lyta-grok-desk-risk` | Risk management | Paper-only |

---

## 📁 Project Files

| File | Purpose |
|---|---|
| `README.md` | Main documentation |
| `grokbot_multi.py` | 12-agent desk simulator |
| `pumpfun_adapter.py` | Pump.fun data adapter |
| `pumpfun_desk_simulator.py` | Pump.fun paper simulator |
| `paper_desk_simulator.py` | Circuit paper simulator |
| `lyta-grok-desk/index.ts` | TypeScript agent (Circuit) |
| `lyta-grok-desk/circuit.toml` | Circuit project config |
| `lyta-grok-desk/CIRCUIT_PAPER_PROMPT.txt` | Copy-paste prompt |
| `comparison_showcase.md` | Platform comparison (this document) |

---

## 📜 License

MIT License — consistent with the Hermes project and the pump.fun trading desk experiment.

---

> ⚠️ **Paper-Only Mode Warning:** All trading agents are paper-only. No real trades executed. No wallet import. No signing. No order execution. The platform is awaiting live platform data for Phase 2 metrics before proceeding.

---

*Last updated: 2026-11-03 | Platform: OpenBot | Mode: Paper-only simulation*
