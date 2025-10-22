import datetime
import os
from datetime import timedelta
import re

import cfbd
import pytz
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q

from .models import Game, Team, TeamStat, PlayerStat, Player


# =========================
# CFBD CONFIGURATION
# =========================
def get_api_client():
    configuration = cfbd.Configuration(
        access_token=os.environ.get("BEARER_TOKEN")
    )
    return cfbd.ApiClient(configuration)


# =========================
# NORMALIZATION
# =========================

def normalize_name(name: str) -> str:
    """Normalize team names to improve matching between CFBD API datasets."""
    if not name:
        return ""
    return (
        name.upper()
        .replace(".", "")
        .replace("&", "AND")
        .replace("-", " ")
        .strip()
    )


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
                candidate = ''.join(raw_tokens[i:i+n])
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


def get_team_logo(team_name: str):
    team = Team.objects.filter(name__iexact=team_name).first()
    if team and team.logo_url:
        return team.logo_url
    return None


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

            schedule = []
            for g in recent_games.order_by("date"):
                opponent = g.opponent.name
                opponent_key = normalize_name(opponent)
                opponent_rank = None
                is_ranked = False
                if latest_week_with_rank and opponent_key in rankings_map.get(latest_week_with_rank, {}):
                    opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                    is_ranked = True

                score_str = (
                    f"{g.oklahoma_score} - {g.opponent_score}"
                    if g.oklahoma_score is not None and g.opponent_score is not None
                    else "TBD"
                )

                schedule.append({
                    "id": g.id,  # Add the game ID for clickable links
                    "date": g.date,
                    "opponent": opponent,
                    "location": "Home" if g.home_away == "H" else ("Neutral" if g.home_away == "N" else "Away"),
                    "score": score_str,
                    "result": g.result,
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

                # Oklahoma-centric fields
                if g.home_team == team or (team_obj and home_team_obj == team_obj):
                    opponent_name = g.away_team
                    is_home = True
                    oklahoma_score = g.home_points
                    opponent_score = g.away_points
                else:
                    opponent_name = g.home_team
                    is_home = False
                    oklahoma_score = g.away_points
                    opponent_score = g.home_points

                # Determine W/L result
                result = ""
                if g.home_points is not None and g.away_points is not None:
                    result = "W" if (oklahoma_score or 0) > (opponent_score or 0) else "L"

                # Determine ranking info
                week_num = getattr(g, "week", None)
                opponent_key = normalize_name(opponent_name)
                opponent_rank = None
                is_ranked = False
                if week_num in rankings_map and opponent_key in rankings_map[week_num]:
                    opponent_rank = rankings_map[week_num][opponent_key]
                    is_ranked = True
                elif latest_week_with_rank and opponent_key in rankings_map.get(latest_week_with_rank, {}):
                    opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                    is_ranked = True

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
                    'home_away': 'H' if is_home else ('N' if bool(getattr(g, 'neutral_site', False)) else 'A'),
                    'oklahoma_score': oklahoma_score,
                    'opponent_score': opponent_score,
                    'result': result,
                    'opponent': away_team_obj if is_home else home_team_obj,
                    'date': g.start_date.date(),
                }

                lookup = {'cfbd_game_id': cfbd_id} if cfbd_id else {
                    'date': g.start_date.date(),
                    'home_team': home_team_obj,
                    'away_team': away_team_obj,
                }

                game, _ = Game.objects.update_or_create(defaults=defaults, **lookup)

                score_str = (
                    f"{oklahoma_score} - {opponent_score}"
                    if g.home_points is not None and g.away_points is not None
                    else "TBD"
                )

                schedule.append({
                    "id": game.id,  # Add the game ID for clickable links
                    "date": g.start_date,
                    "opponent": opponent_name,
                    "location": "Home" if is_home else ("Neutral" if bool(getattr(g, 'neutral_site', False)) else "Away"),
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



