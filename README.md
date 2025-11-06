# Oklahoma Sooners Football Dashboard

A comprehensive Django web application that provides real-time college football statistics, detailed game analytics, and conference standings using the College Football Data (CFBD) API. Originally focused on Oklahoma Sooners football, the architecture now supports multi-team analysis with normalized data models and intelligent caching.

## 🏈 Key Features

### Live Game Data & Analytics
- **Real-time Schedule Tracking**: Displays full season schedules with weekly AP/Coaches Poll rankings for both teams
- **Detailed Box Scores**: ESPN-style game statistics with pivoted player stats, team stats, and game summaries
- **Next Game Preview**: Shows upcoming matchup with current rankings and venue information
- **Latest Victory Highlights**: Automatically surfaces the most recent win with full game context

### Player Statistics
- **Season Leaders Dashboard**: Tracks passing, rushing, and receiving leaders with comprehensive stats
- **Cross-Category Stats**: Shows QB rushing stats, RB receiving stats, and combined touchdown totals
- **Cached Player Data**: Intelligent API caching reduces redundant calls and improves performance

### Team & Conference Analytics
- **Points Per Game Rankings**: Calculates and displays PPG with national (FBS) and conference (SEC) rankings
- **Conference Standings**: Full SEC standings table with win-loss records, conference records, and PPG
- **Team Comparisons**: Highlights Oklahoma's position within the conference with visual indicators

### Robust Data Management
- **Normalized Database Schema**: Teams and Games with proper foreign keys (home/away), CFBD IDs, and neutral site tracking
- **Idempotent Data Sync**: Schedule updates key by CFBD game ID to prevent duplicates
- **Multi-Team Support**: Refactored from Oklahoma-centric to support any FBS team
- **Logo Management**: Automatic team logo fetching and backfill utilities

## 🗂️ Architecture Highlights

### Models (`stats/models.py`)
- **Team**: Stores FBS teams with CFBD IDs, conference, colors, and logos
- **Game**: Normalized home/away structure with legacy Oklahoma fields for backward compatibility
- **Player**: Player roster with CFBD IDs and team relationships
- **TeamStat & PlayerStat**: Relational stats linked to games for detailed box score displays
- **Helper Methods**: `get_opponent()`, `get_result_for_team()`, `get_score_for_team()` for team-agnostic game queries

### Management Commands
- **`refresh_cfbd`**: Syncs Oklahoma schedule and SEC teams for a given year
- **`fetch_all_games`**: Fetches all FBS games (133 teams) for accurate PPG calculations
- **`backfill_logos`**: Ensures all teams in the database have logos from CFBD API

### Views & Pages
- **Home (`/`)**: Season dashboard with records, rankings, leaders, schedule, and next game
- **Box Score (`/boxscore/`)**: Detailed game statistics for the most recent completed game
- **Box Score by ID (`/boxscore/<game_id>/`)**: View any specific game's statistics
- **Team Stats (`/team_stats/`)**: Oklahoma's PPG, total points, and rankings
- **Conference Standings (`/standings/`)**: Full SEC standings with sortable columns

### Smart Caching & Performance
- **Database-First Approach**: Uses local SQLite for fast queries and reduced API calls
- **Freshness Checks**: `last_updated` timestamps track data staleness
- **Batch Processing**: `fetch_all_games` supports conference-based subsets to avoid rate limits
- **Logo Backfilling**: Ensures logos are available even after database rebuilds

## 📋 Requirements

- Python 3.13 (or compatible 3.10+)
- Django 5.x
- CFBD API bearer token from https://collegefootballdata.com/key
- SQLite (dev) or PostgreSQL (production-ready)

## ⚙️ Setup (Windows)

### 1. Clone and Create Virtual Environment
```bash
git clone https://github.com/jacobrluttrull/oklahoma_sooners_dashboard.git
cd oklahoma_sooners_dashboard
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set CFBD API Token
In PowerShell:
```powershell
# Permanent (requires reopening shell):
setx BEARER_TOKEN "<your_cfbd_bearer_token>"

# Current session only:
$env:BEARER_TOKEN = "<your_cfbd_bearer_token>"
```

### 4. Initialize Database
```bash
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py createsuperuser
```

### 5. Load Initial Data
```bash
# Fetch Oklahoma schedule and SEC teams for 2025
.venv\Scripts\python.exe manage.py refresh_cfbd --year 2025 --team Oklahoma --conference SEC

# Optional: Fetch all FBS games for accurate PPG rankings (5-10 minutes)
.venv\Scripts\python.exe manage.py fetch_all_games --year 2025
```

### 6. Run Development Server
```bash
.venv\Scripts\python.exe manage.py runserver
```

Visit http://127.0.0.1:8000/ to view the dashboard!

## 🧪 Testing

Run the test suite:
```bash
.venv\Scripts\python.exe manage.py test stats
```

## 🛠️ Technical Details

- **Time Zone**: Configured to `America/New_York` in Django settings
- **Admin Interface**: Enabled for Team, Game, Player, TeamStat, and PlayerStat models
- **Template System**: Bootstrap-based responsive design extending `base.html`
- **API Integration**: Uses `cfbd-python` SDK with custom wrappers in `cfb_api.py`
- **Utility Scripts**: Offline diagnostic tools in `scripts/` and database utilities in `team_stats_util.py`

## 🚀 Future Enhancements

- [ ] Historical season comparison (multi-year analysis)
- [ ] Player profile pages with career stats
- [ ] Advanced filtering and sorting on all data tables
- [ ] Export functionality for stats (CSV/JSON)
- [ ] Drive-by-drive game analysis
- [ ] Betting line integration
- [ ] Playoff projections and scenarios

## 📝 Notes

- Built as a learning project for Django by a developer new to the framework
- Refactored from team-specific to generalized multi-team architecture
- Uses helper methods and normalized fields for team-agnostic queries
- Designed for easy extension to other teams and conferences

## 📄 License

This project is open source and available under the MIT License.

---

**Developer**: Jacob Luttrull ([@jacobrluttrull](https://github.com/jacobrluttrull))  
**API**: Powered by [College Football Data API](https://collegefootballdata.com)