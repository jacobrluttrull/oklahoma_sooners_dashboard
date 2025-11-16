# Oklahoma Sooners Dashboard

The Oklahoma Sooners Dashboard is a Django app that uses the CollegeFootballData (CFBD) API to surface season records, rankings context, player leaders, a season schedule with rank annotations, and a latest-game box score.

Key highlights
- Normalized schema with Teams and Games (home/away FKs, CFBD IDs, neutral site, etc.).
- Idempotent schedule sync keyed by CFBD game ID when available.
- Caching for player season stats and schedule reuse with freshness checks.
- Clean Bootstrap templates and a management command to refresh data.

Requirements
- Python 3.13 (or compatible 3.10+)
- A CFBD API bearer token: https://collegefootballdata.com/key

Setup (Windows)
1) Create and activate a virtualenv
```
python -m venv .venv
.venv\Scripts\activate
```
2) Install dependencies
```
pip install -r requirements.txt
```
3) Set your CFBD bearer token in the environment (PowerShell)
```
setx BEARER_TOKEN "<your_cfbd_bearer_token>"
```
Close and reopen your shell to get the variable, or set for just the current session:
```
$env:BEARER_TOKEN = "<your_cfbd_bearer_token>"
```

Database and run
1) Apply migrations
```
.venv\Scripts\python.exe manage.py migrate
```
2) (Optional) Preload teams and schedule with rankings
```
.venv\Scripts\python.exe manage.py refresh_cfbd --year 2025 --team Oklahoma --conference SEC
```
3) Start the dev server
```
.venv\Scripts\python.exe manage.py runserver
```
Visit http://127.0.0.1:8000/

Management command
- refresh_cfbd: updates SEC teams and the specified team schedule idempotently with rankings context
  - Flags: --year, --team, --conference

Notes
- Time zone is configured to America/New_York in Django settings.
- Templates extend base.html; home shows schedule, leaders, next game, and latest victory.
- Admin is enabled for Team and Game for quick inspection.

Next steps (suggested)
- Add Player and GamePlayerStat models; store CFBD IDs and upsert by ID.
- Add tests for schedule upserts (with/without CFBD ID) and rankings by week.
- Expose last updated timestamps more broadly in the UI.
