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

    context = {
        'title': f"Oklahoma Football - Season Record: {overall_record}, Conference Record: {conf_record}",
        'message': "Welcome to the Oklahoma Football Dashboard!",
        'record': overall_record,
        'conference_record': conf_record,
    }
    return render(request, 'stats/home.html', context)
