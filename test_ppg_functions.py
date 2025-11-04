"""
Test script to verify the get_all_team_ppg function works correctly after fetching games.
Run this after fetch_all_games completes.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oklahoma_dashboard.settings')
django.setup()

from team_stats_util import get_all_team_ppg, get_oklahoma_ppg_rankings

print("="*60)
print("Testing PPG Functions")
print("="*60)

# Get all teams' PPG
print("\n1. Getting all teams' PPG...")
all_ppg = get_all_team_ppg(year=2025)
print(f"   Total teams with completed games: {len(all_ppg)}")

if len(all_ppg) > 0:
    # Sort and show top 10
    sorted_teams = sorted(all_ppg.items(), key=lambda x: -x[1])
    print("\n2. Top 10 teams by PPG:")
    for i, (team, ppg) in enumerate(sorted_teams[:10], 1):
        print(f"   {i:2}. {team:25} {ppg:5.1f} PPG")

    # Show Oklahoma specifically
    print("\n3. Oklahoma's PPG:")
    ok_ppg = get_all_team_ppg(year=2025, team_name='Oklahoma')
    print(f"   Oklahoma: {ok_ppg} PPG")

    # Get SEC teams
    print("\n4. SEC Teams PPG (Top 10):")
    sec_ppg = get_all_team_ppg(year=2025, conference='SEC')
    sorted_sec = sorted(sec_ppg.items(), key=lambda x: -x[1])
    for i, (team, ppg) in enumerate(sorted_sec[:10], 1):
        marker = " ← Oklahoma" if team == "Oklahoma" else ""
        print(f"   {i:2}. {team:25} {ppg:5.1f} PPG{marker}")

    # Get rankings
    print("\n5. Oklahoma Rankings:")
    try:
        rankings = get_oklahoma_ppg_rankings(year=2025)
        print(f"   PPG: {rankings['ppg']}")
        print(f"   Total Points: {rankings['total_points']}")
        print(f"   Games Played: {rankings['games']}")
        print(f"   National Rank: {rankings['national_rank']} of {rankings['national_total_teams']}")
        print(f"   SEC Rank: {rankings['sec_rank']} of {rankings['sec_total_teams']}")
    except Exception as e:
        print(f"   Error getting rankings: {e}")

else:
    print("\n   ⚠️  No teams found with completed games!")
    print("   Make sure fetch_all_games has completed successfully.")

print("\n" + "="*60)
print("Test Complete")
print("="*60)

