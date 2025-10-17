import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oklahoma_dashboard.settings')
import django
django.setup()
from django.utils import timezone
from stats.models import Game, TeamStat, PlayerStat
from stats.cfb_api import prettify_stat_name
import datetime

year = 2025
today = datetime.date.today()

latest_game = (
    Game.objects.filter(
        season=year,
        home_points__isnull=False,
        away_points__isnull=False,
        date__lt=today,
    )
    .order_by("-date")
    .first()
)

if not latest_game:
    print('No latest game found')
    raise SystemExit(0)

print('Latest game:', latest_game, 'CFBD ID:', latest_game.cfbd_game_id)

# TeamStat categories
team_stats = TeamStat.objects.filter(game=latest_game)
print('\nTeamStat categories (raw -> prettified):')
for ts in team_stats:
    raw = ts.category
    pretty = prettify_stat_name(raw)
    print(f"- {raw!r} -> {pretty!r}")

# PlayerStat categories and types
player_stats = PlayerStat.objects.filter(game=latest_game)
cats = sorted(set((ps.category or 'General') for ps in player_stats))
print('\nPlayerStat categories (raw -> prettified):')
for c in cats:
    print(f"- {c!r} -> {prettify_stat_name(c)!r}")

# Example of stat types under first category
if cats:
    first = cats[0]
    types = sorted(set(ps.stat_type or 'Value' for ps in player_stats.filter(category=first)))
    print(f"\nStat types for category {first!r}:")
    for t in types:
        print(f"- {t!r} -> {prettify_stat_name(t)!r}")

