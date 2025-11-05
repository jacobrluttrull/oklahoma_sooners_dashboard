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

    # Legacy Oklahoma-centric fields (deprecated - use normalized fields instead)
    opponent = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    home_away = models.CharField(max_length=1, choices=HOME_AWAY_CHOICES, blank=True)
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
        # Use normalized fields for display
        if self.home_team and self.away_team:
            score_str = (
                f"{self.home_points} - {self.away_points}"
                if self.home_points is not None and self.away_points is not None
                else "TBD"
            )
            return f"{self.home_team.name} {score_str} {self.away_team.name} ({self.date})"
        # Fallback to legacy Oklahoma-centric format if available
        elif self.opponent:
            score_str = (
                f"{self.oklahoma_score} - {self.opponent_score}"
                if self.oklahoma_score is not None and self.opponent_score is not None
                else "TBD"
            )
            return f"Oklahoma {score_str} {self.opponent.name} ({self.date})"
        else:
            return f"Game on {self.date}"

    def get_opponent(self, team_name):
        """Get the opponent team for a given team in this game.

        Args:
            team_name: Name of the team (e.g., "Oklahoma")

        Returns:
            Team object of the opponent, or None if team not in game
        """
        if self.home_team and self.home_team.name == team_name:
            return self.away_team
        elif self.away_team and self.away_team.name == team_name:
            return self.home_team
        return None

    def get_score_for_team(self, team_name):
        """Get the score for a specific team in this game.

        Args:
            team_name: Name of the team (e.g., "Oklahoma")

        Returns:
            Integer score for that team, or None if team not in game
        """
        if self.home_team and self.home_team.name == team_name:
            return self.home_points
        elif self.away_team and self.away_team.name == team_name:
            return self.away_points
        return None

    def get_location_for_team(self, team_name):
        """Returns whether the game is Home, Away, or Neutral for a team.

        Args:
            team_name: Name of the team (e.g., "Oklahoma")

        Returns:
            'H' for home, 'A' for away, 'N' for neutral, or None if team not in game
        """
        if self.neutral_site:
            return 'N'
        if self.home_team and self.home_team.name == team_name:
            return 'H'
        if self.away_team and self.away_team.name == team_name:
            return 'A'
        return None

    def get_result_for_team(self, team_name):
        """Returns the result (W/L) for a specific team in this game.

        Args:
            team_name: Name of the team (e.g., "Oklahoma")

        Returns:
            'W' for win, 'L' for loss, or None if game incomplete or team not in game
        """
        if self.home_points is None or self.away_points is None:
            return None

        team_score = self.get_score_for_team(team_name)
        opponent = self.get_opponent(team_name)

        if team_score is None or opponent is None:
            return None

        opponent_score = self.get_score_for_team(opponent.name)

        if opponent_score is None:
            return None

        return 'W' if team_score > opponent_score else 'L'

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
