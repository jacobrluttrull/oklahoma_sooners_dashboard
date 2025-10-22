import os

from django.utils import timezone

from test_boxscore_prettify import today, year
from .cfb_api import (
    get_rankings,
    normalize_name,
    get_stats_player,
    get_stat_leader,
    fetch_team_record,
    fetch_next_game,
    fetch_latest_victory,
    fetch_player_stats,
    fetch_and_cache_schedule,
)


# home view
def home(request):
    year = 2025
    team = "Oklahoma"
    conference = "SEC"

    # ----- TEAM RECORDS -----
    overall_record, conf_record = fetch_team_record(year, team, conference)

    # ----- RANKINGS -----
    import cfbd
    from cfbd import RankingsApi
    configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))
    with cfbd.ApiClient(configuration) as api_client:
        rankings_api = RankingsApi(api_client)
        rankings_map, latest_week_with_rank = get_rankings(rankings_api, year)

    oklahoma_key = normalize_name("Oklahoma")
    oklahoma_rank = None
    if latest_week_with_rank and oklahoma_key in rankings_map[latest_week_with_rank]:
        oklahoma_rank = rankings_map[latest_week_with_rank][oklahoma_key]

    # ----- NEXT GAME -----
    next_game = fetch_next_game(year, team, rankings_map, latest_week_with_rank, oklahoma_rank)

    # ----- LATEST VICTORY -----
    latest_victory = fetch_latest_victory(year, team, rankings_map, latest_week_with_rank, oklahoma_rank)

    # ----- PLAYER STATS -----
    passing_stats, rushing_stats, receiving_stats = fetch_player_stats(year, team)

    passing_leader = get_stat_leader(passing_stats, stat_type="YDS")
    passing_leader_interceptions = get_stat_leader(passing_stats, stat_type="INT")
    rushing_leader = get_stat_leader(rushing_stats, stat_type="YDS")
    receiving_leader = get_stat_leader(receiving_stats, stat_type="YDS")

    passing_tds = get_stats_player(passing_stats, getattr(passing_leader, "player", ""), "TD")
    rushing_tds = get_stats_player(rushing_stats, getattr(rushing_leader, "player", ""), "TD")
    receiving_tds = get_stats_player(receiving_stats, getattr(receiving_leader, "player", ""), "TD")

    # ----- EXTRA QB STATS (rushing yards, rushing TDs, combined TDs) -----
    qb_rushing_yards = get_stats_player(rushing_stats, getattr(passing_leader, "player", ""), "YDS")
    qb_rushing_tds = get_stats_player(rushing_stats, getattr(passing_leader, "player", ""), "TD")

    # Combined TDs for QB (passing + rushing)
    qb_combined_tds = int(getattr(passing_tds, "stat", 0)) + int(getattr(qb_rushing_tds, "stat", 0))

    # ----- EXTRA RB STATS (receptions, receiving yards, receiving TDs) -----
    rb_receptions = get_stats_player(receiving_stats, getattr(rushing_leader, "player", ""), "REC")
    rb_receiving_yards = get_stats_player(receiving_stats, getattr(rushing_leader, "player", ""), "YDS")
    rb_receiving_tds = get_stats_player(receiving_stats, getattr(rushing_leader, "player", ""), "TD")

    # ----- EXTRA WR STATS (receptions) -----
    wr_receptions = get_stats_player(receiving_stats, getattr(receiving_leader, "player", ""), "REC")

    # ----- SCHEDULE -----
    schedule = fetch_and_cache_schedule(year, team, rankings_map, latest_week_with_rank)

    # Last updated based on most recently updated game row, fallback to now
    latest_game_row = Game.objects.filter(date__year=year).order_by("-last_updated").first()
    if latest_game_row:
        last_updated = latest_game_row.last_updated
    else:
        last_updated = timezone.now()

    # ----- ML PREDICTION -----
    # ----- CONTEXT -----
    context = {
        "title": f"Oklahoma Football - Season Record: {overall_record}, Conference Record: {conf_record}",
        "message": "Welcome to the Oklahoma Football Dashboard!",
        "record": overall_record,
        "conference_record": conf_record,
        "next_game": next_game,
        "latest_victory": latest_victory,
        "passing_leader": passing_leader,
        "passing_leader_interceptions": passing_leader_interceptions,
        "rushing_leader": rushing_leader,
        "receiving_leader": receiving_leader,
        "passing_tds": passing_tds,
        "rushing_tds": rushing_tds,
        "receiving_tds": receiving_tds,
        "qb_rushing_yards": qb_rushing_yards,
        "qb_rushing_tds": qb_rushing_tds,
        "qb_combined_tds": qb_combined_tds,
        "rb_receptions": rb_receptions,
        "rb_receiving_yards": rb_receiving_yards,
        "rb_receiving_tds": rb_receiving_tds,
        "wr_receptions": wr_receptions,
        "schedule": schedule,
        "last_updated": last_updated,
    }

    return render(request, "stats/home.html", context)


import datetime
from django.shortcuts import render
from .models import Game, TeamStat, PlayerStat
from .cfb_api import sync_game_stats, get_team_logo
from .cfb_api import prettify_stat_name


def boxscore(request, game_id=None):
    """Displays box score for the most recent completed game from the database (syncs if needed)."""


    if game_id:
        latest_game = Game.objects.filter(id=game_id).first()
        if not latest_game:
            return render(
                request,
                "stats/boxscore.html",
                {"title": "Game Not Found", "message": f"No game found with ID {game_id}."},
            )
    else:


        # --- Get most recent completed game ---
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
        return render(
            request,
            "stats/boxscore.html",
            {"title": "No Games Available", "message": "No completed games found."},
        )

    # --- If no stats cached yet, pull from API once ---
    if not TeamStat.objects.filter(game=latest_game).exists() or not PlayerStat.objects.filter(
            game=latest_game).exists():
        print(f"📡 Syncing stats for {latest_game.cfbd_game_id}...")
        sync_game_stats(latest_game.cfbd_game_id)

    # --- Fetch from DB ---
    team_stats = TeamStat.objects.filter(game=latest_game)
    # Prettify team stat category labels for display (do not persist to DB)
    for ts in team_stats:
        ts.category = prettify_stat_name(ts.category)
    team_names = team_stats.values_list("team__name", flat=True).distinct()
    player_stats_qs = PlayerStat.objects.filter(game=latest_game).select_related('player', 'player__team')

    # Build nested structure: [{team: name, categories: [{name, types: [{name, athletes:[{name,stat}]}]}]}]
    from collections import OrderedDict
    teams_map = OrderedDict()
    for ps in player_stats_qs:
        team_name = ps.player.team.name if ps.player and ps.player.team else 'Unknown'
        team_entry = teams_map.setdefault(team_name, OrderedDict())
        cat_entry = team_entry.setdefault(ps.category or 'General', OrderedDict())
        type_list = cat_entry.setdefault(ps.stat_type or 'Value', [])
        type_list.append(ps)

    player_stats = []
    for team_name, categories in teams_map.items():
        team_obj = {'team': team_name, 'categories': []}
        for cat, types_dict in categories.items():
            cat_obj = {'name': prettify_stat_name(cat), 'types': []}
            # types_dict is {stat_type: [PlayerStat,...]} but our grouping used lists per stat_type key
            # However above we appended ps objects into a list keyed by stat_type via setdefault; need to regroup by stat_type
            # types_dict currently is OrderedDict where keys are stat_type and values are lists of PlayerStat
            for stat_type_name, stats_list in types_dict.items():
                type_obj = {
                    'name': prettify_stat_name(stat_type_name),
                    'athletes': [{'name': s.player.name if s.player else '', 'stat': s.stat} for s in stats_list]
                }
                cat_obj['types'].append(type_obj)
            team_obj['categories'].append(cat_obj)
        player_stats.append(team_obj)

    context = {
        "latest_game": latest_game,
        "team_stats": team_stats,
        "team_names": team_names,
        "player_stats": player_stats,
        "home_logo": get_team_logo(latest_game.home_team.name if latest_game.home_team else None),
        "away_logo": get_team_logo(latest_game.away_team.name if latest_game.away_team else None),
    }

    return render(request, "stats/boxscore.html", context)

def team_stats(request):
    """This will display the current team stats page with averages, total values, and rankings among SEC and FBS teams. """

