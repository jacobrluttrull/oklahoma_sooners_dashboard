import datetime
import os
from collections import defaultdict
from datetime import timedelta
import re

import cfbd
import pytz
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q

from .models import Game, Team, TeamStat, PlayerStat, Player


SEC_TEAMS = [
    "Alabama", "Arkansas", "Auburn", "Florida", "Georgia", "Kentucky",
    "LSU", "Mississippi State", "Missouri", "Ole Miss", "Oklahoma",
    "South Carolina", "Tennessee", "Texas", "Texas A&M", "Vanderbilt"]


# =========================
# CFBD CONFIGURATION
# =========================
def get_api_client():
    """
    Creates and returns a CFBD API client with authentication.

    Returns:
        cfbd.ApiClient: Configured API client

    Raises:
        ValueError: If BEARER_TOKEN environment variable is not set
    """
    bearer_token = os.environ.get("BEARER_TOKEN")

    if not bearer_token:
        raise ValueError(
            "BEARER_TOKEN environment variable is required! "
            "Get your API key from https://collegefootballdata.com/key and set it with: "
            "setx BEARER_TOKEN \"your_token_here\" (Windows) or export BEARER_TOKEN=\"your_token_here\" (Mac/Linux)"
        )

    configuration = cfbd.Configuration(access_token=bearer_token)
    return cfbd.ApiClient(configuration)


# =========================
# NORMALIZATION
# =========================

def normalize_name(name: str) -> str:
    if not name:
        return ""
    import html
    name = html.unescape(name).upper()
    name = (
        name.replace(".", "")
        .replace("&", "AND")
        .replace("AMP;", "")
        .replace("-", " ")
        .strip()
    )
    # Fix common variations
    replacements = {
        "MISSISSIPPI ST": "MISSISSIPPI STATE",
        "S CAROLINA": "SOUTH CAROLINA",
        "OLE MISS": "MISSISSIPPI",
    }
    return replacements.get(name, name)



def prettify_stat_name(name: str) -> str:
    """
    Convert CFBD-style stat names into human-readable labels.
    Approach:
      - Tokenize the input into words/acronyms/numbers (handles camelCase, snake_case, ALLCAPS)
      - Map common abbreviations per-token (case-insensitive)
      - Join tokens with spaces and title-case where appropriate, preserving known acronyms (e.g., 'QB')
    """
    if not name:
        return ""

    s = name.strip()
    # Normalize separators
    s = s.replace('_', ' ').replace('-', ' ')

    # Tokenize: capture sequences like XML, Http, 3rd, numbers
    token_pattern = r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+"
    raw_tokens = re.findall(token_pattern, s)
    if not raw_tokens:
        raw_tokens = re.split(r"\s+", s)

    # mapping of common abbreviations -> full form (lowercase keys)
    token_map = {
        'qbr': 'QB Rating',
        'qb': 'QB',
        'td': 'Touchdown',
        'tds': 'Touchdowns',
        'int': 'Interception',
        'ints': 'Interceptions',
        'eff': 'Efficiency',
        'yds': 'Yards',
        'pct': 'Percentage',
        'avg': 'Average',
        'att': 'Attempts',
        'cmp': 'Completions',
        'comp': 'Completions',
        'fum': 'Fumbles',
        'sack': 'Sack',
        'sacks': 'Sacks',
        'fg': 'Field Goal',
        'fgm': 'Field Goals',
        'pd': 'Passes Defended',
        'tfl': 'Tackles For Loss',
        'tot': 'Total',
        'hur': 'Hurries',
        'hurr': 'Hurries',
        'hurries': 'Hurries',
        'attmpts': 'Attempts',
    }

    out_tokens = []
    i = 0
    L = len(raw_tokens)
    # Try to combine up to 3 tokens to match token_map keys (fixes splits like ['T','Ds'] -> 'tds')
    while i < L:
        matched = False
        # Look ahead up to 3 tokens
        for n in (3, 2, 1):
            if i + n <= L:
                # normalize candidate by removing non-alphanumeric characters
                candidate_norm = ''.join(re.sub(r'[^A-Za-z0-9]', '', c) for c in raw_tokens[i:i+n])
                key = candidate_norm.lower()
                if key in token_map:
                    out_tokens.append(token_map[key])
                    i += n
                    matched = True
                    break
        if matched:
            continue

        t = raw_tokens[i]
        key = t.lower()
        if key in token_map:
            out_tokens.append(token_map[key])
        elif t.isupper():
            # Preserve acronyms like QB, FG
            out_tokens.append(t)
        else:
            out_tokens.append(t.capitalize())
        i += 1

    pretty = ' '.join(out_tokens)
    # final cleanup: replace multiple spaces
    pretty = re.sub(r'\s+', ' ', pretty).strip()
    return pretty


# =========================
# TEAM RECORD
# =========================

def fetch_team_record(year=2025, team="Oklahoma", conference="SEC"):
    """Fetch the team's overall and conference record."""
    with get_api_client() as api_client:
        api = cfbd.GamesApi(api_client)
        try:
            api_response = api.get_records(year=year, team=team, conference=conference)
            if api_response and len(api_response) > 0:
                overall = api_response[0].total
                conf = api_response[0].conference_games
                overall_record = f"{overall.wins}-{overall.losses}"

                conf_record = f"{conf.wins}-{conf.losses}"
                return overall_record, conf_record
        except Exception as e:
            print(f"Error fetching team record: {e}")
    return "N/A", "N/A"


# =========================
# NEXT GAME
# =========================

def fetch_next_game(year=2025, team="Oklahoma", rankings_map=None, latest_week_with_rank=None, oklahoma_rank=None):
    """Fetch the team's next upcoming game."""
    with get_api_client() as api_client:
        api = cfbd.GamesApi(api_client)
        try:
            games = api.get_games(year=year, team=team)
            today = datetime.date.today()
            future_games = [g for g in games if hasattr(g, "start_date") and g.start_date.date() >= today]

            if not future_games:
                return None

            next_g = sorted(future_games, key=lambda g: g.start_date)[0]
            eastern = pytz.timezone("US/Eastern")
            local_start_date = next_g.start_date.astimezone(eastern)

            opponent_team = next_g.away_team if next_g.home_team == team else next_g.home_team
            opponent_key = normalize_name(opponent_team)
            opponent_rank = None

            if rankings_map and latest_week_with_rank and opponent_key in rankings_map.get(latest_week_with_rank, {}):
                opponent_rank = rankings_map[latest_week_with_rank][opponent_key]

            return {
                "away_team": next_g.away_team,
                "home_team": next_g.home_team,
                "venue": getattr(next_g, "venue", None),
                "start_date": next_g.start_date,
                "local_start_date": local_start_date,
                "oklahoma_rank": oklahoma_rank,
                "opponent_rank": opponent_rank
            }
        except Exception as e:
            print(f"Error fetching next game: {e}")
            return None


# =========================
# LATEST VICTORY
# =========================

def fetch_latest_victory(year=2025, team="Oklahoma", rankings_map=None, latest_week_with_rank=None, oklahoma_rank=None):
    """Fetch details of the team's most recent victory."""
    with get_api_client() as api_client:
        api = cfbd.GamesApi(api_client)
        try:
            today = datetime.date.today()
            games = api.get_games(year=year, team=team)
            past_games = [
                g for g in games
                if hasattr(g, "start_date") and g.start_date.date() < today and (
                    (g.home_team == team and g.home_points is not None and g.away_points is not None and g.home_points > g.away_points) or
                    (g.away_team == team and g.home_points is not None and g.away_points is not None and g.away_points > g.home_points)
                )
            ]

            if not past_games:
                return None

            latest = sorted(past_games, key=lambda g: g.start_date, reverse=True)[0]
            opponent_team = latest.away_team if latest.home_team == team else latest.home_team
            opponent_key = normalize_name(opponent_team)
            opponent_rank = None

            if rankings_map and latest_week_with_rank and opponent_key in rankings_map.get(latest_week_with_rank, {}):
                opponent_rank = rankings_map[latest_week_with_rank][opponent_key]

            # Get the game ID from the database
            from .models import Game, Team
            game_id = None
            try:
                home_team_obj = Team.objects.filter(name=latest.home_team).first()
                away_team_obj = Team.objects.filter(name=latest.away_team).first()
                if home_team_obj and away_team_obj:
                    game_obj = Game.objects.filter(
                        home_team=home_team_obj,
                        away_team=away_team_obj,
                        date=latest.start_date.date()
                    ).first()
                    if game_obj:
                        game_id = game_obj.id
            except Exception as e:
                print(f"Error getting game ID: {e}")

            return {
                "game_id": game_id,
                "away_team": latest.away_team,
                "home_team": latest.home_team,
                "away_points": latest.away_points,
                "home_points": latest.home_points,
                "venue": getattr(latest, "venue", None),
                "attendance": getattr(latest, "attendance", None),
                "start_date": latest.start_date,
                "oklahoma_rank": oklahoma_rank,
                "opponent_rank": opponent_rank
            }
        except Exception as e:
            print(f"Error fetching latest victory: {e}")
            return None


# =========================
# PLAYER STATS
# =========================

def fetch_player_stats(year=2025, team="Oklahoma"):
    """Fetch and cache player season stats for passing, rushing, and receiving."""
    cache_key_prefix = f"{team}-{year}"
    passing_key = f"{cache_key_prefix}-passing"
    rushing_key = f"{cache_key_prefix}-rushing"
    receiving_key = f"{cache_key_prefix}-receiving"

    passing_stats = cache.get(passing_key)
    rushing_stats = cache.get(rushing_key)
    receiving_stats = cache.get(receiving_key)

    if not all([passing_stats, rushing_stats, receiving_stats]):
        print("Cache miss — fetching player stats...")
        with get_api_client() as api_client:
            api = cfbd.StatsApi(api_client)
            passing_stats = api.get_player_season_stats(year=year, team=team, category="passing")
            rushing_stats = api.get_player_season_stats(year=year, team=team, category="rushing")
            receiving_stats = api.get_player_season_stats(year=year, team=team, category="receiving")

        cache.set_many({
            passing_key: passing_stats,
            rushing_key: rushing_stats,
            receiving_key: receiving_stats
        }, timeout=600)
    else:
        print("Cache hit — using stored stats")

    return passing_stats, rushing_stats, receiving_stats


# =========================
# HELPER FUNCTIONS
# =========================

def get_rankings(rankings_api, year: int):
    """Fetch and return AP Top 25 rankings by week."""
    all_rankings = rankings_api.get_rankings(year=year)
    rankings_map = {}

    for week_obj in all_rankings:
        week_num = week_obj.week
        for poll in week_obj.polls:
            if poll.poll == "AP Top 25":
                for r in poll.ranks:
                    school = getattr(r, "school", None)
                    rank_number = getattr(r, "rank", None)
                    if school and rank_number is not None:
                        rankings_map.setdefault(week_num, {})[normalize_name(school)] = rank_number

    latest_week_with_rank = max(rankings_map.keys()) if rankings_map else None
    return rankings_map, latest_week_with_rank


def get_stats_player(stats_list, player_name, stat_type):
    """Retrieve a specific player's stat from a stat list."""
    for s in stats_list:
        if (getattr(s, "player", "").strip().upper() == player_name.strip().upper() and
                getattr(s, "statType", getattr(s, 'stat_type', "")).strip().upper() == stat_type):
            return s
    return 0.0


def get_stat_leader(stats_list, stat_type="YDS"):
    """Find the player with the highest given stat."""
    filtered_stats = [
        s for s in stats_list
        if getattr(s, "statType", getattr(s, 'stat_type', "")).strip().upper() == stat_type
    ]
    if not filtered_stats:
        return None

    leader = max(filtered_stats, key=lambda s: int(s.stat))
    return leader


def update_teams_from_conference(conference: str, year: int = 2025):
    """Fetch and store team info including logo URLs for a conference."""
    configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
    with cfbd.ApiClient(configuration) as api_client:
        teams_api = cfbd.TeamsApi(api_client)
        teams = teams_api.get_teams(conference=conference, year=year)
        for t in teams:
            team, created = Team.objects.get_or_create(name=t.school)

            team.abbreviation = getattr(t, 'abbreviation', None)
            team.conference = getattr(t, 'conference', '') or ''
            team.color = getattr(t, "color", None)
            team.alternate_color = getattr(t, "alternateColor", None)
            team.cfbd_team_id = getattr(t, 'id', None)

            logos = getattr(t, "logos", [])
            if logos and len(logos) > 0:
                team.logo_url = logos[0].replace("http://", "https://")
            else:
                team.logo_url = ""

            team.save()
            print(f"{'Created' if created else 'Updated'}: {team.name} → {team.logo_url or 'No logo'}")


def ensure_team_logo(team_name: str, year: int = 2025):
    """Ensure we have a logo_url for a team: check DB, otherwise fetch from CFBD and cache it.

    Returns the logo URL if found, otherwise None.
    """
    if not team_name:
        return None

    try:
        # Try to find an existing Team DB entry first
        team_obj = Team.objects.filter(name__iexact=team_name).first() or Team.objects.filter(abbreviation__iexact=team_name).first()
        if team_obj and team_obj.logo_url:
            return team_obj.logo_url

        # Fetch list of teams from CFBD and try to match
        with get_api_client() as api_client:
            teams_api = cfbd.TeamsApi(api_client)
            api_teams = teams_api.get_teams(year=year)

        target_norm = normalize_name(team_name)
        match = None
        for t in api_teams:
            school = getattr(t, 'school', '')
            if not school:
                continue
            if normalize_name(school) == target_norm:
                match = t
                break
            # also check abbreviation match
            abb = getattr(t, 'abbreviation', None)
            if abb and abb.strip().upper() == team_name.strip().upper():
                match = t
                break

        # fallback: substring match
        if not match:
            for t in api_teams:
                school = getattr(t, 'school', '')
                if not school:
                    continue
                if target_norm in normalize_name(school):
                    match = t
                    break

        if match:
            # Create or update Team DB record
            team_db, created = Team.objects.get_or_create(name=match.school)
            team_db.abbreviation = getattr(match, 'abbreviation', None) or team_db.abbreviation
            team_db.conference = getattr(match, 'conference', '') or team_db.conference
            team_db.color = getattr(match, 'color', None) or team_db.color
            team_db.alternate_color = getattr(match, 'alternateColor', None) or team_db.alternate_color
            team_db.cfbd_team_id = getattr(match, 'id', None) or team_db.cfbd_team_id

            logos = getattr(match, 'logos', []) or []
            if logos and len(logos) > 0:
                team_db.logo_url = logos[0].replace("http://", "https://")
            else:
                # keep any existing value or empty string
                team_db.logo_url = team_db.logo_url or ""

            team_db.save()
            return team_db.logo_url or None

    except Exception as e:
        print(f"Error ensuring team logo for '{team_name}': {e}")

    # Last-resort: if we had a team_obj earlier, return whatever it had
    try:
        team_obj = Team.objects.filter(name__iexact=team_name).first() or Team.objects.filter(abbreviation__iexact=team_name).first()
        return team_obj.logo_url if team_obj else None
    except Exception:
        return None


def get_team_logo(team_name_or_obj):
    """Return a team's logo URL.

    Accepts either a Team model instance or a team-name string. If no logo is found in the DB
    this will attempt to fetch it from the CFBD API and cache it in the Team table.
    """
    if not team_name_or_obj:
        return None

    # If a Team object was passed, use it directly
    if isinstance(team_name_or_obj, Team):
        if team_name_or_obj.logo_url:
            return team_name_or_obj.logo_url
        # try to ensure a logo for this team
        return ensure_team_logo(team_name_or_obj.name)

    # Otherwise assume it's a string name/abbreviation
    name = str(team_name_or_obj)
    team_obj = Team.objects.filter(name__iexact=name).first() or Team.objects.filter(abbreviation__iexact=name).first()
    if team_obj and team_obj.logo_url:
        return team_obj.logo_url

    # Attempt to fetch/cache from CFBD and return result
    return ensure_team_logo(name)


def fetch_and_cache_schedule(year, team, rankings_map, latest_week_with_rank):
    """
    Fetch full schedule for a team and cache it in the DB idempotently.
    Will skip re-fetching if last update < 24 hours ago.

    `team` may be a Team instance, a team name/abbreviation string, or a numeric CFBD team id.
    """

    # Resolve the `team` argument to a Team DB object when possible to filter by FK.
    team_obj = None
    try:
        # If user passed an integer or numeric string, try to match cfbd_team_id
        if isinstance(team, int) or (isinstance(team, str) and team.isdigit()):
            team_id = int(team)
            team_obj = Team.objects.filter(cfbd_team_id=team_id).first()
    except Exception:
        team_obj = None

    if not team_obj and isinstance(team, str):
        # Try matching by name or abbreviation (case-insensitive)
        team_obj = Team.objects.filter(name__iexact=team).first() or Team.objects.filter(abbreviation__iexact=team).first()

    # --- Check cache freshness (games for the requested team updated in the last 24h) ---
    if team_obj:
        recent_games = Game.objects.filter(date__year=year).filter(
            Q(home_team=team_obj) | Q(away_team=team_obj)
        )
    else:
        # Fallback to name-based filtering if we couldn't resolve a Team object
        recent_games = Game.objects.filter(date__year=year).filter(
            Q(home_team__name__iexact=team) | Q(away_team__name__iexact=team)
        )

    if recent_games.exists():
        last_update = recent_games.order_by("-last_updated").first().last_updated
        if (timezone.now() - last_update) < timedelta(days=1):
            print("Using cached schedule from database")

            # Determine team name string for helper methods
            team_name = team_obj.name if team_obj else team

            schedule = []
            for g in recent_games.order_by("date"):
                # Use helper methods to get opponent and scores
                opponent_obj = g.get_opponent(team_name)
                if not opponent_obj:
                    continue  # Skip if this game doesn't involve the requested team

                opponent = opponent_obj.name
                opponent_key = normalize_name(opponent)
                opponent_rank = None
                is_ranked = False
                if latest_week_with_rank and opponent_key in rankings_map.get(latest_week_with_rank, {}):
                    opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                    is_ranked = True

                team_score = g.get_score_for_team(team_name)
                opponent_score = g.get_score_for_team(opponent)
                score_str = (
                    f"{team_score} - {opponent_score}"
                    if team_score is not None and opponent_score is not None
                    else "TBD"
                )

                location = g.get_location_for_team(team_name)
                location_display = "Home" if location == "H" else ("Neutral" if location == "N" else "Away")

                result = g.get_result_for_team(team_name) or ""

                schedule.append({
                    "id": g.id,
                    "date": g.date,
                    "opponent": opponent,
                    "location": location_display,
                    "score": score_str,
                    "result": result,
                    "is_ranked": is_ranked,
                    "opponent_rank": opponent_rank,
                })

            return schedule

    # --- Otherwise, fetch fresh data ---
    print("Fetching fresh schedule from CFBD API...")

    try:
        with get_api_client() as api_client:
            games_api = cfbd.GamesApi(api_client)
            games = games_api.get_games(year=year, team=team)

            seen = set()  # prevent duplicates
            schedule = []

            for g in sorted(games, key=lambda x: getattr(x, "start_date", None) or timezone.now()):
                if not hasattr(g, "start_date"):
                    continue  # skip incomplete data

                # Create a unique key to skip duplicates (e.g., duplicate game_id or postseason variant)
                key = (g.start_date.date(), g.home_team, g.away_team)
                if key in seen:
                    continue
                seen.add(key)

                # Ensure Team records exist for both sides
                home_team_obj, _ = Team.objects.get_or_create(name=g.home_team)
                away_team_obj, _ = Team.objects.get_or_create(name=g.away_team)

                # Store game using normalized fields only
                cfbd_id = getattr(g, "id", None)
                defaults = {
                    'season': getattr(g, 'season', None),
                    'week': getattr(g, 'week', None),
                    'game_type': getattr(g, 'season_type', '') or '',
                    'conference_game': bool(getattr(g, 'conference_game', False)),
                    'neutral_site': bool(getattr(g, 'neutral_site', False)),
                    'home_team': home_team_obj,
                    'away_team': away_team_obj,
                    'home_points': getattr(g, 'home_points', None),
                    'away_points': getattr(g, 'away_points', None),
                    'venue': getattr(g, 'venue', ''),
                    'attendance': getattr(g, 'attendance', None),
                    'date': g.start_date.date(),
                }

                lookup = {'cfbd_game_id': cfbd_id} if cfbd_id else {
                    'date': g.start_date.date(),
                    'home_team': home_team_obj,
                    'away_team': away_team_obj,
                }

                game, _ = Game.objects.update_or_create(defaults=defaults, **lookup)

                # Determine team name string for helper methods
                team_name = team_obj.name if team_obj else team

                # Use helper methods to build schedule entry
                opponent_obj = game.get_opponent(team_name)
                if not opponent_obj:
                    continue  # Skip if this game doesn't involve the requested team

                opponent_name = opponent_obj.name
                opponent_key = normalize_name(opponent_name)

                # Determine ranking info
                week_num = getattr(g, "week", None)
                opponent_rank = None
                is_ranked = False
                if week_num in rankings_map and opponent_key in rankings_map[week_num]:
                    opponent_rank = rankings_map[week_num][opponent_key]
                    is_ranked = True
                elif latest_week_with_rank and opponent_key in rankings_map.get(latest_week_with_rank, {}):
                    opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                    is_ranked = True

                team_score = game.get_score_for_team(team_name)
                opponent_score = game.get_score_for_team(opponent_name)
                score_str = (
                    f"{team_score} - {opponent_score}"
                    if team_score is not None and opponent_score is not None
                    else "TBD"
                )

                location = game.get_location_for_team(team_name)
                location_display = "Home" if location == "H" else ("Neutral" if location == "N" else "Away")

                result = game.get_result_for_team(team_name) or ""

                schedule.append({
                    "id": game.id,
                    "date": g.start_date,
                    "opponent": opponent_name,
                    "location": location_display,
                    "score": score_str,
                    "result": result,
                    "is_ranked": is_ranked,
                    "opponent_rank": opponent_rank,
                })

            print(f"Cached/updated {len(schedule)} games in the database (deduplicated).")
            return schedule

    except Exception as e:
        print(f"Error fetching season schedule: {e}")
        return []

def sync_game_stats(game_id: int):
    """Fetch team/player stats from CFBD API and store them in TeamStat and PlayerStat models."""
    configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
    with cfbd.ApiClient(configuration) as api_client:
        games_api = cfbd.GamesApi(api_client)

        # Fetch stats
        game_stats = games_api.get_game_team_stats(id=game_id)
        player_stats = games_api.get_game_player_stats(id=game_id)

        try:
            game_obj = Game.objects.get(cfbd_game_id=game_id)
        except Game.DoesNotExist:
            print(f"Game with CFBD ID {game_id} does not exist in the database.")
            return

        # TEAM STATS
        if game_stats and hasattr(game_stats[0], "teams"):
            for team_entry in game_stats[0].teams:
                team_obj, _ = Team.objects.get_or_create(name=team_entry.team)
                for stat in team_entry.stats:
                    TeamStat.objects.update_or_create(
                        game=game_obj,
                        team=team_obj,
                        category=prettify_stat_name(stat.category),
                        defaults={'stat': stat.stat}
                    )

        # PLAYER STATS
        if player_stats and hasattr(player_stats[0], "teams"):
            for team_entry in player_stats[0].teams:
                team_obj, _ = Team.objects.get_or_create(name=team_entry.team)
                for category in team_entry.categories:
                    for stat_type in category.types:
                        for athlete in stat_type.athletes:
                            player_obj, _ = Player.objects.get_or_create(
                                team=team_obj,
                                name=athlete.name,
                                defaults={'cfbd_player_id': getattr(athlete, 'id', None)},
                            )
                            PlayerStat.objects.update_or_create(
                                game=game_obj,
                                player=player_obj,
                                category=category.name,
                                stat_type=stat_type.name,
                                defaults={'stat': athlete.stat},
                            )

        print(f"Game stats synchronized successfully for {game_obj}")
# ====== TEAM STATS ======
def get_team_season_stats(year=2025, team="Oklahoma"):
    """Fetch and cache total season team stats"""
    with get_api_client() as api_client:
        api = cfbd.StatsApi(api_client)
        try:
            team_stats = api.get_team_stats(year=year, team=team)

            return team_stats
        except Exception as e:
            print(f"Error fetching team season stats: {e}")
            return []




def get_team_ppg(year=2025, conference="SEC"):
    """
    Fetch and cache SEC teams' average points per game (PPG) for a given year.
    Only includes SEC teams. Cached for 1 hour.
    """
    cache_key = f"{conference}-{year}-ppg"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    team_stats = defaultdict(lambda: {'points_per_game': 0.0, 'games_played': 0})

    with get_api_client() as api_client:
        api = cfbd.GamesApi(api_client)
        games = api.get_games(year=year, conference=conference)

        for g in games:
            if not g.completed:
                continue

            home_team = g.home_team
            away_team = g.away_team
            home_points = float(g.home_points or 0)
            away_points = float(g.away_points or 0)

            # Only SEC teams get counted
            if home_team in SEC_TEAMS:
                team_stats[home_team]['points_per_game'] += home_points
                team_stats[home_team]['games_played'] += 1

            if away_team in SEC_TEAMS:
                team_stats[away_team]['points_per_game'] += away_points
                team_stats[away_team]['games_played'] += 1

    # Compute averages using correct keys
    sec_team_ppg = {
        team: (data["points_per_game"] / data["games_played"])
        for team, data in team_stats.items()
        if data["games_played"] > 0 and team in SEC_TEAMS
    }

    # Cache for 1 hour
    cache.set(cache_key, sec_team_ppg, timeout=3600)
    return sec_team_ppg



def fetch_conference_standings(year=2025, conference="SEC"):
    """Fetch conference standings by querying records for all teams in the conference."""

    # SEC teams (2024-2025 lineup)
    sec_teams = [
        "Alabama", "Arkansas", "Auburn", "Florida", "Georgia", "Kentucky",
        "LSU", "Mississippi State", "Missouri", "Ole Miss", "Oklahoma",
        "South Carolina", "Tennessee", "Texas", "Texas A&M", "Vanderbilt"
    ]

    standings = []

    for team in sec_teams:
        streak_str = '0'
        try:
            with get_api_client() as api_client:
                api = cfbd.GamesApi(api_client)
                api_response = api.get_records(year=year, team=team, conference=conference)

                overall = None
                conf = None
                if api_response and len(api_response) > 0:
                    record = api_response[0]
                    overall = record.total
                    conf = record.conference_games

                # fetch past games for streak calculation
                try:
                    games = api.get_games(year=year, team=team)
                    past_games = [
                        g for g in games
                        if hasattr(g, "start_date") and g.start_date.date() < datetime.date.today()
                        and getattr(g, "home_points", None) is not None and getattr(g, "away_points", None) is not None
                    ]
                    past_games = sorted(past_games, key=lambda g: g.start_date, reverse=True)

                    if past_games:
                        streak_count = 0
                        streak_type = None
                        for g in past_games:
                            is_win = (
                                (g.home_team == team and (g.home_points or 0) > (g.away_points or 0)) or
                                (g.away_team == team and (g.away_points or 0) > (g.home_points or 0))
                            )
                            result = 'W' if is_win else 'L'
                            if streak_type is None:
                                streak_type = result
                                streak_count = 1
                            elif result == streak_type:
                                streak_count += 1
                            else:
                                break
                        if streak_type:
                            streak_str = f"{streak_type}{streak_count}"
                except Exception as e:
                    # non-fatal: if streak calc fails, leave streak_str as default and continue
                    print(f"Error fetching games for streak calculation for {team}: {e}")

                # Build the standings entry (fall back to zeros if API didn't return records)
                standings.append({
                    'team': team,
                    'conference_wins': conf.wins or 0 if conf else 0,
                    'conference_losses': conf.losses or 0 if conf else 0,
                    'total_wins': overall.wins or 0 if overall else 0,
                    'total_losses': overall.losses or 0 if overall else 0,
                    'conference_win_pct': (conf.wins / (conf.wins + conf.losses)) if (conf and (conf.wins + conf.losses) > 0) else 0,
                    'overall_win_pct': (overall.wins / (overall.wins + overall.losses)) if (overall and (overall.wins + overall.losses) > 0) else 0,
                    'streak': streak_str,
                })
        except Exception as e:
            print(f"Error fetching record for {team}: {e}")
            standings.append({
                'team': team,
                'conference_wins': 0,
                'conference_losses': 0,
                'total_wins': 0,
                'total_losses': 0,
                'conference_win_pct': 0,
                'overall_win_pct': 0,
                'streak': '0',
            })

    # Sort by: conference wins (desc), conference losses (asc), total wins (desc), team name (asc)
    standings.sort(key=lambda x: (-x['conference_wins'], x['conference_losses'], -x['total_wins'], x['team']))

    # Calculate positions with ties based ONLY on conference record

    for i, entry in enumerate(standings):
        if i == 0:
            entry['position'] = 1
            entry['tied'] = False
        else:
            prev = standings[i - 1]
            # Check if tied - ONLY based on conference record
            if (entry['conference_wins'] == prev['conference_wins'] and
                entry['conference_losses'] == prev['conference_losses']):
                entry['position'] = prev['position']
                entry['tied'] = True
                prev['tied'] = True  # Mark previous as tied too
            else:
                current_rank = i + 1
                entry['position'] = current_rank
                entry['tied'] = False

    return standings

