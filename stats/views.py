import datetime
import os
from django.shortcuts import render
import cfbd
from pydantic import StrictInt, StrictStr
from django.core.cache import cache
import pytz



def get_stats_player(stats_list, player_name, stat_type):
    for s in stats_list:
        if (getattr(s, "player", "").strip().upper() == player_name.strip().upper() and
                getattr(s, "statType", getattr(s, 'stat_type', "")).strip().upper() == stat_type):
            return s
    return 0.0


def get_stat_leader(stats_list, stat_type="YDS"):
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


def home(request):
    configuration = cfbd.Configuration(
        access_token=os.environ.get('BEARER_TOKEN')
    )
    overall_record = "N/A"
    conf_record = "N/A"

    with cfbd.ApiClient(configuration) as api_client:
        api_instance = cfbd.GamesApi(api_client)
        year = StrictInt(2025)
        team = StrictStr("Oklahoma")
        conference = StrictStr("SEC")
        next_game = None
        latest_victory = None
        passing_leader = None
        rushing_leader = None
        receiving_leader = None

        # ----- TEAM RECORDS -----
        try:
            api_response = api_instance.get_records(year=year, team=team, conference=conference)
            if api_response and len(api_response) > 0:
                overall = api_response[0].total
                overall_record = f"{overall.wins}-{overall.losses}"
                conference_record_obj = api_response[0].conference_games
                conf_record = f"{conference_record_obj.wins}-{conference_record_obj.losses}"
                print(f"Overall Record: {overall_record}, Conference Record: {conf_record}")
        except Exception as e:
            print(f"Error fetching data from CFBD API: {e}")

        # ----- NEXT GAME -----
        try:
            with cfbd.ApiClient(configuration) as api_client:
                games_api = cfbd.GamesApi(api_client)
                today = datetime.date.today()
                games = games_api.get_games(year=year, team=team)
                future_games = [g for g in games if hasattr(g, "start_date") and g.start_date.date() >= today]
                if future_games:
                    next_game = sorted(future_games, key=lambda g: g.start_date)[0]
                    eastern = pytz.timezone('US/Eastern')
                    local_start_date = next_game.start_date.astimezone(eastern)
                    print(f"Next Game: {next_game.away_team} at {next_game.home_team}, Date: {local_start_date}")
        except Exception as e:
            print(f"Error fetching next game from CFBD API: {e}")

        # ----- LATEST VICTORY -----
        try:
            with cfbd.ApiClient(configuration) as api_client:
                games_api = cfbd.GamesApi(api_client)
                today = datetime.date.today()
                games = games_api.get_games(year=year, team=team)
                past_games = [
                    g for g in games
                    if hasattr(g, "start_date") and g.start_date.date() < today and (
                        (g.home_team == "Oklahoma" and g.home_points > g.away_points) or
                        (g.away_team == "Oklahoma" and g.away_points > g.home_points)
                    )
                ]
                if past_games:
                    latest_victory = sorted(past_games, key=lambda g: g.start_date, reverse=True)[0]
                    print(f"Latest Victory: {latest_victory.away_team} at {latest_victory.home_team}, Date: {latest_victory.start_date}")
        except Exception as e:
            print(f"Error fetching latest victory from CFBD API: {e}")

        # ----- PLAYER STATS WITH CACHING -----
        cache_key_prefix = f"{team}-{year}"
        passing_key = f"{cache_key_prefix}-passing"
        rushing_key = f"{cache_key_prefix}-rushing"
        receiving_key = f"{cache_key_prefix}-receiving"

        passing_stats = cache.get(passing_key)
        rushing_stats = cache.get(rushing_key)
        receiving_stats = cache.get(receiving_key)

        if not all([passing_stats, rushing_stats, receiving_stats]):
            print("Cache miss — fetching player stats from CFBD API...")
            with cfbd.ApiClient(configuration) as api_client:
                player_stats_api = cfbd.StatsApi(api_client)
                passing_stats = player_stats_api.get_player_season_stats(year=year, team=team, category="passing")
                rushing_stats = player_stats_api.get_player_season_stats(year=year, team=team, category="rushing")
                receiving_stats = player_stats_api.get_player_season_stats(year=year, team=team, category="receiving")

            # Cache for 10 minutes (600 seconds)
            cache.set_many({
                passing_key: passing_stats,
                rushing_key: rushing_stats,
                receiving_key: receiving_stats
            }, timeout=600)
        else:
            print("Cache hit — using stored player stats")

        # ----- PROCESS STATS -----
        try:
            passing_leader = get_stat_leader(passing_stats, stat_type="YDS")
            rushing_leader = get_stat_leader(rushing_stats, stat_type="YDS")
            receiving_leader = get_stat_leader(receiving_stats, stat_type="YDS")

            passing_tds = get_stats_player(passing_stats, passing_leader.player, "TD")
            rushing_tds = get_stats_player(rushing_stats, rushing_leader.player, "TD")
            receiving_tds = get_stats_player(receiving_stats, receiving_leader.player, "TD")

        except Exception as e:
            print(f"Error processing player stats: {e}")

        # ----- SEASON SCHEDULE WITH RESULTS -----
        try:
            with cfbd.ApiClient(configuration) as api_client:
                games_api = cfbd.GamesApi(api_client)
                games = games_api.get_games(year=year, team=team)
                schedule = []

                for g in sorted(games, key=lambda x: x.start_date):
                    if g.home_team == "Oklahoma":
                        opponent = g.away_team
                        is_home = True
                        score_display = f"{g.home_points} - {g.away_points}" if g.home_points is not None else "TBD"
                        if g.home_points is not None and g.away_points is not None:
                            if g.home_points > g.away_points:
                                result = "W"
                            elif g.home_points < g.away_points:
                                result = "L"
                            else:
                                result = ""
                        else:
                            result = ""
                    else:
                        opponent = g.home_team
                        is_home = False
                        score_display = f"{g.away_points} - {g.home_points}" if g.away_points is not None else "TBD"
                        if g.home_points is not None and g.away_points is not None:
                            if g.away_points > g.home_points:
                                result = "W"
                            elif g.away_points < g.home_points:
                                result = "L"
                            else:
                                result = ""
                        else:
                            result = ""

                    # Debugging output
                    print(
                        f"Game: {g.away_team} at {g.home_team} | "
                        f"HomePts={g.home_points}, AwayPts={g.away_points} | "
                        f"Oklahoma is {'home' if is_home else 'away'} | "
                        f"Computed result='{result}'"
                    )

                    schedule.append({
                        "date": g.start_date,
                        "opponent": opponent,
                        "location": "Home" if is_home else "Away",
                        "score": score_display,
                        "result": result
                    })
        except Exception as e:
            print(f"Error fetching season schedule: {e}")
            schedule = []

    # ----- CONTEXT -----
    context = {
        'title': f"Oklahoma Football - Season Record: {overall_record}, Conference Record: {conf_record}",
        'message': "Welcome to the Oklahoma Football Dashboard!",
        'record': overall_record,
        'conference_record': conf_record,
        'next_game': next_game,
        'latest_victory': latest_victory,
        'local_start_date': local_start_date,
        'passing_leader': passing_leader,
        'rushing_leader': rushing_leader,
        'receiving_leader': receiving_leader,
        'passing_tds': passing_tds,
        'rushing_tds': rushing_tds,
        'receiving_tds': receiving_tds,
        'schedule': schedule,
    }

    return render(request, 'stats/home.html', context)
