# Telegram Counter Bot (SQLite + Docker)

A lightweight Telegram bot that lets users add named counters and increment them via inline buttons. Each chat (private or group) keeps its own list in a single SQLite database.

> NOTE: The majority of this codebase (structure, source, and documentation) was generated with the help of AI assistance.

## Features
- SQLite persistence (separate logical list per chat)
- Inline buttons with live refresh of the message
- Command menu (/add, /list, /up, /top, /reset, /help)
- Admin check for /reset in group chats
- Docker + docker-compose setup

## Tech Stack
- Python 3.11
- [python-telegram-bot 21.x](https://docs.python-telegram-bot.org/)
- SQLite (file-based, WAL mode)
- Docker / docker-compose

## Project Structure
```
telegram-counter-bot/
├─ app/
│  ├─ bot.py
│  └─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
├─ .dockerignore
├─ .env.example
└─ README.md
```
A host `./data` directory (created at runtime) stores the SQLite DB (`entries.db`).

## Getting a Bot Token
1. Talk to **@BotFather** in Telegram
2. Create a new bot and copy the provided `BOT_TOKEN`

## Quick Start (Docker)
```powershell
# Clone project
git clone <your-repo-url> telegram-counter-bot
cd telegram-counter-bot

# Create env file
copy .env.example .env   # (PowerShell) or: cp .env.example .env
# Edit .env and insert your real BOT_TOKEN

# Build and start
docker compose up --build -d

# View logs
docker compose logs -f
```
The SQLite database file will appear in `./data/entries.db` on the host.

## Manual Run (Without Docker)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r app/requirements.txt
$env:BOT_TOKEN="123456:ABC..."  # set your token
python -m app.bot
```
On Linux/macOS the activation / env export differ:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
export BOT_TOKEN="123456:ABC..."
python -m app.bot
```

## Commands
| Command | Description |
|---------|-------------|
| `/add <text>` | Add a new counter entry |
| `/list` | Show the list with inline buttons |
| `/up <text>` | Increment (alternative to button) |
| `/top` | Show top 3 entries |
| `/reset` | Reset list (group admins only) |
| `/help` | Show help text |

## Behavior & Notes
- Entries are stored in lowercase to avoid duplicates (`UNIQUE(chat_id, name)`).
- WAL mode improves concurrent read performance.
- Inline keyboard is fully redrawn after each increment to keep order sorted.
- The DB path can be overridden with `DB_PATH` env var (default: `./data/entries.db`).

## Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `BOT_TOKEN` | Telegram bot API token | (required) |
| `DB_PATH` | SQLite file path inside container | `/app/data/entries.db` |

## Docker Tips
Rebuild after dependency changes:
```powershell
docker compose build --no-cache bot
```
Stop & remove:
```powershell
docker compose down
```
Remove volumes (including DB data):
```powershell
docker compose down -v
```

## Security Considerations
- Treat your `BOT_TOKEN` like a secret; never commit `.env`.
- SQLite file permissions are restricted by the non-root `botuser` inside the container.
- For production behind proxies, configure `HTTP_PROXY` / `HTTPS_PROXY` environment variables if needed.

## Future Ideas
- Add /stats with more detailed breakdown
- Add export/import of counters (CSV or JSON)
- Add rate limiting or flood protection
- Migrate to Postgres for multi-instance scaling
- Add tests (pytest) and CI workflow

## License
Choose and add a license file (e.g. MIT) before publishing. (Currently none specified.)

## Acknowledgment
This repository was largely generated using AI assistance; manual review and adjustments are recommended before production use.
