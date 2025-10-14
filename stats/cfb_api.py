import os
import datetime
import pytz
import cfbd
from pydantic import StrictInt, StrictStr
from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone
from .models import Game, Team


# =========================
# 🔐 CFBD CONFIGURATION
# =========================
def get_api_client():
    configuration = cfbd.Configuration(
        access_token=os.environ.get("BEARER_TOKEN")
    )
    return cfbd.ApiClient(configuration)


# =========================
# 🏈 TEAM RECORD
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
# 📅 NEXT GAME
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

            opponent_team = next_g.away_team if next_g.home_team == "Oklahoma" else next_g.home_team
            opponent_key = normalize_name(opponent_team)
            opponent_rank = None

            if rankings_map and latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
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
# 🏆 LATEST VICTORY
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
                    (g.home_team == team and g.home_points > g.away_points) or
                    (g.away_team == team and g.away_points > g.home_points)
                )
            ]

            if not past_games:
                return None

            latest = sorted(past_games, key=lambda g: g.start_date, reverse=True)[0]
            opponent_team = latest.away_team if latest.home_team == team else latest.home_team
            opponent_key = normalize_name(opponent_team)
            opponent_rank = None

            if rankings_map and latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
                opponent_rank = rankings_map[latest_week_with_rank][opponent_key]

            return {
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
# 📊 PLAYER STATS
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
# 🧩 HELPER FUNCTIONS
# =========================
def get_rankings(rankings_api, year: int):
    """Fetch and return AP Top 25 rankings by week."""
    def normalize_name(name: str) -> str:
        if not name:
            return ""
        return (
            name.upper()
            .replace(".", "")
            .replace("&", "AND")
            .replace("-", " ")
            .strip()
        )

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

    for s in filtered_stats:
        print(f"Player: {getattr(s, 'player', 'N/A')}, Stat: {s.stat}")

    leader = max(filtered_stats, key=lambda s: int(s.stat))
    print(f"Leader for {stat_type}: {getattr(leader, 'player', 'N/A')} with {leader.stat}")
    return leader

from datetime import timedelta
from django.utils import timezone
from .models import Game, Team
import cfbd

def fetch_and_cache_schedule(configuration, year, team, rankings_map, latest_week_with_rank):
    """Fetch full schedule with rankings and cache it in the DB."""
    #Check cache freshness (any OU games updated in the last 24h)
    recent_games = Game.objects.filter(date__year=year)
    if recent_games.exists():
        last_update = recent_games.order_by("-last_updated").first().last_updated
        if (timezone.now() - last_update) < timedelta(days=1):
            print("✅ Using cached schedule from database")
            schedule = []
            for g in recent_games.order_by("date"):
                opponent = g.opponent.name
                opponent_key = opponent.upper()
                opponent_rank = None
                is_ranked = False
                if latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
                    opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                    is_ranked = True

                schedule.append({
                    "date": g.date,
                    "opponent": opponent,
                    "location": "Home" if g.home_away == "H" else "Away",
                    "score": f"{g.oklahoma_score} - {g.opponent_score}" if g.oklahoma_score or g.opponent_score else "TBD",
                    "result": g.result,
                    "is_ranked": is_ranked,
                    "opponent_rank": opponent_rank,
                })
            return schedule
    print("♻️ Fetching fresh schedule from CFBD API...")
    try:
        with cfbd.ApiClient(configuration) as api_client:
            games_api = cfbd.GamesApi(api_client)
            games = games_api.get_games(year=year, team=team)

            # ✅ Clear old OU schedule before saving
            Game.objects.filter(date__year=year).delete()

            # Prepare for bulk insert
            new_games = []
            schedule = []

            for g in sorted(games, key=lambda x: x.start_date):
                if not hasattr(g, "start_date"):
                    continue  # skip incomplete data

                if g.home_team == "Oklahoma":
                    opponent_name = g.away_team
                    is_home = True
                    oklahoma_score = g.home_points or 0
                    opponent_score = g.away_points or 0
                else:
                    opponent_name = g.home_team
                    is_home = False
                    oklahoma_score = g.away_points or 0
                    opponent_score = g.home_points or 0

                result = ""
                if g.home_points is not None and g.away_points is not None:
                    result = "W" if oklahoma_score > opponent_score else "L"

                week_num = getattr(g, "week", None)
                opponent_key = opponent_name.upper()
                opponent_rank = None
                is_ranked = False
                if week_num in rankings_map and opponent_key in rankings_map[week_num]:
                    opponent_rank = rankings_map[week_num][opponent_key]
                    is_ranked = True
                elif latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
                    opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                    is_ranked = True

                # Create Team if needed
                opponent, _ = Team.objects.get_or_create(name=opponent_name)

                new_games.append(
                    Game(
                        opponent=opponent,
                        date=g.start_date.date(),
                        home_away="H" if is_home else "A",
                        oklahoma_score=oklahoma_score,
                        opponent_score=opponent_score,
                        result=result,
                        venue=getattr(g, "venue", ""),
                        attendance=getattr(g, "attendance", None),
                    )
                )

                schedule.append({
                    "date": g.start_date,
                    "opponent": opponent_name,
                    "location": "Home" if is_home else "Away",
                    "score": f"{oklahoma_score} - {opponent_score}" if g.home_points is not None else "TBD",
                    "result": result,
                    "is_ranked": is_ranked,
                    "opponent_rank": opponent_rank,
                })

            # ✅ Save all at once
            Game.objects.bulk_create(new_games)
            print(f"✅ Cached {len(new_games)} games in the database.")
            return schedule

    except Exception as e:
        print(f"⚠️ Error fetching season schedule: {e}")
        return []


