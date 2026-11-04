# 🏆 LYTA PUMP.FUN TRADING DESK — Platform Comparison Showcase

**User:** Rei Kubota | **Workspace:** /Users/test/projects/lyta-grokbot-multi | **Experiment:** Pump.fun Grok Bot Trading Desk

---

## 📊 External: "Grok Bot vs OpenBot — Which Platform for the Trading Desk?"

| Criterion | **Grok Bot** | **OpenBot** | **Winner** |
|---|---|---|---|
| **Role** | Primary routing bot (Grok CLI) | Full desktop agent platform + CLI | OpenBot |
| **Agents configured** | 1 (Grok Bot itself) | **7** (paper, pumpfun, signal, analyst, trader, risk, grok-bot) | OpenBot |
| **Paper-only mode** | Not configured | All 7 agents paper-only with guards | OpenBot |
| **Trading desk logic** | Routing only | 12-bot voting, consensus, micro-sizing, risk layers | OpenBot |
| **Platform** | Hermes + Grok CLI (interactive TUI) | OpenBot desktop app + CLI (port 4132) | OpenBot |
| **Migration to Hermes** | `hermes import-agent grok-bot` | `hermes migrate openbot` ✅ | OpenBot |
| **MCP servers** | No | Yes (connector/network layer) | OpenBot |
| **Connectors** | No | Yes (pump.fun, Circuit, finance) | OpenBot |
| **GUI interface** | No (TUI only) | **Yes** (full desktop GUI) | OpenBot |
| **Sub-agent creation** | No | Yes (7 agents in projection_agents) | OpenBot |
| **Open-sourcing** | Partial (export JSON only) | **Full** (agent configs + db + prompts) | OpenBot |

---

## 🎯 VERDICT: OpenBot is the Best Platform for the Pump.fun Trading Desk Experiment

### Why OpenBot wins

1. **Complete agent suite** — All 7 agents created in `openbot.db`:
   - `lyta-grok-desk-paper` (Phase 1 Circuit paper trading)
   - `lyta-grok-desk-pumpfun` (Phase 2 pump.fun memecoin)
   - `lyta-grok-desk-signal` (signal generation)
   - `lyta-grok-desk-analyst` (analytics & rug risk)
   - `lyta-grok-desk-trader` (execution, paper-only)
   - `lyta-grok-desk-risk` (3% risk, 5x max, stand-down)
   - `grok-bot` (primary routing bot)

2. **Paper-only mode** — Every agent declares paper-only constraints:
   - `no_wallet_import` — rejects live frameworks
   - `no_signing_or_order_execution` — rejects send_transaction, sign_transaction, place_order, execute_swap
   - `paper_label_present` — "PAPER ONLY" + "SIMULATION"
   - `shared_state_paper_flag` — `paper_only: true` in state
   - `spec_simulation_only` — spec declares `SIMULATION` + `paper_only: true`

3. **Full workflow management** — MCP servers, connectors, channels, desktop GUI for managing the entire trading desk.

4. **Migration path** — All agents already migrated to Hermes via `hermes migrate openbot` (exit 0).

5. **Trading desk logic** — The actual 12-bot voting, consensus bar (5+), micro-sizing ($0.20-$0.85), risk management lives in:
   - `lyta-grok-desk/circuit.toml`
   - `lyta-grok-desk/index.ts`
   - `pumpfun_adapter.py`
   - `paper_desk_simulator.py`
   - `pumpfun_desk_simulator.py`

---

## 📁 Project Structure (Open-Source Ready)

```
lyta-grokbot-multi/
├── README.md                    # Main project documentation
├── grokbot_multi.py             # 12-agent desk simulator (stdlib)
├── pumpfun_adapter.py           # Pump.fun data adapter
├── pumpfun_desk_simulator.py    # Pump.fun paper trading simulator
├── paper_desk_simulator.py      # Circuit paper trading simulator
├── STRATEG_TYPE_FINALIZE.md     # Strategy documentation
├── PAPER_COMPLETE.md            # Paper trading completion report
├── _verify_final.py             # Verification script
├── verify_80step.py             # 80-step viability test
├── 100x_adapter_report.md       # Adaptation report
├── lyta-grok-desk/              # Phase 1 Circuit agents
│   ├── index.ts                 # 12-bot desk TypeScript agent
│   ├── circuit.toml             # Circuit project config
│   ├── circuit-sdk.d.ts         # Circuit SDK types
│   ├── DESCRIPTION.md           # Agent description
│   ├── package.json             # Node package
│   ├── bun.lock                 # Bun lockfile
│   ├── CIRCUIT_PAPER_PROMPT.txt # Copy-paste prompt
│   ├── CIRCUIT_PUMPFUN_PROMPT.txt
│   ├── CIRCUIT_PUMPFUN_EXIT_PROMPT.txt
│   └── CIRCUIT_PUMPFUN_UPDATE_PROMPT.txt
└── memories/ (Hermes)
    ├── MEMORY.md               # All 7 agents documented
    └── USER.md                 # User profile (Rei Kubota)
```

---

## 🚀 Open-Sourcing Plan

### Steps to open-source the outcome

1. **Create GitHub repository:**
   ```bash
   gh repo create lyta-grokbot-multi --public
   ```

2. **Initialize Git and commit all files:**
   ```bash
   cd /Users/test/projects/lyta-grokbot-multi
   git init
   git add -A
   git commit -m "🐕 LYTA Pump.fun Grok Bot Trading Desk — Phase 1 & 2 agents"

3. **Push to GitHub:**
   ```bash
   git branch -M main
   git remote add origin https://github.com/<your-username>/lyta-grokbot-multi.git
   git push -u origin main
   ```

4. **Add Open-Source README:**
   The existing `README.md` already documents the project. Add:
   - Platform comparison (Grok Bot vs OpenBot)
   - Verdict: OpenBot
   - How to run the 12-bot trading desk
   - Paper-only mode documentation
   - Phase 1 and Phase 2 descriptions

5. **Include OpenBot agent configs:**
   - `openbot.db` (users can migrate via `hermes migrate openbot`)
   - Agent instructions and memory records

6. **License:**
   - MIT License (consistent with Hermes project)
   - Include `LICENSE` file

7. **GitHub Pages / Documentation:**
   - Deploy the project docs
   - Add badge for paper-only mode status
   - Add "Platform: OpenBot" badge

---

## ✅ Completed Actions

1. **Refreshed Hermes models** — `hermes model --refresh` exit 0
2. **Grok CLI verified** — v1.0.70, logged in as `kubo100x@proton.me`, `grok-4.7` default
3. **Grok Bot imported** — role, memories, user facts written to Hermes MEMORY.md/USER.md
4. **OpenBot installed** — `/Applications/OpenBot.app` (DMG 0.60.0-arm64)
5. **OpenBot agents created** — 7 agents in `projection_agents` table
6. **Agents migrated to Hermes** — `hermes migrate openbot --source ... --yes` exit 0
7. **All agents documented** — MEMORY.md updated with all 7 agents
8. **Comparison verified** — Grok Bot vs OpenBot table complete
9. **Verdict determined** — OpenBot is the best for the pump.fun trading desk experiment

---

## 🔜 Next Steps

- [ ] Create GitHub repository `lyta-grokbot-multi`
- [ ] Add MIT LICENSE file
- [ ] Push all project files
- [ ] Add Open-Source README with comparison table
- [ ] Document platform choice (OpenBot) and migration steps
- [ ] Add badges to README
- [ ] Host documentation

---

> ⚠️ **Paper-Only Mode Warning:** All trading agents are paper-only. No real trades executed. No wallet import. No signing. No order execution. This is a simulation/experiment only. The platform is awaiting live platform data for Phase 2 metrics.
