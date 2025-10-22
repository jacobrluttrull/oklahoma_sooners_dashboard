# Repository Guidelines

## Project Structure & Module Organization
The Django project root contains `manage.py`, configuration in `oklahoma_dashboard/`, and the primary `stats/` app with models, views, and the `cfb_api.py` integrations. HTML is under `templates/` (shared `base.html` plus `templates/stats/` feature pages), while static assets live in `stats/static/`. Management commands (including `refresh_cfbd`) sit in `stats/management/commands`, and lightweight integration tests reside alongside unit tests in `stats/tests.py` and the root `test_*.py` modules.

## Build, Test, and Development Commands
Create the virtual environment and install dependencies:
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
Apply migrations and load CFBD data when needed:
```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py refresh_cfbd --year 2025 --team Oklahoma --conference SEC
```
Run the development server with `.venv\Scripts\python.exe manage.py runserver`, and execute the full suite via `.venv\Scripts\python.exe manage.py test`.

## Coding Style & Naming Conventions
Use PEP 8 conventions with four-space indentation, f-strings for formatting, and snake_case for variables, methods, and Django template context keys. Keep Django models and serializers concise; extract CFBD-specific helpers into `cfb_api.py`. HTML templates follow Bootstrap classes and extend `base.html`, so block names should remain consistent (`content`, `scripts`). Avoid introducing global state—prefer dependency injection through function parameters.

## Testing Guidelines
Django’s built-in test runner is the default; organize new suites under `stats/tests.py` or add focused modules under `stats/tests/`. Name methods `test_<behavior>` and include fixtures in `setUp()` or factory helpers. For API integrations, mock outbound CFBD calls and assert caching behavior mirrors the patterns in `CachedScheduleTests`. Aim to cover new models, views, and management commands before opening a PR.

## Commit & Pull Request Guidelines
Commit messages follow an imperative, sentence-case summary (`Add WARP.md for project setup and development guidelines`). Group related changes per commit, and include migrations or fixtures when schema updates occur. Pull requests should state the feature or fix, reference any issues, describe data refresh requirements, and document new commands or environment variables. Attach screenshots for UI changes (home dashboard, box score views) and note test results from `manage.py test`.

## Environment & Data Access
Set the CFBD bearer token before hitting remote endpoints (`$env:BEARER_TOKEN = "<token>"` in PowerShell). A local SQLite database (`db.sqlite3`) is tracked for convenience; do not commit production data. Regenerate logos via `update_logos.py` only when assets change, and cache external responses responsibly to stay within CFBD rate limits.
