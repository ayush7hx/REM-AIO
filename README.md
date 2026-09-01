<p align="center">
  <img src="remaio.png" alt="DARK INFINITE" width="100%">
</p>

<h1 align="center">DARK INFINITE</h1>

<p align="center">
  <b>One bot. Every tool. Zero clutter.</b><br>
  moderation · security · music · tickets · games · welcome · logging
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-0ea5e9?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/discord.py-2.x-5865F2?style=flat-square&logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/Components_V2-enabled-f472b6?style=flat-square" alt="Components V2">
  <img src="https://img.shields.io/badge/119_cogs-8b5cf6?style=flat-square" alt="119 cogs">
  <img src="https://img.shields.io/badge/MIT-22c55e?style=flat-square" alt="MIT">
</p>

<p align="center">
  <a href="#about">About</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#features">Features</a> ·
  <a href="#music">Music</a> ·
  <a href="#setup">Setup</a> ·
  <a href="#environment">Environment</a> ·
  <a href="#project-structure">Structure</a>
</p>

---

## About

**REM** is a full-featured all-in-one Discord bot — moderation, security, music, tickets, welcome flows, games, and utilities in one place.

Everything runs through soft pastel **Components V2** panels, so setup and daily use stay clean instead of spread across multiple bots.

---

## Quick Start

```bash
pip install -r requirements.txt
copy .env.example .env
python rem.py
```

| Step | Command | Notes |
|:---:|:---|:---|
| 1 | `pip install -r requirements.txt` | Install dependencies |
| 2 | Copy `.env.example` → `.env` | Add your bot token |
| 3 | `python rem.py` | Start the bot |

**Required in `.env`:**

```env
TOKEN=your_discord_bot_token
OWNER_IDS=your_user_id
PREFIX=>
```

Enable **Message Content** and **Server Members** intents in the Discord Developer Portal.

---

## Features

<table>
<tr>
<td align="center" width="25%">
  <img src="assets/readme/feature-security.png" width="100%" alt="Security">
  <br><b>Security</b>
</td>
<td align="center" width="25%">
  <img src="assets/readme/feature-music.png" width="100%" alt="Music">
  <br><b>Music</b>
</td>
<td align="center" width="25%">
  <img src="assets/readme/feature-tools.png" width="100%" alt="Server Tools">
  <br><b>Server Tools</b>
</td>
<td align="center" width="25%">
  <img src="assets/readme/feature-games.png" width="100%" alt="Games">
  <br><b>Games</b>
</td>
</tr>
</table>

<br>

<table>
<tr>
<td width="50%" valign="top">

### Security & Moderation
- **Antinuke** — block nukes before damage spreads
- **Automod** — spam, caps, links, invites
- **Nightmode & emergency** — lock down dangerous permissions
- Ban · kick · timeout · warn · jail · purge · snipe
- Whitelist · blacklist · ignore · topcheck

### Music
- Lavalink playback via Wavelink
- Player, search, and queue cards
- Loop · shuffle · autoplay · volume

</td>
<td width="50%" valign="top">

### Server Management
- Tickets · giveaways · logging
- Welcome · autorole · vanity roles
- Invite tracker · reaction roles

### Fun & Utilities
- Chess · Wordle · 2048 · RPS · blackjack
- AI chat *(optional key)*
- Translate · QR · maps · stats · AFK

</td>
</tr>
</table>

---

## Music

| Command | Description |
|:---|:---|
| `>play <song>` | Play a track or playlist |
| `>search <query>` | Search and pick a result |
| `>nowplaying` | Current track info |
| `>queue` | View upcoming songs |
| `>pause` / `>resume` / `>skip` | Playback controls |
| `>volume <1-150>` | Set volume |
| `>loop` / `>shuffle` / `>autoplay` | Queue modes |

**Optional Lavalink config:**

```env
LAVALINK_ENABLED=true
LAVALINK_URI=http://127.0.0.1:2333
LAVALINK_PASSWORD=youshallnotpass
```

Restart the bot fully after changing music settings.

---

## Setup

| Requirement | Purpose |
|:---|:---|
| Python **3.11+** | Runtime |
| Discord **bot token** | Authentication |
| **Message Content** intent | Prefix commands |
| **Server Members** intent | Mod, welcome, security |
| Lavalink *(optional)* | Music playback |

**Permissions:** Administrator is easiest, or grant manage server, roles, channels, messages, ban/kick/moderate, embeds, and connect/speak for music.

Security commands (`antinuke`, `automod`, `emergency`, etc.) require **owner**, **admin**, or **bypass** access.

---

## Environment

| Key | Required | Purpose |
|:---|:---:|:---|
| `TOKEN` | ✅ | Bot token |
| `OWNER_IDS` | ✅ | Owner user ID(s) |
| `PREFIX` | — | Default `>` |
| `BOT_NAME` | — | Display name in panels |
| `BYPASS_IDS` | — | Trusted bypass users |
| `LAVALINK_URI` | 🎵 | Music node |
| `OPENAI_API_KEY` | — | AI chat |
| `COMMAND_LOG_WEBHOOK_URL` | — | Command logs |

See [`.env.example`](.env.example) for the full list.

---

## Project Structure

```text
rem.py              → entry point
core/               → bot class + context
cogs/commands/      → user commands
cogs/moderation/    → moderation actions
cogs/antinuke/      → anti-nuke listeners
cogs/automod/       → automod listeners
cogs/rem/           → help panels
utils/              → config, database, CV2 UI
games/              → game engines
db/                 → SQLite databases
```

---

## Development

```bash
python -m compileall rem.py cogs utils core
```

Health endpoint *(when keep-alive is on):* `GET http://127.0.0.1:8080/health`  
Logs: `logs/rem.log`

**Security tips:** Never commit `.env` or database files. Regenerate your token if leaked. Keep `OWNER_IDS` and `BYPASS_IDS` minimal. Restart after permission or env changes.

---

<p align="center">
  <sub>MIT License</sub>
</p>
