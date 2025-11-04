from collections import defaultdict
from stats.models import Game


def get_oklahoma_ppg():
    """
    Only includes completed games and returns Oklahoma's ppg and total points.
    Returns: (ppg, total_points)
    """
    games = Game.objects.filter(
        oklahoma_score__isnull=False,
        opponent_score__isnull=False
    )
    games_played = games.count()
    if games_played == 0:
        return 0.0, 0
    total_points = sum(g.oklahoma_score for g in games)
    avg_ppg = total_points / games_played
    return round(avg_ppg, 1), total_points


def get_all_team_ppg(year=2025, team_name=None, conference=None):
    """
    Get PPG for all teams (or a specific team) from completed games in the database.

    Args:
        year: Season year
        team_name: Optional - return just this team's PPG
        conference: Optional - filter to only teams in this conference

    Returns:
        dict: {team_name: ppg} or single ppg value if team_name specified
    """
    games = Game.objects.filter(
        season=year,
        home_points__isnull=False,
        away_points__isnull=False
    ).select_related('home_team', 'away_team')

    team_totals = defaultdict(lambda: {'points': 0, 'games': 0})

    for g in games:
        if g.home_team:
            # Apply conference filter if specified
            if conference and g.home_team.conference != conference:
                pass
            else:
                team_totals[g.home_team.name]['points'] += g.home_points
                team_totals[g.home_team.name]['games'] += 1

        if g.away_team:
            # Apply conference filter if specified
            if conference and g.away_team.conference != conference:
                pass
            else:
                team_totals[g.away_team.name]['points'] += g.away_points
                team_totals[g.away_team.name]['games'] += 1

    # Calculate PPG
    team_ppg = {}
    for team, data in team_totals.items():
        if data['games'] > 0:
            team_ppg[team] = round(data['points'] / data['games'], 1)

    # Return single team or all teams
    if team_name:
        return team_ppg.get(team_name, 0.0)
    return team_ppg


def get_oklahoma_ppg_rankings(year=2025):
    """
    Get Oklahoma's PPG rank nationally and within the SEC.

    Returns:
        dict: {
            'ppg': float,
            'total_points': int,
            'games': int,
            'national_rank': int,
            'national_total_teams': int,
            'sec_rank': int,
            'sec_total_teams': int,
        }
    """
    # Get Oklahoma's PPG and total
    ok_ppg, ok_total = get_oklahoma_ppg()
    ok_games = Game.objects.filter(
        season=year,
        oklahoma_score__isnull=False,
        opponent_score__isnull=False
    ).count()

    # Get all national PPG
    national_ppg = get_all_team_ppg(year=year)

    # Get SEC PPG only
    sec_ppg = get_all_team_ppg(year=year, conference='SEC')

    # Calculate national rank (higher PPG = better rank)
    national_rank = 1
    for team, ppg in national_ppg.items():
        if ppg > ok_ppg:
            national_rank += 1

    # Calculate SEC rank
    sec_rank = 1
    for team, ppg in sec_ppg.items():
        if ppg > ok_ppg:
            sec_rank += 1

    return {
        'ppg': ok_ppg,
        'total_points': ok_total,
        'games': ok_games,
        'national_rank': national_rank,
        'national_total_teams': len(national_ppg),
        'sec_rank': sec_rank,
        'sec_total_teams': len(sec_ppg),
    }


