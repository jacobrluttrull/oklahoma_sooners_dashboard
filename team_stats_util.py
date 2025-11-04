from django.db.models import Avg
from stats.models import Game, TeamStat

def get_oklahoma_ppg():
    """
    only includes completed games and returns only Oklahoma's ppg
    :return:
    """
    games= Game.objects.filter(
        oklahoma_score__isnull=False,
        opponent_score__isnull=False
    )
    games_played = games.count()
    if games_played == 0:
        return 0.0
    total_points = sum(g.oklahoma_score for g in games)
    avg_ppg = total_points / games_played
    return round(avg_ppg, 1), total_points
