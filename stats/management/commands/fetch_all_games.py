"""
Management command to fetch and store all FBS games for a given year, team by team.
This populates the database with games from all teams so we can calculate accurate PPG rankings.

Usage:
  python manage.py fetch_all_games --year 2025
  python manage.py fetch_all_games --year 2025 --team "Alabama"
"""
import os
from django.core.management.base import BaseCommand
import cfbd
from stats.models import Game, Team
import time


class Command(BaseCommand):
    help = 'Fetch and store all FBS games for a given year from CFBD API (team by team)'

    # All FBS teams by conference (based on ESPN college football teams page)
    FBS_TEAMS = {
        'ACC': ['Boston College', 'Clemson', 'Duke', 'Florida State', 'Georgia Tech',
                'Louisville', 'Miami', 'North Carolina', 'NC State', 'Pittsburgh',
                'Syracuse', 'Virginia', 'Virginia Tech', 'Wake Forest', 'California', 'SMU', 'Stanford'],
        'American': ['Army', 'Charlotte', 'East Carolina', 'Florida Atlantic', 'Memphis',
                     'Navy', 'North Texas', 'Rice', 'South Florida', 'Temple', 'Tulane',
                     'Tulsa', 'UAB', 'UTSA'],
        'Big 12': ['Arizona', 'Arizona State', 'Baylor', 'BYU', 'UCF', 'Cincinnati',
                   'Colorado', 'Houston', 'Iowa State', 'Kansas', 'Kansas State',
                   'Oklahoma State', 'TCU', 'Texas Tech', 'Utah', 'West Virginia'],
        'Big Ten': ['Illinois', 'Indiana', 'Iowa', 'Maryland', 'Michigan', 'Michigan State',
                    'Minnesota', 'Nebraska', 'Northwestern', 'Ohio State', 'Penn State',
                    'Purdue', 'Rutgers', 'Wisconsin', 'Oregon', 'UCLA', 'USC', 'Washington'],
        'Conference USA': ['Florida International', 'Jacksonville State', 'Kennesaw State',
                          'Liberty', 'Louisiana Tech', 'Middle Tennessee', 'New Mexico State',
                          'Sam Houston State', 'UTEP', 'Western Kentucky'],
        'FBS Independents': ['Notre Dame', 'UConn', 'Massachusetts'],
        'Mid-American': ['Akron', 'Ball State', 'Bowling Green', 'Buffalo', 'Central Michigan',
                        'Eastern Michigan', 'Kent State', 'Miami (OH)', 'Northern Illinois',
                        'Ohio', 'Toledo', 'Western Michigan'],
        'Mountain West': ['Air Force', 'Boise State', 'Colorado State', 'Fresno State', 'Hawaii',
                         'Nevada', 'New Mexico', 'San Diego State', 'San José State', 'UNLV',
                         'Utah State', 'Wyoming'],
        'Pac-12': ['Washington State', 'Oregon State'],
        'SEC': ['Alabama', 'Arkansas', 'Auburn', 'Florida', 'Georgia', 'Kentucky',
                'LSU', 'Mississippi State', 'Missouri', 'Ole Miss', 'Oklahoma',
                'South Carolina', 'Tennessee', 'Texas', 'Texas A&M', 'Vanderbilt'],
        'Sun Belt': ['Appalachian State', 'Arkansas State', 'Coastal Carolina', 'Georgia Southern',
                     'Georgia State', 'James Madison', 'Louisiana', 'Marshall', 'Old Dominion',
                     'South Alabama', 'Southern Miss', 'Texas State', 'Troy', 'UL Monroe'],
    }

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=2025, help='Season year to fetch')
        parser.add_argument('--team', type=str, help='Fetch only one specific team')

    def handle(self, *args, **options):
        year = options['year']
        single_team = options.get('team')

        # Build flat list of all teams
        if single_team:
            teams_to_fetch = [single_team]
        else:
            teams_to_fetch = []
            for conf_teams in self.FBS_TEAMS.values():
                teams_to_fetch.extend(conf_teams)

        configuration = cfbd.Configuration(
            access_token=os.environ.get("BEARER_TOKEN")
        )

        total_created = 0
        total_updated = 0
        total_skipped = 0
        total_duplicate = 0

        with cfbd.ApiClient(configuration) as api_client:
            games_api = cfbd.GamesApi(api_client)

            for idx, team in enumerate(teams_to_fetch, 1):
                self.stdout.write(f"[{idx}/{len(teams_to_fetch)}] Fetching {team} games for {year}...")

                try:
                    # Fetch games for this team
                    games = games_api.get_games(year=year, team=team)

                    created_count = 0
                    updated_count = 0
                    skipped_count = 0
                    duplicate_count = 0

                    for g in games:
                        cfbd_id = getattr(g, 'id', None)

                        # Skip if game already exists (check by cfbd_game_id)
                        if cfbd_id and Game.objects.filter(cfbd_game_id=cfbd_id).exists():
                            duplicate_count += 1
                            continue

                        # Skip games without scores (not completed yet)
                        if g.home_points is None or g.away_points is None:
                            skipped_count += 1
                            continue

                        # Get or create team objects
                        home_team, _ = Team.objects.get_or_create(name=g.home_team)
                        away_team, _ = Team.objects.get_or_create(name=g.away_team)

                        # Set conference for teams if not already set
                        if not home_team.conference and hasattr(g, 'home_conference'):
                            home_team.conference = g.home_conference or ''
                            home_team.save()
                        if not away_team.conference and hasattr(g, 'away_conference'):
                            away_team.conference = g.away_conference or ''
                            away_team.save()

                        # Prepare game data using normalized fields only
                        defaults = {
                            'season': getattr(g, 'season', year),
                            'week': getattr(g, 'week', None),
                            'game_type': getattr(g, 'season_type', '') or '',
                            'conference_game': bool(getattr(g, 'conference_game', False)),
                            'neutral_site': bool(getattr(g, 'neutral_site', False)),
                            'home_team': home_team,
                            'away_team': away_team,
                            'home_points': g.home_points,
                            'away_points': g.away_points,
                            'venue': getattr(g, 'venue', ''),
                            'attendance': getattr(g, 'attendance', None),
                            'date': g.start_date.date() if hasattr(g, 'start_date') else None,
                            'cfbd_game_id': cfbd_id,
                        }
                        # Note: We no longer populate Oklahoma-centric fields (opponent, home_away,
                        # oklahoma_score, opponent_score, result). Use Game.get_opponent(),
                        # get_score_for_team(), etc. instead.

                        # Create game (we already checked for duplicates above)
                        try:
                            Game.objects.create(**defaults)
                            created_count += 1
                        except Exception as e:
                            # Handle unique constraint violations or other errors
                            self.stdout.write(self.style.WARNING(f"    Skip: {g.home_team} vs {g.away_team} - {str(e)[:50]}"))
                            skipped_count += 1

                    total_created += created_count
                    total_updated += updated_count
                    total_skipped += skipped_count
                    total_duplicate += duplicate_count

                    if created_count > 0 or skipped_count > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ {team}: Created {created_count}, Duplicates {duplicate_count}, Skipped {skipped_count}"
                            )
                        )

                    # Small delay between teams to avoid rate limiting
                    if idx % 10 == 0:  # Delay every 10 teams
                        time.sleep(0.5)

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {team}: Error - {str(e)}")
                    )
                    continue

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{'='*60}\n"
                    f"TOTAL SUMMARY for {year}:\n"
                    f"  - Created: {total_created}\n"
                    f"  - Duplicates (skipped): {total_duplicate}\n"
                    f"  - Skipped (incomplete/errors): {total_skipped}\n"
                    f"  - Total processed: {total_created + total_duplicate + total_skipped}\n"
                    f"{'='*60}"
                )
            )

