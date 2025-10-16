from django.core.management.base import BaseCommand
import os
import cfbd

from stats.cfb_api import (
    update_teams_from_conference,
    fetch_and_cache_schedule,
    get_rankings,
)


class Command(BaseCommand):
    help = "Refresh teams (conference) and schedule (with rankings) from CFBD API."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=2025, help="Season year")
        parser.add_argument("--team", type=str, default="Oklahoma", help="Team name")
        parser.add_argument("--conference", type=str, default="SEC", help="Conference code")

    def handle(self, *args, **options):
        year = options["year"]
        team = options["team"]
        conference = options["conference"]

        token = os.environ.get("BEARER_TOKEN")
        if not token:
            self.stderr.write(self.style.ERROR("BEARER_TOKEN is not set in environment."))
            return

        self.stdout.write(self.style.NOTICE(f"Refreshing data for {team} ({conference}) {year}"))

        # 1) Teams
        update_teams_from_conference(conference=conference, year=year)
        self.stdout.write(self.style.SUCCESS("Teams updated."))

        # 2) Rankings
        configuration = cfbd.Configuration(access_token=token)
        with cfbd.ApiClient(configuration) as api_client:
            rankings_api = cfbd.RankingsApi(api_client)
            rankings_map, latest_week = get_rankings(rankings_api, year)

        # 3) Schedule (idempotent)
        schedule = fetch_and_cache_schedule(year, team, rankings_map, latest_week)
        self.stdout.write(self.style.SUCCESS(f"Schedule refreshed. {len(schedule)} games cached/updated."))
