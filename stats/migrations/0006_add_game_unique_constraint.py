from django.db import migrations, models


def dedupe_games(apps, schema_editor):
    """Remove duplicate Game rows that share the same date, home_team, and away_team.
    Keep a single representative row per group. Prefer rows with a non-null cfbd_game_id.
    """
    Game = apps.get_model('stats', 'Game')
    from django.db.models import Count

    duplicates = (
        Game.objects.values('date', 'home_team_id', 'away_team_id')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
    )

    for dup in duplicates:
        date = dup['date']
        home_id = dup['home_team_id']
        away_id = dup['away_team_id']

        qs = list(Game.objects.filter(date=date, home_team_id=home_id, away_team_id=away_id))
        if len(qs) <= 1:
            continue

        # Prefer a keeper with a non-null cfbd_game_id
        keeper = None
        for obj in qs:
            if getattr(obj, 'cfbd_game_id', None) is not None:
                keeper = obj
                break

        # If none have cfbd_game_id, keep the one with smallest PK (stable)
        if keeper is None:
            keeper = sorted(qs, key=lambda o: o.pk)[0]

        # Delete all others
        for obj in qs:
            if obj.pk != keeper.pk:
                obj.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0005_player_playerstat_teamstat'),
    ]

    operations = [
        migrations.RunPython(dedupe_games, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='game',
            constraint=models.UniqueConstraint(fields=['date', 'home_team', 'away_team'], name='unique_game_date_home_away'),
        ),
    ]

