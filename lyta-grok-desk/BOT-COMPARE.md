# Bot Comparison — Grok bot vs OpenBot

Yes/No contrast table. Each row states a design characteristic; "**Yes**"
denotes OpenBot, "**No**" denotes Grok bot. Read the section below for
how the two compare on privacy, cost, and locality.

## Quick Map

| Dimension | OpenBot | Grok bot |
|---|---|---|
| Type | Local desktop agent host | Cloud paper trader + on-chain scanner |
| Agent framework | 7 named agents (FIFO + messaging) | 12-agent circuit.ts workspace |
| Execution | Local desktop | Cloud server + local clients |
| Data stays on your machine | Yes | No |
| Cost | Free (non-commercial) | Self-hosted (free), but uses paid providers |
| Scheduler / automation | Yes (Keep awake / routines) | Yes (market hours) |
| Ledger | Books local: chat, files, code | Books local: journal + ledger + state |
| Chat / human-in-the-loop | Yes (chat, approve actions) | No |
| Mobile app | Yes (iPhone/Android) | No |
| Voice / dictation | Yes (31 languages) | No |
| Teams / roles | Yes (roles, shared channels) | No |
| Backup models | Yes | No |
| Source code | Open source | Open source |

## Design Characteristics

**OpenBot offers:**
- Local-first execution and data hosting
- Mobile app and voice/dictation support
- Team roles and structured chat
- Backup and restore of models
- Free non-commercial cost model
- Scheduler/routine automation

**Grok bot offers:**
- Cloud paper-trading execution on the same local-first stack
- On-chain scanning and spot signal monitoring
- 12-agent circuit.ts workspace (vs. 7 named agents)
- Market-hours automated scheduling
- Closed-loop chat and human-in-the-loop approval: none

## Framing

Grok bot is a paper-trading variant, not a general-purpose agent host.
Its strengths are execution-focused: live market coverage, on-chain scanning,
and spot signal monitoring. Its limitations are also execution-focused:
it does not run as a local desktop agent host, so it has no mobile app,
no voice/dictation, no backup models, no teams/roles, and no local data
storage for chat and files.

## Privacy, Cost, and Locality

These three axes are where the two diverge most sharply:

- **Privacy:** OpenBot keeps data on your machine. Grok bot is cloud
  hosted and therefore cannot offer that guarantee.
- **Cost:** OpenBot is free (non-commercial). Grok bot uses paid cloud
  providers on top of a free self-hosted base — not a standalone cost
  advantage.
- **Locality:** OpenBot runs fully on your desktop with a mobile app. Grok bot
  requires a cloud server and has no mobile app, no voice, and no offline mode.

On these axes, Grok bot is not a substitute for OpenBot's local-first
design; it is a complementary paper-trading layer.
