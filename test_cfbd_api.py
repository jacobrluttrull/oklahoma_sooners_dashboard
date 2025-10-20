#!/usr/bin/env python
"""Test script to verify CFBD API methods for talent and ratings."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oklahoma_dashboard.settings')
django.setup()

import cfbd

configuration = cfbd.Configuration(access_token=os.environ.get("BEARER_TOKEN"))

print("Testing CFBD API endpoints...\n")

# Test Teams API for talent
print("1. Testing Teams API - get_talent():")
try:
    with cfbd.ApiClient(configuration) as api_client:
        teams_api = cfbd.TeamsApi(api_client)
        talent = teams_api.get_talent(year=2025)

        # Find Oklahoma
        for t in talent:
            if hasattr(t, 'team') and t.team == "Oklahoma":
                print(f"   ✓ Oklahoma Talent: {t.talent}")
                print(f"   Available attributes: {dir(t)}")
                break
        else:
            print("   ✗ Oklahoma not found in talent data")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test Ratings API for SP+
print("\n2. Testing Ratings API - get_sp_ratings():")
try:
    with cfbd.ApiClient(configuration) as api_client:
        ratings_api = cfbd.RatingsApi(api_client)
        print(f"   Available methods: {[m for m in dir(ratings_api) if not m.startswith('_')]}")

        # Try different method names
        try:
            sp_ratings = ratings_api.get_sp_ratings(year=2025)
            print(f"   ✓ get_sp_ratings() works - found {len(sp_ratings)} teams")
        except AttributeError:
            print("   ✗ get_sp_ratings() doesn't exist, trying alternatives...")

        # Try get_conference_sp_ratings
        try:
            sp_ratings = ratings_api.get_conference_sp_ratings(year=2025)
            for r in sp_ratings:
                if hasattr(r, 'team') and r.team == "Oklahoma":
                    print(f"   ✓ Oklahoma SP+ Rating: {r.rating}")
                    break
        except Exception as e2:
            print(f"   ✗ get_conference_sp_ratings() error: {e2}")

except Exception as e:
    print(f"   ✗ Error: {e}")

# Test Recruiting API
print("\n3. Testing Recruiting API - get_recruiting_teams():")
try:
    with cfbd.ApiClient(configuration) as api_client:
        recruiting_api = cfbd.RecruitingApi(api_client)
        print(f"   Available methods: {[m for m in dir(recruiting_api) if not m.startswith('_')]}")

        # Try get_recruiting_teams
        try:
            rankings = recruiting_api.get_recruiting_teams(year=2025)
            for r in rankings:
                if hasattr(r, 'team') and r.team == "Oklahoma":
                    print(f"   ✓ Oklahoma Recruiting Rank: {r.rank}")
                    break
        except AttributeError as e2:
            print(f"   ✗ get_recruiting_teams() doesn't exist: {e2}")

except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n✓ API test complete!")

