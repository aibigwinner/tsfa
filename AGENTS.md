# Instructions for opencode agents working on this project

## Project
Telegram bot for Shadow Fight 4: Arena tournaments.
- GitHub: https://github.com/aibigwinner/tsfa
- Deployed on Render free plan

## Tech stack
- Python 3.11+, python-telegram-bot v22+ (webhooks mode on Render)
- SQLite (via `database.py`), previously JSON
- All formatting in HTML mode (`ParseMode.HTML`) with `html.escape()`

## Critical facts
- `RENDER` env var is `"true"` (not `"1"`) — check via `in ("1", "true", "yes")`
- `RENDER_EXTERNAL_URL` must be set manually in Render Dashboard
- JSON auto-migrates to SQLite on first run via `migrate_from_json()`
- Admin ID: 7153815329

## Commands
- `python main.py` — run locally (polling)
- `python app.py` — run for Render (webhook, reads PORT/$RENDER)

## Architecture
- `app.py` — entry point for Render (webhook), calls `build_application()` from main.py
- `main.py` — `build_application()`, registers all handlers + error_handler
- `database.py` — `SQLiteStorage` class (generic id+data per table), `migrate_from_json()`
- `storage.py` — public API: `get_or_create_player()`, `get_player()`, `create_battle()`, etc.
- `handlers/` — feature modules (battle, tournament, admin, profile, voting, achievements, characters, notifications, start)

## Data model
- Tables in `data/bot.db`: players, battles, tournaments, challenges, polls
- Each table: `id TEXT PK`, `data TEXT` (JSON blob)
- `players.get(key)` / `players.set(key, value)` / `players.all()` / `players.filter(pred)`

## Key patterns
- `owner_id` in `context.user_data` to prevent button stealing between users
- `battle_step` state machine in user_data for multi-step workflows
- `html.escape()` (aliased as `h`) on all user-provided strings in HTML mode
- Error handler sends error to admin's DM (not to chat)

## Deploy
1. Commit & push to main
2. Render → Manual Deploy → Deploy latest commit
3. After deploy: send `/backup` before, `/restore` after

## Cron setup
Render free web services sleep after 15 minutes idle. Use cron-job.org (free):
- URL: `https://<name>.onrender.com/`
- Interval: every 10 minutes
- Any HTTP request (even 404) counts as activity

## Testing
Tests go in `tests/` directory if any.
- `pip install -r requirements.txt`
- `python app.py` for Render webhook mode
- `python main.py` for local polling mode
