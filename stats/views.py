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
    fetch_player_stats,
    fetch_and_cache_schedule,
)
# home view
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
    schedule = fetch_and_cache_schedule(configuration, year, team, rankings_map, latest_week_with_rank)

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
    fetch_player_stats,
    fetch_and_cache_schedule,
)
# home view
def home(request):

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
    schedule = fetch_and_cache_schedule(configuration, year, team, rankings_map, latest_week_with_rank)

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

        # --- Find most recent completed game ---
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

        # --- Fetch stats using id instead of week ---
        try:
            player_stats = games_api.get_game_player_stats(id=latest_game.id)
            team_stats = games_api.get_game_team_stats(id=latest_game.id)
        except Exception as e:
            print(f"Error fetching game stats: {e}")
            return render(request, "stats/boxscore.html", {
                "title": "Error",
                "message": "Unable to retrieve game stats right now."
            })

        # --- Unpack nested objects ---
        if team_stats and hasattr(team_stats[0], "teams"):
            team_stats = team_stats[0].teams  # list of team stat entries
        if player_stats and hasattr(player_stats[0], "teams"):
            player_stats = player_stats[0].teams  # list of player stat entries

        # --- Debug info ---
        print("=== BOX SCORE DEBUG ===")
        print(f"Latest game: {latest_game.away_team} @ {latest_game.home_team}")
        print(f"Game ID: {getattr(latest_game, 'id', 'N/A')} | Year: {year}")
        print(f"Team entries: {len(team_stats) if team_stats else 0}")
        print(f"Player team entries: {len(player_stats) if player_stats else 0}")

        if team_stats:
            print("First team sample:", team_stats[0].to_dict())
        if player_stats:
            print("First player team sample:", player_stats[0].to_dict())

        # --- Flatten player stats ---
        passing_stats, rushing_stats, receiving_stats, defensive_stats = [], [], [], []

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

        # Loop deeper: team -> players -> stats
        for team_entry in player_stats:
            for player in getattr(team_entry, "players", []):
                for s in getattr(player, "stats", []):
                    bucket = classify(getattr(s, "stat_type", getattr(s, "statType", "")))
                    row = {
                        "player": getattr(player, "name", "Unknown"),
                        "stat_type": getattr(s, "stat_type", getattr(s, "statType", "")),
                        "stat": getattr(s, "stat", getattr(s, "value", "")),
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



