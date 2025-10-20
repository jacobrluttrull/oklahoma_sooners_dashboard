#!/usr/bin/env python
"""Script to update team logos for all teams in the database."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oklahoma_dashboard.settings')
django.setup()

from stats.models import Team
from stats.cfb_api import update_teams_from_conference

# Check teams without logos
teams_without_logos = Team.objects.filter(logo_url__isnull=True) | Team.objects.filter(logo_url='')
print(f"Teams without logos: {teams_without_logos.count()}")
for t in teams_without_logos:
    print(f"  - {t.name}")

# Get all unique conferences from teams
conferences = Team.objects.exclude(conference__isnull=True).exclude(conference='').values_list('conference', flat=True).distinct()
print(f"\nFound conferences: {list(conferences)}")

# Update logos for all conferences
print("\nUpdating team logos from CFBD API...")
for conf in conferences:
    if conf:
        print(f"\nUpdating {conf}...")
        try:
            update_teams_from_conference(conf, year=2025)
        except Exception as e:
            print(f"Error updating {conf}: {e}")

# Also update teams that played Oklahoma but aren't in conferences yet
print("\n\nUpdating teams from games...")
from stats.models import Game
all_teams = set()
games = Game.objects.all()
for game in games:
    if game.home_team:
        all_teams.add(game.home_team.name)
    if game.away_team:
        all_teams.add(game.away_team.name)

print(f"Found {len(all_teams)} unique teams from games")

# Try to fetch logos for teams without conference info
import cfbd
configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
with cfbd.ApiClient(configuration) as api_client:
    teams_api = cfbd.TeamsApi(api_client)
    for team_name in all_teams:
        team_obj = Team.objects.filter(name=team_name).first()
        if team_obj and (not team_obj.logo_url or team_obj.logo_url == ''):
            print(f"Fetching logo for {team_name}...")
            try:
                # Try to get team info
                teams = teams_api.get_teams(year=2025)
                for t in teams:
                    if t.school == team_name:
                        logos = getattr(t, "logos", [])
                        if logos and len(logos) > 0:
                            team_obj.logo_url = logos[0].replace("http://", "https://")
                            team_obj.conference = getattr(t, 'conference', '') or ''
                            team_obj.abbreviation = getattr(t, 'abbreviation', None)
                            team_obj.color = getattr(t, "color", None)
                            team_obj.alternate_color = getattr(t, "alternateColor", None)
                            team_obj.cfbd_team_id = getattr(t, 'id', None)
                            team_obj.save()
                            print(f"  ✓ Updated {team_name} with logo")
                            break
            except Exception as e:
                print(f"  ✗ Error fetching {team_name}: {e}")

print("\n✓ Logo update complete!")

# Final check
teams_without_logos = Team.objects.filter(logo_url__isnull=True) | Team.objects.filter(logo_url='')
print(f"\nTeams still without logos: {teams_without_logos.count()}")
for t in teams_without_logos:
    print(f"  - {t.name}")

