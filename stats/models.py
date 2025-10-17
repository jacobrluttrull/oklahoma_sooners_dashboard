from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    conference = models.CharField(max_length=50, blank=True)
    abbreviation = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    alternate_color = models.CharField(max_length=20, blank=True, null=True)
    cfbd_team_id = models.BigIntegerField(blank=True, null=True, unique=True)
    logo_url = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Game(models.Model):
    RESULT_CHOICES = [
        ('W', 'Win'),
        ('L', 'Loss'),
    ]

    HOME_AWAY_CHOICES = [
        ('H', 'Home'),
        ('A', 'Away'),
        ('N', 'Neutral'),
    ]

    opponent = models.ForeignKey(Team, on_delete=models.CASCADE)
    date = models.DateField()
    home_away = models.CharField(max_length=1, choices=HOME_AWAY_CHOICES, default='H')
    oklahoma_score = models.PositiveIntegerField(null=True, blank=True)
    opponent_score = models.PositiveIntegerField(null=True, blank=True)
    result = models.CharField(max_length=1, choices=RESULT_CHOICES, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    attendance = models.PositiveIntegerField(null=True, blank=True)
    season_record = models.CharField(max_length=20, blank=True)
    conference_record = models.CharField(max_length=20, blank=True)

    # Normalized fields
    season = models.IntegerField(blank=True, null=True)
    week = models.IntegerField(blank=True, null=True)
    game_type = models.CharField(max_length=30, blank=True)
    conference_game = models.BooleanField(default=False)
    neutral_site = models.BooleanField(default=False)
    home_team = models.ForeignKey(
        Team, related_name='home_games', on_delete=models.CASCADE, null=True, blank=True
    )
    away_team = models.ForeignKey(
        Team, related_name='away_games', on_delete=models.CASCADE, null=True, blank=True
    )
    home_points = models.PositiveIntegerField(null=True, blank=True)
    away_points = models.PositiveIntegerField(null=True, blank=True)
    cfbd_game_id = models.BigIntegerField(blank=True, null=True, unique=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.oklahoma_score is not None and self.opponent_score is not None:
            self.result = 'W' if self.oklahoma_score > self.opponent_score else 'L'
        else:
            self.result = ''
        super().save(*args, **kwargs)

    def __str__(self):
        score_str = (
            f"{self.oklahoma_score} - {self.opponent_score}"
            if self.oklahoma_score is not None and self.opponent_score is not None
            else "TBD"
        )
        return f"Oklahoma {score_str} {self.opponent.name} ({self.date})"

    class Meta:
        ordering = ['-date']
        unique_together = (('date', 'home_team', 'away_team'),)


# ============================================================
# 💡 Step 5: Relational Models (Player, TeamStat, PlayerStat)
# ============================================================

class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=20, blank=True)
    jersey_number = models.PositiveIntegerField(null=True, blank=True)
    cfbd_player_id = models.BigIntegerField(blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.name} ({self.team.name})"


class TeamStat(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="team_stats")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="team_stats")
    category = models.CharField(max_length=100)
    stat = models.CharField(max_length=100)

    class Meta:
        unique_together = ("game", "team", "category")

    def __str__(self):
        return f"{self.team.name} – {self.category}: {self.stat}"


class PlayerStat(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="player_stats")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="stats")
    category = models.CharField(max_length=100)
    stat_type = models.CharField(max_length=50)
    stat = models.CharField(max_length=50)

    class Meta:
        unique_together = ("game", "player", "category", "stat_type")

    def __str__(self):
        return f"{self.player.name} – {self.category}/{self.stat_type}: {self.stat}"
