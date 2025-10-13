import datetime
import os
from django.shortcuts import render
import cfbd
from pydantic import StrictInt, StrictStr
from django.core.cache import cache
import pytz



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

        # ----- GET AP RANKINGS -----
        with cfbd.ApiClient(configuration) as api_client:
            rankings_api = cfbd.RankingsApi(api_client)
            rankings_map, latest_week_with_rank = get_rankings(rankings_api, year)

        oklahoma_key = normalize_name("Oklahoma")
        if latest_week_with_rank and oklahoma_key in rankings_map[latest_week_with_rank]:
            oklahoma_rank = rankings_map[latest_week_with_rank][oklahoma_key]
        else:
            oklahoma_rank = None

        # ----- NEXT GAME -----
        try:
            with cfbd.ApiClient(configuration) as api_client:
                games_api = cfbd.GamesApi(api_client)
                today = datetime.date.today()
                games = games_api.get_games(year=year, team=team)
                future_games = [g for g in games if hasattr(g, "start_date") and g.start_date.date() >= today]

                if future_games:
                    next_g = sorted(future_games, key=lambda g: g.start_date)[0]
                    eastern = pytz.timezone('US/Eastern')
                    local_start_date = next_g.start_date.astimezone(eastern)

                    # Add opponent and OU ranks
                    opponent_team = next_g.away_team if next_g.home_team == "Oklahoma" else next_g.home_team
                    opponent_key = normalize_name(opponent_team)
                    opponent_rank = None
                    if latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
                        opponent_rank = rankings_map[latest_week_with_rank][opponent_key]

                    # Wrap next_game into a dict (instead of mutating CFBD object)
                    next_game = {
                        "away_team": next_g.away_team,
                        "home_team": next_g.home_team,
                        "venue": getattr(next_g, "venue", None),
                        "start_date": next_g.start_date,
                        "local_start_date": local_start_date,
                        "oklahoma_rank": oklahoma_rank,
                        "opponent_rank": opponent_rank
                    }

                    print(f"Next Game: {next_g.away_team} at {next_g.home_team}, Date: {local_start_date}, "
                          f"OU Rank: {oklahoma_rank}, Opp Rank: {opponent_rank}")
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
                    latest_victory_obj = sorted(past_games, key=lambda g: g.start_date, reverse=True)[0]

                    opponent_team = (
                        latest_victory_obj.away_team
                        if latest_victory_obj.home_team == "Oklahoma"
                        else latest_victory_obj.home_team
                    )
                    opponent_key = normalize_name(opponent_team)
                    opponent_rank = None
                    if latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
                        opponent_rank = rankings_map[latest_week_with_rank][opponent_key]

                    latest_victory = {
                        "away_team": latest_victory_obj.away_team,
                        "home_team": latest_victory_obj.home_team,
                        "away_points": latest_victory_obj.away_points,
                        "home_points": latest_victory_obj.home_points,
                        "venue": getattr(latest_victory_obj, "venue", None),
                        "attendance": getattr(latest_victory_obj, "attendance", None),
                        "start_date": latest_victory_obj.start_date,
                        "oklahoma_rank": oklahoma_rank,
                        "opponent_rank": opponent_rank
                    }

                    print(f"Latest Victory: {latest_victory['away_team']} at {latest_victory['home_team']}, "
                          f"OU Rank: {oklahoma_rank}, Opp Rank: {opponent_rank}")
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

            cache.set_many({
                passing_key: passing_stats,
                rushing_key: rushing_stats,
                receiving_key: receiving_stats
            }, timeout=600)
        else:
            print("Cache hit — using stored player stats")

        try:
            passing_leader = get_stat_leader(passing_stats, stat_type="YDS")
            rushing_leader = get_stat_leader(rushing_stats, stat_type="YDS")
            receiving_leader = get_stat_leader(receiving_stats, stat_type="YDS")

            passing_tds = get_stats_player(passing_stats, passing_leader.player, "TD")
            rushing_tds = get_stats_player(rushing_stats, rushing_leader.player, "TD")
            receiving_tds = get_stats_player(receiving_stats, receiving_leader.player, "TD")

        except Exception as e:
            print(f"Error processing player stats: {e}")

        # ----- SEASON SCHEDULE WITH RESULTS + RANKINGS -----
        try:
            with cfbd.ApiClient(configuration) as api_client:
                games_api = cfbd.GamesApi(api_client)
                games = games_api.get_games(year=year, team=team)
                schedule = []
                ranked_wins = []

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
                    opponent_rank = None
                    is_ranked = False
                    opponent_key = normalize_name(opponent)

                    if week_num in rankings_map and opponent_key in rankings_map[week_num]:
                        opponent_rank = rankings_map[week_num][opponent_key]
                        is_ranked = True
                    elif latest_week_with_rank and opponent_key in rankings_map[latest_week_with_rank]:
                        opponent_rank = rankings_map[latest_week_with_rank][opponent_key]
                        is_ranked = True

                    print(
                        f"Week {week_num}: {g.away_team} at {g.home_team} | "
                        f"Rank: {opponent_rank if opponent_rank else 'Unranked'} | "
                        f"Result: {result}"
                    )

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

                    if is_ranked and result == "W":
                        ranked_wins.append(game_data)

        except Exception as e:
            print(f"Error fetching season schedule: {e}")
            schedule = []

    context = {
        'title': f"Oklahoma Football - Season Record: {overall_record}, Conference Record: {conf_record}",
        'message': "Welcome to the Oklahoma Football Dashboard!",
        'record': overall_record,
        'conference_record': conf_record,
        'next_game': next_game,
        'latest_victory': latest_victory,
        'passing_leader': passing_leader,
        'rushing_leader': rushing_leader,
        'receiving_leader': receiving_leader,
        'passing_tds': passing_tds,
        'rushing_tds': rushing_tds,
        'receiving_tds': receiving_tds,
        'schedule': schedule,
    }

    return render(request, 'stats/home.html', context)

def boxscore(request):
    configuration = cfbd.Configuration(access_token=os.environ.get('BEARER_TOKEN'))

    with cfbd.ApiClient(configuration) as api_client:
        games_api = cfbd.GamesApi(api_client)

        team = "Oklahoma"
        year = 2025
        today = datetime.date.today()

        # --- All OU games this year ---
        games = games_api.get_games(year=year, team=team)

        # Completed games: both scores present & in the past
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

        # Latest completed game
        latest_game = sorted(completed, key=lambda g: g.start_date, reverse=True)[0]
        opponent = latest_game.away_team if latest_game.home_team == team else latest_game.home_team
        game_week = latest_game.week

        # --- Pull player + team stats for that WEEK ---
        try:
            # Per-player rows for the week (stat_type, stat, player, etc.)
            player_stats = games_api.get_game_player_stats(year=year, week=game_week, team=team)
            # Team stat rows for the week (stat_type, stat)
            team_stats = games_api.get_game_team_stats(year=year, week=game_week, team=team)
        except Exception as e:
            print(f"Error fetching game stats: {e}")
            return render(request, "stats/boxscore.html", {
                "title": "Error",
                "message": "Unable to retrieve game stats right now."
            })

        # --- Classify player stats by stat_type ---
        def classify(stat_type: str) -> str:
            st = (stat_type or "").lower()
            # receiving first to avoid 'rec' being mistaken
            if "rec" in st:                 # rec, rec_yds, rec_td, receptions, receivingYards
                return "receiving"
            if "rush" in st:                # rush_att, rush_yds, rushingYards, rushingTDs
                return "rushing"
            if "pass" in st:                # pass_att, pass_cmp, pass_yds, passingYards, interceptions (QB stat appears as 'int' sometimes)
                return "passing"
            # crude defensive bucket
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
            # ignore "other" for now

        context = {
            "latest_game": latest_game,
            "opponent": opponent,
            "passing_stats": passing_stats,
            "rushing_stats": rushing_stats,
            "receiving_stats": receiving_stats,
            "defensive_stats": defensive_stats,
            "team_stats": team_stats,   # NOTE: these have stat_type/stat fields
        }

        return render(request, "stats/boxscore.html", context)



