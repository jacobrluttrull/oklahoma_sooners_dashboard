from django.core.management.base import BaseCommand
from django.db import transaction
from stats.models import Team
from stats.cfb_api import ensure_team_logo


class Command(BaseCommand):
    help = "Backfill team logos from the CFBD API into the Team table. Useful after a database reset."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=2025, help="Year to use when fetching team metadata/logos from CFBD.")
        parser.add_argument("--dry-run", action="store_true", help="Run without saving updates to the DB (shows what would change).")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of teams processed (0 means all).")

    def handle(self, *args, **options):
        year = options.get("year") or 2025
        dry_run = options.get("dry_run")
        limit = options.get("limit") or 0

        qs = Team.objects.all().order_by("name")
        if limit and limit > 0:
            qs = qs[:limit]

        self.stdout.write(self.style.NOTICE(f"Starting backfill of team logos (year={year}) - dry_run={dry_run}"))

        updated = 0
        errors = 0
        for team in qs:
            try:
                if dry_run:
                    logo = ensure_team_logo(team.name, year=year)
                    self.stdout.write(f"DRY: {team.name} -> {logo}")
                else:
                    # use transaction per-team to avoid partial failures
                    with transaction.atomic():
                        logo = ensure_team_logo(team.name, year=year)
                        if logo:
                            updated += 1
                            self.stdout.write(self.style.SUCCESS(f"Updated: {team.name} -> {logo}"))
                        else:
                            self.stdout.write(self.style.WARNING(f"No logo found for: {team.name}"))
            except Exception as e:
                errors += 1
                self.stderr.write(self.style.ERROR(f"Error for {team.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Backfill complete. Updated={updated}, Errors={errors}"))

