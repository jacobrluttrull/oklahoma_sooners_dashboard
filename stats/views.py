import os
from datetime import date

from django.utils import timezone

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
    ensure_team_logo, fetch_conference_standings,
    get_team_ppg# added: ensure logos are fetched when missing
)
from team_stats_util import get_oklahoma_ppg


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

    # Ensure logos for schedule opponents are present (backfill if DB was rebuilt)
    try:
        for entry in schedule or []:
            opp = entry.get('opponent') if isinstance(entry, dict) else None
            if opp:
                ensure_team_logo(opp, year=year)
    except Exception as e:
        print(f"Warning while ensuring schedule logos: {e}")

    # Ensure logos for next game and latest victory as well
    try:
        if next_game:
            ensure_team_logo(next_game.get('away_team') or next_game.get('away_team_name') if isinstance(next_game, dict) else getattr(next_game, 'away_team', None), year=year)
            ensure_team_logo(next_game.get('home_team') or next_game.get('home_team_name') if isinstance(next_game, dict) else getattr(next_game, 'home_team', None), year=year)
    except Exception:
        pass

    try:
        if latest_victory:
            ensure_team_logo(latest_victory.get('away_team') or getattr(latest_victory, 'away_team', None), year=year)
            ensure_team_logo(latest_victory.get('home_team') or getattr(latest_victory, 'home_team', None), year=year)
    except Exception:
        pass

    # Last updated based on most recently updated game row, fallback to now
    latest_game_row = Game.objects.filter(date__year=year).order_by("-last_updated").first()
    if latest_game_row:
        last_updated = latest_game_row.last_updated
    else:
        last_updated = timezone.now()


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


from django.shortcuts import render
from .models import Game, TeamStat, PlayerStat
from .cfb_api import sync_game_stats, get_team_logo
from .cfb_api import prettify_stat_name


def boxscore(request, game_id=None):
    """Displays box score for the most recent completed game from the database (syncs if needed)."""

    year = 2025
    today = date.today()

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
        print(f" Syncing stats for {latest_game.cfbd_game_id}...")
        for team_name in [latest_game.home_team, latest_game.away_team]:
            if team_name:
                # Ensure logos exist (backfill missing ones) before syncing stats
                try:
                    ensure_team_logo(team_name.name if hasattr(team_name, 'name') else team_name, year=latest_game.season)
                except Exception:
                    pass
                get_team_logo(team_name)
        sync_game_stats(latest_game.cfbd_game_id)

    # --- Fetch from DB ---
    team_stats = TeamStat.objects.filter(game=latest_game)
    # Prettify team stat category labels for display (do not persist to DB)
    for ts in team_stats:
        ts.category = prettify_stat_name(ts.category)
    team_names = team_stats.values_list("team__name", flat=True).distinct()
    player_stats_qs = PlayerStat.objects.filter(game=latest_game).select_related('player', 'player__team')

    # Build ESPN-style structure: pivot by player so all stats appear in one row
    # Structure: [{team, categories: [{name, stat_columns: [col names], players: [{name, stats: [values]}]}]}]
    from collections import OrderedDict
    teams_map = OrderedDict()

    for ps in player_stats_qs:
        team_name = ps.player.team.name if ps.player and ps.player.team else 'Unknown'
        player_name = ps.player.name if ps.player else ''
        category = ps.category or 'General'
        stat_type = ps.stat_type or 'Value'
        stat_value = ps.stat

        team_entry = teams_map.setdefault(team_name, OrderedDict())
        cat_entry = team_entry.setdefault(category, {'stat_types': OrderedDict(), 'players': OrderedDict()})

        # Track stat type order
        if stat_type not in cat_entry['stat_types']:
            cat_entry['stat_types'][stat_type] = len(cat_entry['stat_types'])

        # Track player stats
        player_entry = cat_entry['players'].setdefault(player_name, {})
        player_entry[stat_type] = stat_value

    # Convert to list format for template
    player_stats = []
    for team_name, categories in teams_map.items():
        team_obj = {'team': team_name, 'categories': []}
        for cat_name, cat_data in categories.items():
            # Get stat column names in order
            stat_columns = sorted(cat_data['stat_types'].items(), key=lambda x: x[1])
            stat_column_names = [prettify_stat_name(col[0]) for col in stat_columns]
            stat_column_keys = [col[0] for col in stat_columns]

            # Build player rows with all stats
            players = []
            for player_name, player_stats_dict in cat_data['players'].items():
                # Collect stats in correct column order
                stats = [player_stats_dict.get(key, '-') for key in stat_column_keys]
                players.append({'name': player_name, 'stats': stats})

            cat_obj = {
                'name': prettify_stat_name(cat_name),
                'stat_columns': stat_column_names,
                'players': players
            }
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
    avg_ppg, total_points = get_oklahoma_ppg()
    context = {
        "oklahoma_ppg": avg_ppg,
        "oklahoma_total_points": total_points,
    }

    return render(request, "stats/team_stats.html", context)


def conference_standings(request):
    """Displays the current conference standings for the SEC and highlights Oklahoma's position."""
    year = 2025
    conference = "SEC"
    team = "Oklahoma"

    # Get cached points-per-game data
    ppg_data = get_team_ppg(year=year, conference=conference)
    standings = fetch_conference_standings(year, conference)

    oklahoma_position = None
    oklahoma_tied = False

    for entry in standings:
        # Normalize and find PPG value safely
        entry['ppg'] = next(
            (ppg_value for ppg_team, ppg_value in ppg_data.items()
             if normalize_name(ppg_team) == normalize_name(entry['team'])),
            'N/A'
        )
        try:
            entry['logo'] = get_team_logo(entry['team'])
        except Exception:
            entry['logo'] = None

        # Highlight Oklahoma
        if normalize_name(entry['team']) == normalize_name(team):
            oklahoma_position = entry['position']
            oklahoma_tied = entry['tied']
            entry['is_oklahoma'] = True
        else:
            entry['is_oklahoma'] = False

    context = {
        "title": f"{conference} Conference Standings - {year}",
        "conference": conference,
        "year": year,
        "standings": standings,
        "oklahoma_position": oklahoma_position,
        "oklahoma_tied": oklahoma_tied,
    }

    return render(request, "stats/conference_standings.html", context)





