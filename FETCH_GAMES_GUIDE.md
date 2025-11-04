# Fetching All FBS Games Guide

## Overview
The `fetch_all_games` management command fetches games team-by-team for all 133 FBS teams to ensure accurate PPG calculations.

## Usage

### Fetch all FBS teams (~5-10 minutes for all teams):
```bash
python manage.py fetch_all_games --year 2025
```

### Fetch a single team:
```bash
python manage.py fetch_all_games --year 2025 --team "Alabama"
```

## Features
- **Duplicate Detection**: Automatically skips games already in database using cfbd_game_id
- **Smart Rate Limiting**: Small delays every 10 teams to avoid API rate limits
- **Conference Auto-Assignment**: Sets team conferences automatically during fetch
- **Progress Tracking**: Shows real-time progress for each team processed

## Supported Teams
All 133 FBS teams across 11 conferences:
- **SEC** (16 teams): Alabama, Arkansas, Auburn, Florida, Georgia, Kentucky, LSU, Mississippi State, Missouri, Ole Miss, Oklahoma, South Carolina, Tennessee, Texas, Texas A&M, Vanderbilt
- **Big Ten** (18 teams): Illinois, Indiana, Iowa, Maryland, Michigan, Michigan State, Minnesota, Nebraska, Northwestern, Ohio State, Penn State, Purdue, Rutgers, Wisconsin, Oregon, UCLA, USC, Washington
- **ACC** (17 teams): Boston College, Clemson, Duke, Florida State, Georgia Tech, Louisville, Miami, North Carolina, NC State, Pittsburgh, Syracuse, Virginia, Virginia Tech, Wake Forest, California, SMU, Stanford
- **Big 12** (16 teams): Arizona, Arizona State, Baylor, BYU, UCF, Cincinnati, Colorado, Houston, Iowa State, Kansas, Kansas State, Oklahoma State, TCU, Texas Tech, Utah, West Virginia
- Plus 7 more conferences (American, Conference USA, FBS Independents, Mid-American, Mountain West, Pac-12, Sun Belt)

## After Fetching Games

Once games are fetched, you can use the PPG functions:

### Django Shell:
```python
from team_stats_util import get_all_team_ppg, get_oklahoma_ppg_rankings

# Get all teams' PPG
all_ppg = get_all_team_ppg(year=2025)
print(f"Total teams: {len(all_ppg)}")

# Get Oklahoma's rankings
ok_ranks = get_oklahoma_ppg_rankings(year=2025)
print(f"Oklahoma PPG: {ok_ranks['ppg']}")
print(f"National Rank: {ok_ranks['national_rank']} of {ok_ranks['national_total_teams']}")
print(f"SEC Rank: {ok_ranks['sec_rank']} of {ok_ranks['sec_total_teams']}")

# Get SEC teams only
sec_ppg = get_all_team_ppg(year=2025, conference='SEC')
sorted_sec = sorted(sec_ppg.items(), key=lambda x: -x[1])
for i, (team, ppg) in enumerate(sorted_sec, 1):
    print(f"{i}. {team}: {ppg}")
```

## Notes
- The command includes a 1-second delay between conferences to avoid rate limiting
- Team conferences are automatically set when games are fetched
- Incomplete games (no scores yet) are automatically skipped
- Games are deduplicated using cfbd_game_id or (date, home_team, away_team)

