import datetime
import os
from django.shortcuts import render
import cfbd
from pydantic import StrictInt, StrictStr

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
        try:
            api_response = api_instance.get_records(year=year, team=team, conference=conference)
            print("The response of GamesApi->get_records:\n")
            if api_response and len(api_response) > 0:
                overall = api_response[0].total
                overall_record = f"{overall.wins}-{overall.losses}"
                conference = api_response[0].conference_games
                conf_record = f"{conference.wins}-{conference.losses}"
                print(f"Overall Record: {overall_record}, Conference Record: {conf_record}")
        except Exception as e:
            print("Error fetching data from CFBD API: %s\n" % e)
        try:
            with cfbd.ApiClient(configuration) as api_client:
                games_api = cfbd.GamesApi(api_client)
                today = datetime.date.today()
                games = games_api.get_games(year=year, team=team)
                future_games = [g for g in games if hasattr(g, "start_date") and g.start_date.date() >= today]
                if future_games:
                    next_game = sorted(future_games, key=lambda g: g.start_date)[0]
                    print(f"Next Game: {next_game.away_team} at {next_game.home_team}, Date: {next_game.start_date}")

        except Exception as e:
            print("Error fetching next game from CFBD API: %s\n" % e)
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
            print("Error fetching latest victory from CFBD API: %s\n" % e)


    context = {
        'title': f"Oklahoma Football - Season Record: {overall_record}, Conference Record: {conf_record}",
        'message': "Welcome to the Oklahoma Football Dashboard!",
        'record': overall_record,
        'conference_record': conf_record,
        'next_game': next_game,
        'latest_victory': latest_victory,
    }
    return render(request, 'stats/home.html', context)
