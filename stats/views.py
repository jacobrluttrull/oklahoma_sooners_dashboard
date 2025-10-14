import datetime
from django.shortcuts import render
import os
from .cfb_api import (
    get_rankings,
    normalize_name,
    get_stats_player,
    get_stat_leader,
    fetch_team_record,
    fetch_next_game,
    fetch_latest_victory,
    fetch_player_stats
)
##home view
def home(request):
    # ----- CONFIG -----
    year = 2025
    team = "Oklahoma"
    conference = "SEC"

    # ----- TEAM RECORDS -----
    overall_record, conf_record = fetch_team_record(year, team, conference)

    # ----- RANKINGS -----
    import cfbd
    from cfbd import RankingsApi
    configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
    with cfbd.ApiClient(configuration) as api_client:
        rankings_api = RankingsApi(api_client)
        rankings_map, latest_week_with_rank = get_rankings(rankings_api, year)

    oklahoma_key = normalize_name("Oklahoma")
    oklahoma_rank = None
    if latest_week_with_rank and oklahoma_key in rankings_map[latest_week_with_rank]:
        oklahoma_rank = rankings_map[latest_week_with_rank][oklahoma_key]

    # ----- NEXT GAME -----
    next_game = fetch_next_game(year, team, rankings_map, latest_week_with_rank, oklahoma_rank)

    # ----- LATEST VICTORY -----
    latest_victory = fetch_latest_victory(year, team, rankings_map, latest_week_with_rank, oklahoma_rank)

    # ----- PLAYER STATS -----
    passing_stats, rushing_stats, receiving_stats = fetch_player_stats(year, team)

    passing_leader = get_stat_leader(passing_stats, stat_type="YDS")
    rushing_leader = get_stat_leader(rushing_stats, stat_type="YDS")
    receiving_leader = get_stat_leader(receiving_stats, stat_type="YDS")

    passing_tds = get_stats_player(passing_stats, getattr(passing_leader, "player", ""), "TD")
    rushing_tds = get_stats_player(rushing_stats, getattr(rushing_leader, "player", ""), "TD")
    receiving_tds = get_stats_player(receiving_stats, getattr(receiving_leader, "player", ""), "TD")

    # ----- SCHEDULE (inline for now) -----
    # Keeping schedule inline because it combines multiple datasets dynamically
    schedule = []
    try:
        with cfbd.ApiClient(configuration) as api_client:
            games_api = cfbd.GamesApi(api_client)
            games = games_api.get_games(year=year, team=team)
            for g in sorted(games, key=lambda x: x.start_date):
                if g.home_team == "Oklahoma":
                    opponent = g.away_team
                    is_home = True
                    score_display = f"{g.home_points} - {g.away_points}" if g.home_points is not None else "TBD"
                    result = ""
                    if g.home_points is not None and g.away_points is not None:
                        if g.home_points > g.away_points:
                            result = "W"
                        elif g.home_points < g.away_points:
                            result = "L"
                else:
                    opponent = g.home_team
                    is_home = False
                    score_display = f"{g.away_points} - {g.home_points}" if g.away_points is not None else "TBD"
                    result = ""
                    if g.home_points is not None and g.away_points is not None:
                        if g.away_points > g.home_points:
                            result = "W"
                        elif g.away_points < g.home_points:
                            result = "L"

                week_num = getattr(g, "week", None)
                opponent_key = normalize_name(opponent)
                opponent_rank = None
                is_ranked = False

                if week_num in rankings_map and opponent_key in rankings_map[week_num]:
                    opponent_rank = rankings_map[week_num][opponent_key]
                    is_ranked = True
                elif latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
                    opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                    is_ranked = True

                game_data = {
                    "date": g.start_date,
                    "opponent": opponent,
                    "location": "Home" if is_home else "Away",
                    "score": score_display,
                    "result": result,
                    "is_ranked": is_ranked,
                    "opponent_rank": opponent_rank,
                }
                schedule.append(game_data)

    except Exception as e:
        print(f"Error fetching season schedule: {e}")

    # ----- CONTEXT -----
    context = {
        "title": f"Oklahoma Football - Season Record: {overall_record}, Conference Record: {conf_record}",
        "message": "Welcome to the Oklahoma Football Dashboard!",
        "record": overall_record,
        "conference_record": conf_record,
        "next_game": next_game,
        "latest_victory": latest_victory,
        "passing_leader": passing_leader,
        "rushing_leader": rushing_leader,
        "receiving_leader": receiving_leader,
        "passing_tds": passing_tds,
        "rushing_tds": rushing_tds,
        "receiving_tds": receiving_tds,
        "schedule": schedule,
    }

    return render(request, "stats/home.html", context)


def boxscore(request):
    """Displays box score for the most recent completed game."""
    import cfbd
    configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
    with cfbd.ApiClient(configuration) as api_client:
        games_api = cfbd.GamesApi(api_client)
        team = "Oklahoma"
        year = 2025
        today = datetime.date.today()

        # Completed games
        games = games_api.get_games(year=year, team=team)
        completed = [
            g for g in games
            if hasattr(g, "start_date") and g.start_date.date() < today
            and g.home_points is not None and g.away_points is not None
        ]
        if not completed:
            return render(request, "stats/boxscore.html", {
                "title": "No Games Available",
                "message": "No completed games found for this season."
            })

        latest_game = sorted(completed, key=lambda g: g.start_date, reverse=True)[0]
        opponent = latest_game.away_team if latest_game.home_team == team else latest_game.home_team
        game_week = latest_game.week

        try:
            player_stats = games_api.get_game_player_stats(year=year, week=game_week, team=team)
            team_stats = games_api.get_game_team_stats(year=year, week=game_week, team=team)
        except Exception as e:
            print(f"Error fetching game stats: {e}")
            return render(request, "stats/boxscore.html", {
                "title": "Error",
                "message": "Unable to retrieve game stats right now."
            })

        # --- Classify player stats ---
        def classify(stat_type: str) -> str:
            st = (stat_type or "").lower()
            if "rec" in st:
                return "receiving"
            if "rush" in st:
                return "rushing"
            if "pass" in st:
                return "passing"
            if any(x in st for x in ["tackle", "sack", "tfl", "int", "ff", "fr", "qb_hurry", "deflect", "pd"]):
                return "defensive"
            return "other"

        passing_stats, rushing_stats, receiving_stats, defensive_stats = [], [], [], []

        for s in player_stats:
            bucket = classify(getattr(s, "stat_type", ""))
            row = {
                "player": getattr(s, "player", "Unknown"),
                "stat_type": getattr(s, "stat_type", ""),
                "stat": getattr(s, "stat", ""),
            }
            if bucket == "passing":
                passing_stats.append(row)
            elif bucket == "rushing":
                rushing_stats.append(row)
            elif bucket == "receiving":
                receiving_stats.append(row)
            elif bucket == "defensive":
                defensive_stats.append(row)

        context = {
            "latest_game": latest_game,
            "opponent": opponent,
            "passing_stats": passing_stats,
            "rushing_stats": rushing_stats,
            "receiving_stats": receiving_stats,
            "defensive_stats": defensive_stats,
            "team_stats": team_stats,
        }

        return render(request, "stats/boxscore.html", context)
