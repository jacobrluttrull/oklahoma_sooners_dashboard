# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## How to Assist the Developer

### Developer Background
- **New to Django**: The developer is learning Django - explain concepts clearly and avoid assumptions about advanced Django knowledge.
- **IDE**: Uses Windows and PyCharm 2025.2.4
- **Role of Claude**: You are a helper and guide, **not a substitute** for the developer. Think of yourself as a tutor and code reviewer.

### Critical Constraints
- **No complete file rewrites** - Do not produce or replace entire files unless explicitly requested and authorized
- **Incremental changes only** - Make targeted, focused changes to specific functions/sections, not sweeping rewrites
- **No arbitrary function limits** - Provide as many functions as needed for a focused change, but keep changes scoped to one specific task/file
- **Explain your reasoning** - Include short, explicit explanations and rationale for each change

### Response Format Guidelines
When suggesting code changes:
1. **Focused changes**: Provide all functions needed for a specific, scoped task
2. **Exact file paths**: Use backticked paths like `stats/views.py`
3. **Code snippets**: Provide clear code blocks with brief plain-English summaries
4. **One task at a time**: Keep changes focused on solving one specific problem
5. **Windows commands**: Use `python manage.py` commands for local testing (not bash/Linux commands)
6. **Database changes**: Prefer Django CLI migration instructions over editing migration files directly

### Preferred Workflows

**For Feature Requests**:
- Propose a minimal design and list the files to be touched
- Provide all necessary functions/code for that focused feature
- Show how to test locally: `python manage.py runserver` and `python manage.py test`

**For Debugging**:
- Ask for the failing traceback or relevant file content
- Propose focused fixes with all necessary changes
- Explain why the fix works

**For Data/Analysis Tasks**:
- Suggest safe, batched approaches (e.g., team-by-team fetches, conference subsets)
- Warn about hitting external API rate limits and memory issues
- Avoid running or fetching large datasets from external APIs on behalf of the developer

### Code Style Expectations
- Use clear function names, docstrings, and type hints where useful
- Prefer small unit tests added to `stats/tests.py`
- Keep tests targeted and minimal

### Example Requests That Work Well
✅ "Help me add a function to `stats/cfb_api.py` that converts API game objects to model dicts. Show the function and tests."

✅ "I have a traceback from `stats/views.py` when rendering `team_stats.html`. Here's the traceback. Suggest fixes and the exact lines to change."

✅ "Refactor the Game model to use helper methods instead of Oklahoma-centric fields"

❌ "Rewrite the entire views.py file from scratch"

❌ "Redesign the entire database schema and regenerate all models"

### What You Must Never Do
- ❌ Write entire files or complete rewrites unless explicitly requested
- ❌ Make sweeping changes across many unrelated files at once
- ❌ Run or fetch large datasets from external APIs
- ❌ Modify migration files directly without explicit permission
- ❌ Assume advanced Django knowledge

---

## Project Overview

This is a Django web application that displays Oklahoma Sooners football statistics using the College Football Data (CFBD) API. It shows season records, rankings, player leaders, game schedules with rank annotations, boxscores, and conference standings for the SEC.

### Project Structure (High Level)
- **`stats/` app**: Core app containing models, views, `cfb_api.py`, and management commands under `stats/management/commands/`
- **`team_stats_util.py`**: Database-based PPG calculation utilities
- **`scripts/`**: Offline diagnostic tools
- **`templates/stats/`**: HTML templates for views
- **`db.sqlite3`**: Local SQLite database (dev environment on Windows)
- **`manage.py`**: Django management script in repo root

## Environment Setup

**Python Version**: 3.13 (or compatible 3.10+)

**Required Environment Variable**:
- `BEARER_TOKEN`: Your CFBD API token from https://collegefootballdata.com/key

Set on Windows (PowerShell):
```powershell
# Permanent (requires reopening shell):
setx BEARER_TOKEN "<your_token>"

# Current session only:
$env:BEARER_TOKEN = "<your_token>"
```

**Virtual Environment** (Windows):
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Common Commands

### Database Operations
```bash
# Apply migrations
.venv\Scripts\python.exe manage.py migrate

# Create superuser for admin access
.venv\Scripts\python.exe manage.py createsuperuser
```

### Data Refresh Commands

**Refresh Oklahoma schedule and SEC teams** (for current season):
```bash
.venv\Scripts\python.exe manage.py refresh_cfbd --year 2025 --team Oklahoma --conference SEC
```

**Fetch all FBS games** (required for accurate PPG calculations - takes 5-10 minutes):
```bash
# All 133 FBS teams:
.venv\Scripts\python.exe manage.py fetch_all_games --year 2025

# Single team:
.venv\Scripts\python.exe manage.py fetch_all_games --year 2025 --team "Alabama"
```

**Backfill team logos**:
```bash
.venv\Scripts\python.exe manage.py backfill_logos --year 2025 --conference SEC
```

### Running the Development Server
```bash
.venv\Scripts\python.exe manage.py runserver
```
Visit http://127.0.0.1:8000/

### Testing Utilities (in project root)
```bash
# Test CFBD API connection
.venv\Scripts\python.exe test_cfbd_api.py

# Test PPG calculation functions
.venv\Scripts\python.exe test_ppg_functions.py

# Run PPG diagnostics
.venv\Scripts\python.exe scripts\run_ppg_diagnostics.py
```

## Architecture & Data Flow

### Database Models (`stats/models.py`)

**Team**: Stores team information including name, conference, colors, CFBD team ID, and logo URL.

**Game**: Central model with dual structure:
- **Oklahoma-centric fields**: `opponent`, `home_away`, `oklahoma_score`, `opponent_score`, `result`
- **Normalized fields**: `home_team` (FK), `away_team` (FK), `home_points`, `away_points`, `cfbd_game_id`
- **Constraints**: Unique on `cfbd_game_id` or `(date, home_team, away_team)`
- **Auto-saves**: Result ('W'/'L') calculated automatically from scores

**Player**: Player roster linked to teams with CFBD player IDs.

**TeamStat**: Game-level team statistics (per game, per team, per category).

**PlayerStat**: Game-level player statistics (per game, per player, per category/stat_type).

### Key Data Functions (`stats/cfb_api.py`)

**API Client Setup**:
- `get_api_client()`: Creates CFBD API client with bearer token

**Data Fetching**:
- `fetch_team_record()`: Gets overall and conference records
- `fetch_next_game()`: Returns upcoming game with rankings
- `fetch_latest_victory()`: Returns most recent win with rankings
- `fetch_player_stats()`: Fetches passing/rushing/receiving stats (cached 600s)
- `fetch_and_cache_schedule()`: Idempotently stores full season schedule (24h freshness check)
- `fetch_conference_standings()`: Gets conference standings with win percentages and streaks
- `sync_game_stats()`: Pulls detailed team/player stats for a specific game into DB

**Team/Logo Management**:
- `update_teams_from_conference()`: Bulk fetch and store teams with logos for a conference
- `ensure_team_logo()`: Ensures a team has a logo URL (fetches from API if missing)
- `get_team_logo()`: Returns logo URL for a team (name or object)

**Rankings & Helpers**:
- `get_rankings()`: Fetches AP Top 25 rankings by week
- `normalize_name()`: Standardizes team names for matching (handles "Ole Miss" → "MISSISSIPPI", etc.)
- `prettify_stat_name()`: Converts API stat names to human-readable labels (e.g., "qbr" → "QB Rating")

**PPG Calculations**:
- `get_team_ppg()`: API-based PPG for conference teams (cached 1 hour) - used in conference standings view
- See `team_stats_util.py` for database-based PPG calculations (more accurate, used in team stats page)

### Views Architecture (`stats/views.py`)

**home** (`/`):
- Displays: records, rankings, next game, latest victory, player leaders, full schedule
- Uses cached player stats (10-min timeout)
- Ensures team logos exist for all schedule opponents

**boxscore** (`/boxscore/` or `/boxscore/<game_id>/`):
- Shows detailed game stats (team stats + player stats in ESPN-style format)
- Syncs stats from API on first view (then cached in DB)
- Player stats pivoted by player (all stats in one row per player)

**team_stats** (`/team-stats/`):
- Displays Oklahoma's PPG, total points, games played
- Shows national and SEC rankings using database-based calculations
- Uses `get_oklahoma_ppg_rankings()` from `team_stats_util.py`

**conference_standings** (`/conference-standings/`):
- SEC standings with conference/overall records, win percentages, streaks
- Includes PPG for each team
- Highlights Oklahoma's position and handles ties

### PPG Calculation System (`team_stats_util.py`)

**Two PPG Calculation Approaches**:
1. **API-based** (`stats/cfb_api.py:get_team_ppg()`): Fetches games from API, used for conference standings
2. **Database-based** (`team_stats_util.py`): Calculates from stored games, more accurate after running `fetch_all_games`

**Key Functions**:
- `get_oklahoma_ppg()`: Returns Oklahoma's PPG and total points from DB
- `get_all_team_ppg(year, team_name=None, conference=None)`: Returns PPG dict for all/filtered teams
- `get_oklahoma_ppg_rankings(year)`: Returns Oklahoma's national and SEC rankings with metadata

**Workflow for Accurate PPG**:
1. Run `fetch_all_games --year 2025` to populate all FBS games
2. Database-based functions in `team_stats_util.py` calculate from complete data
3. National rankings include all ~133 FBS teams, SEC rankings include 16 SEC teams

### Caching Strategy

**Django Cache** (LocMemCache configured in `settings.py`):
- Player stats: 600 seconds (10 minutes)
- Team PPG (API-based): 3600 seconds (1 hour)
- Schedule: 24-hour freshness check (DB-backed)

**Database Caching**:
- Games cached with `last_updated` timestamp
- Schedule reused if updated within 24 hours
- Team/player stats stored in DB after first fetch

### Management Commands

**refresh_cfbd** (`stats/management/commands/refresh_cfbd.py`):
- Updates SEC teams and Oklahoma schedule
- Fetches rankings and caches schedule idempotently
- Flags: `--year`, `--team`, `--conference`

**fetch_all_games** (`stats/management/commands/fetch_all_games.py`):
- Fetches all FBS games team-by-team (133 teams across 11 conferences)
- Skips duplicates using `cfbd_game_id`
- Auto-assigns team conferences
- Rate limiting: 0.5s delay every 10 teams
- Flags: `--year`, `--team` (optional for single team)

**backfill_logos** (`stats/management/commands/backfill_logos.py`):
- Fetches and stores team logos for a conference
- Run after database rebuilds or when logos are missing

## Important Patterns & Conventions

### Idempotent Data Syncing
- All data fetch operations use `update_or_create()` or check freshness before re-fetching
- Games identified by `cfbd_game_id` when available, else by `(date, home_team, away_team)`
- Stats synced once per game and stored in DB (TeamStat, PlayerStat)

### Oklahoma-Centric vs. Normalized Schema
- Game model maintains both perspectives for backwards compatibility
- New code should use normalized fields (`home_team`, `away_team`, `home_points`, `away_points`)
- Oklahoma-centric fields populated automatically for Oklahoma games

### Team Name Normalization
- Always use `normalize_name()` when matching team names from different sources
- Handles HTML entities, punctuation, common abbreviations
- Critical for rankings matching and logo lookups

### Timezone Configuration
- Project timezone: `America/New_York` (settings.py:116)
- Game times displayed in Eastern Time
- Use `pytz.timezone("US/Eastern")` for conversions

### Template Structure
- Base template: `templates/base.html` (Bootstrap 5, Oklahoma crimson/cream colors)
- App templates: `templates/stats/*.html`
- Template tags: `stats/templatetags/stat_extras.py` (if custom filters needed)

## Testing & Development Notes

### Pre-Deployment Checklist
1. Run `fetch_all_games --year 2025` for complete PPG data
2. Run `refresh_cfbd --year 2025 --team Oklahoma --conference SEC` for current schedule
3. Test boxscore view loads and syncs stats correctly
4. Verify team logos display (run `backfill_logos` if needed)

### Common Issues
- **Missing logos**: Run `backfill_logos` or ensure `ensure_team_logo()` is called
- **Stale data**: Check `last_updated` timestamps or clear cache
- **Duplicate games**: Fetch logic prevents duplicates via `cfbd_game_id` or unique constraint
- **API rate limiting**: `fetch_all_games` includes delays; don't run concurrently

### Secret Key Warning
- `settings.py:24` contains dev secret key - **DO NOT use in production**
- Set `DEBUG = False` and use environment-based secrets for deployment

## URLs & Routes

```
/                           → home (stats.views.home)
/boxscore/                  → latest game boxscore (stats.views.boxscore)
/boxscore/<game_id>/        → specific game boxscore
/team-stats/                → team statistics page (stats.views.team_stats)
/conference-standings/      → SEC standings (stats.views.conference_standings)
/admin/                     → Django admin (Team, Game, Player, TeamStat, PlayerStat)
```

## Future Development Notes (from TODO.md)

High-priority unimplemented features include:
- Expanding team stats page with offensive/defensive breakdowns
- Player leaders dashboard (`/stats/players/`)
- Game-by-game performance charts
- Automatic data refresh scheduling (Celery/Django-Q)
- Enhanced caching layer (Redis)

See `TODO.md` for complete feature roadmap.