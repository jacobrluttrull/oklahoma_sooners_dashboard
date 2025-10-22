# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Commands

### Environment Setup
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set CFBD API token (required for all API operations)
setx BEARER_TOKEN "<your_cfbd_bearer_token>"
# OR for current session only:
$env:BEARER_TOKEN = "<your_cfbd_bearer_token>"
```

### Database Operations
```powershell
# Apply migrations
.venv\Scripts\python.exe manage.py migrate

# Refresh teams and schedule from CFBD API
.venv\Scripts\python.exe manage.py refresh_cfbd --year 2025 --team Oklahoma --conference SEC

# Create superuser (if needed)
.venv\Scripts\python.exe manage.py createsuperuser
```

### Development Server
```powershell
# Run development server
.venv\Scripts\python.exe manage.py runserver

# Access at: http://127.0.0.1:8000/
# Admin at: http://127.0.0.1:8000/admin/
```

### Testing
```powershell
# Run Django tests
.venv\Scripts\python.exe manage.py test stats

# Run standalone test scripts (requires Django setup)
.venv\Scripts\python.exe test_boxscore_prettify.py
.venv\Scripts\python.exe test_cfbd_api.py
.venv\Scripts\python.exe test_prettify.py
```

## Architecture

### Project Structure
- **oklahoma_dashboard/**: Main Django project configuration
  - `settings.py`: TIME_ZONE set to 'America/New_York', uses in-memory cache, SQLite database
  - `urls.py`: Root URL configuration
- **stats/**: Core Django app for football statistics
  - `models.py`: Team, Game, Player, TeamStat, PlayerStat models
  - `views.py`: Home dashboard and boxscore views
  - `cfb_api.py`: CFBD API integration and data fetching logic
  - `management/commands/refresh_cfbd.py`: Management command for data sync
- **templates/**: Django templates (Bootstrap-based UI)

### Data Flow & Architecture

#### API Integration Pattern
The app uses the **CollegeFootballData (CFBD) API** as its primary data source:
1. **Configuration**: API client created via `get_api_client()` using `BEARER_TOKEN` environment variable
2. **Idempotent Sync**: `refresh_cfbd` management command updates teams and schedule using CFBD game IDs as primary keys
3. **Caching Strategy**: 
   - Schedule data cached in-memory (LocMemCache) with freshness checks (<24h)
   - Player stats cached to avoid repeated API calls
   - Cache keys use year/team combinations

#### Model Relationships
```
Team (1) ----< (M) Game
            ├─ home_team FK
            ├─ away_team FK
            └─ opponent FK (legacy)

Team (1) ----< (M) Player
Player (1) ---< (M) PlayerStat >--- (1) Game
Team (1) -----< (M) TeamStat >----- (1) Game
```

**Key Fields**:
- `Team.cfbd_team_id`: Unique identifier from CFBD API
- `Game.cfbd_game_id`: Unique identifier for idempotent game updates
- `Game.last_updated`: Auto-updated timestamp for cache freshness
- `Game` has dual structure: legacy fields (`opponent`, `oklahoma_score`) + normalized fields (`home_team`, `away_team`, `home_points`, `away_points`)

#### View Logic Pattern
Views in `stats/views.py` follow this pattern:
1. **Fetch rankings** from CFBD API (used for context throughout)
2. **Retrieve cached or DB data** (schedule, team records)
3. **Fetch player season stats** (passing, rushing, receiving leaders)
4. **Calculate derived stats** (e.g., QB combined TDs = passing TDs + rushing TDs)
5. **Build nested context dict** for templates

For boxscore view:
1. Get most recent completed game from DB
2. Check if TeamStat/PlayerStat exist; if not, call `sync_game_stats()` to pull from API
3. Build nested player stats structure: `team → category → stat_type → athletes[]`
4. Prettify stat names using `prettify_stat_name()` for display

#### Name Normalization
Critical for matching teams across CFBD API responses:
- `normalize_name()`: Converts to uppercase, removes dots/ampersands/hyphens
- Used when looking up rankings and matching opponents
- Example: "U.S.C." → "USC", "Texas A&M" → "TEXAS A AND M"

#### Stat Prettification
`prettify_stat_name()` converts CFBD API stat names to human-readable labels:
- Tokenizes camelCase/snake_case/ALLCAPS
- Maps abbreviations (e.g., "qbr" → "QB Rating", "yds" → "Yards")
- Applied at template render time (not persisted to DB)

### Important Patterns

#### API Rate Limiting & Error Handling
- All CFBD API calls wrapped in try/except with fallback to "N/A" or None
- Functions return None on failure; views handle gracefully
- No retry logic—fails fast to avoid blocking requests

#### Time Zones
- Django `TIME_ZONE = 'America/New_York'`
- API responses converted to Eastern time using `pytz.timezone("US/Eastern")`
- Always use timezone-aware datetimes via `django.utils.timezone`

#### Database Constraints
- `Game` has unique constraint on `(date, home_team, away_team)`
- `cfbd_game_id` and `cfbd_team_id` are unique when present
- Use `update_or_create()` with CFBD IDs for idempotent syncing

#### Template Context Requirements
Templates expect specific nested data structures:
- **home.html**: `schedule` as list of dicts with opponent rank annotations
- **boxscore.html**: `player_stats` as `[{team, categories: [{name, types: [{name, athletes: [{name, stat}]}]}]}]`

### Development Notes

#### Adding New CFBD Data
When adding new data from CFBD API:
1. Create/update models with `cfbd_*_id` field for the CFBD identifier
2. Add function in `cfb_api.py` using `get_api_client()` context manager
3. Handle missing/None values gracefully (CFBD data can be sparse)
4. Use `update_or_create()` with CFBD ID for idempotency
5. Consider caching if data is frequently accessed

#### Testing Strategy
- Unit tests in `stats/tests.py` for models and utility functions
- Standalone test scripts (`test_*.py`) for quick validation
- Always test with real CFBD IDs to ensure normalization works
- Test with missing scores (upcoming games) and completed games

#### Common Gotchas
- CFBD API requires bearer token in environment—all API calls will fail silently without it
- Game model auto-computes `result` field on save—don't set it manually
- Rankings data is week-specific; latest_week_with_rank may be None early in season
- Template expects `opponent_rank` and `oklahoma_rank` even when None
- Virtual environment must be activated before running any Django commands
