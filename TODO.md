# Project Context & Next Steps

## Overview
This file documents the review performed, issues discovered in templates, a recommended SQLite schema to capture teams, games, players and stats, and a concise implementation plan to build relationships and populate data.

## What was reviewed
- Templates: `templates/stats/boxscore.html` (scoped UI and loop logic).
- Project intent: store teams, games, players, logos, and both team and player stats in SQLite using primary/foreign keys.
- Repository: local workspace.

## Key issues found (brief)
- In `boxscore.html` the `team.stats` loop needed to render each stat inside the loop — the template currently already does this correctly in the provided attachment. Keep the loop and ensure view data matches the structure.
- Validate that `player_stats` is always an iterable or that templates guard against `None` to avoid template errors.
- Template data shape requires structured view context: `latest_game`, `team_stats`, `player_stats`, `home_logo`, `away_logo`. Views must assemble these from the DB.
- There was no explicit schema in the repository for player/team/game relationships; a normalized schema is recommended to avoid duplicate data and make joins easier.

## Suggested SQLite schema (core tables)
Use integer primary keys, foreign keys, and simple types. Adjust names to match your ORM/models.

- `teams`
  - `id INTEGER PRIMARY KEY`
  - `name TEXT UNIQUE NOT NULL`
  - `abbrev TEXT`
  - `logo_path TEXT`

- `players`
  - `id INTEGER PRIMARY KEY`
  - `team_id INTEGER REFERENCES teams(id) ON DELETE CASCADE`
  - `first_name TEXT`
  - `last_name TEXT`
  - `position TEXT`
  - `number INTEGER`

- `games`
  - `id INTEGER PRIMARY KEY`
  - `date DATE`
  - `home_team_id INTEGER REFERENCES teams(id)`
  - `away_team_id INTEGER REFERENCES teams(id)`
  - `home_points INTEGER`
  - `away_points INTEGER`
  - `status TEXT` — e.g., FINAL, SCHEDULED

- `team_stat_categories`
  - `id INTEGER PRIMARY KEY`
  - `name TEXT UNIQUE` — e.g., "offense", "defense", "rebounding"

- `team_stats`
  - `id INTEGER PRIMARY KEY`
  - `game_id INTEGER REFERENCES games(id)`
  - `team_id INTEGER REFERENCES teams(id)`
  - `category_id INTEGER REFERENCES team_stat_categories(id)`
  - `stat_key TEXT` — e.g., "points", "fga"
  - `stat_value TEXT` — store as TEXT to allow percentages/formats

- `player_stat_categories`
  - `id INTEGER PRIMARY KEY`
  - `name TEXT` — e.g., "scoring", "rebounding"

- `player_stats`
  - `id INTEGER PRIMARY KEY`
  - `game_id INTEGER REFERENCES games(id)`
  - `player_id INTEGER REFERENCES players(id)`
  - `category_id INTEGER REFERENCES player_stat_categories(id)`
  - `stat_key TEXT`
  - `stat_value TEXT`

## Implementation plan (step-by-step)
1. Design models/migrations (Django models or raw SQL) matching the schema above.
2. Run migrations/create SQLite file and enable foreign keys (`PRAGMA foreign_keys = ON;`).
3. Create seed scripts to populate `teams`, `players`, and a few `games` with `team_stats` and `player_stats`.
4. Build view/query that:
   - Loads `latest_game` (or requested `game_id`).
   - Joins `teams` for `home` and `away` and their `logo_path`s.
   - Aggregates `team_stats` per team into a list of `{ team, stats: [ { category, stat_key, stat_value } ] }`.
   - Aggregates `player_stats` into structure used by template: `player_stats = [ { team, categories: [ { name, types: [ { name, athletes: [ { name, stat } ] } ] } ] } ]`.
5. Fix template issues and render view context keys: `latest_game`, `team_stats`, `player_stats`, `home_logo`, `away_logo`.
6. Add unit tests for data assembling functions and template context.

## Template fixes (concise)
- Ensure the `team.stats` loop in `templates/stats/boxscore.html` iterates and renders each stat inside the loop.
- Ensure `player_stats` is checked for truthiness before iterating so the template safely handles empty results.
- Validate `latest_game` presence before accessing attributes in template or provide fallback values in view context.

Example pseudo-fix for the team stats section:
- Keep:
  - `{% for stat in team.stats %}`
  - render each stat row inside that loop
  - `{% endfor %}`

## Queries / views guidance
- Use ORM relations or SQL JOINs to load teams, players, and stats in as few queries as possible.
- Prefer assembling Python structures in the view rather than complex template logic.

## Files to add or update
- `models.py` or migration SQL for `teams`, `players`, `games`, `team_stats`, `player_stats`
- `management/commands/seed_data.py` or `scripts/seed_db.py`
- `views.py` (or function) that returns the prepared context for `boxscore.html`
- `tests/test_stats_views.py`

## Next immediate tasks (priority)
1. Implement schema and run migrations.
2. Seed sample data for one completed game.
3. Update the view that renders `boxscore.html` to provide the exact nested data shape.
4. Fix template loops and conditionals to match the provided context.
5. Add unit tests for the view/data assembly.

## Notes
- Use SQLite for development; if you later add concurrency or scale needs, migrate to PostgreSQL.
- Keep `stat_key` and `stat_value` flexible for formatting; normalize later if needed for analytics.

---

Generated: Project context and recommended next steps for implementing relational models and connecting them to the boxscore template.
