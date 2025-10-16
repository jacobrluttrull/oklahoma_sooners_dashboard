from django.test import TestCase
from datetime import date

from .models import Team, Game
from .cfb_api import normalize_name, get_stat_leader, fetch_and_cache_schedule


class NormalizationTests(TestCase):
    def test_normalize_name_basic(self):
        self.assertEqual(normalize_name("Oklahoma"), "OKLAHOMA")
        self.assertEqual(normalize_name("U.S.C."), "USC")
        self.assertEqual(normalize_name("Florida-State"), "FLORIDA STATE")
        self.assertEqual(normalize_name("Texas & Rice"), "TEXAS AND RICE")


class StatLeaderTests(TestCase):
    class Dummy:
        def __init__(self, player, stat, statType):
            self.player = player
            self.stat = stat
            self.statType = statType

    def test_get_stat_leader_numeric(self):
        stats = [
            self.Dummy("A", "10", "YDS"),
            self.Dummy("B", "200", "YDS"),
            self.Dummy("C", "150", "YDS"),
            self.Dummy("D", "7", "TD"),
        ]
        leader = get_stat_leader(stats, stat_type="YDS")
        self.assertIsNotNone(leader)
        self.assertEqual(leader.player, "B")
        self.assertEqual(int(leader.stat), 200)


class GameModelTests(TestCase):
    def setUp(self):
        self.ou = Team.objects.create(name="Oklahoma")
        self.tx = Team.objects.create(name="Texas")

    def test_result_blank_when_scores_missing(self):
        g = Game.objects.create(
            opponent=self.tx,
            date=date(2025, 9, 10),
            home_away='H',
            oklahoma_score=None,
            opponent_score=None,
        )
        self.assertEqual(g.result, "")

    def test_result_computed_when_scores_present(self):
        g = Game.objects.create(
            opponent=self.tx,
            date=date(2025, 9, 10),
            home_away='H',
            oklahoma_score=28,
            opponent_score=14,
        )
        self.assertEqual(g.result, 'W')
        g.oklahoma_score = 13
        g.opponent_score = 17
        g.save()
        self.assertEqual(g.result, 'L')


class CachedScheduleTests(TestCase):
    def setUp(self):
        self.ou = Team.objects.create(name="Oklahoma")
        self.tx = Team.objects.create(name="Texas")
        # Recent game ensures cache path used (<24h)
        Game.objects.create(
            opponent=self.tx,
            date=date(2025, 9, 10),
            home_away='A',
            oklahoma_score=None,
            opponent_score=None,
        )

    def test_cached_schedule_with_rankings(self):
        rankings_map = {12: {normalize_name("Texas"): 3}}
        latest_week = 12
        schedule = fetch_and_cache_schedule(2025, "Oklahoma", rankings_map, latest_week)
        self.assertEqual(len(schedule), 1)
        row = schedule[0]
        self.assertEqual(row["opponent"], "Texas")
        self.assertTrue(row["is_ranked"])  # ranked opponent
        self.assertEqual(row["opponent_rank"], 3)
        self.assertEqual(row["score"], "TBD")
        self.assertIn(row["location"], ["Home", "Away", "Neutral"])  # sanity
