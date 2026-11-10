# Bot Comparison — Grok bot vs OpenBot

Yes/No contrast table. Each row states a design characteristic; "**Yes**"
denotes OpenBot, "**No**" denotes Grok bot. Read the section below for
how the two compare on privacy, cost, and locality.

## Quick Map

|| Dimension | Grok bot | OpenBot |
||---|---|---|
|| Type | Cloud paper trader + on-chain scanner | Local desktop agent host |
|| Agent framework | 12-agent circuit.ts workspace | 7 named agents (FIFO + messaging) |
|| Execution | Cloud server + local clients | Local desktop |
|| Data stays on your machine | No | Yes |
|| Cost | Self-hosted (free), but uses paid providers | Free (non-commercial) |
|| Scheduler / automation | Yes (market hours) | Yes (Keep awake / routines) |
|| Ledger | Books local: journal + ledger + state | Books local: chat, files, code |
|| Chat / human-in-loop | ✅ Yes (text-thread interface) | ✅ Yes (chat, approve actions) |
|| Mobile app | ✅ Yes (iPhone/Android) | ✅ Yes |
|| Voice / dictation | ✅ Yes (voice input, voice chat) | ✅ Yes (31 languages) |
|| Teams / roles | ✅ Yes (group chats, parallel bots, roles) | ✅ Yes (roles, shared channels) |
|| Backup models | ✅ Yes (cloud backup, multiple plans) | ✅ Yes |
|| Source code | ✅ Open (lyta-grokbot-multi) | ✅ Open (openbot.io) |

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
- 12-agent circuit.ts workspace
- Market-hours automated scheduling
- Text-thread chat interface and human-in-the-loop approval
- Mobile app, voice/dictation, backup models, teams/roles

## Framing

Grok bot is a paper-trading variant, not a general-purpose agent host.
Its strengths are execution-focused: live market coverage, on-chain scanning,
and spot signal monitoring. Both Grok bot and OpenBot provide mobile app,
voice/dictation, backup models, teams/roles, and chat/human-in-the-loop.

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
