from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=100)
    conference = models.CharField(max_length=50, blank=True)
    logo_url = models.URLField(blank=True)
    def __str__(self):
        return self.name


class Game(models.Model):
    RESULT_CHOICES = [
        ('W', 'Win'),
        ('L', 'Loss'),
        # Removed ('T', 'Tie') since college football doesn't have ties
    ]

    HOME_AWAY_CHOICES = [
        ('H', 'Home'),
        ('A', 'Away'),
        ('N', 'Neutral'),
    ]

    opponent = models.ForeignKey(Team, on_delete=models.CASCADE)
    date = models.DateField()
    home_away = models.CharField(max_length=1, choices=HOME_AWAY_CHOICES, default='H')
    oklahoma_score = models.PositiveIntegerField()
    opponent_score = models.PositiveIntegerField()
    result = models.CharField(max_length=1, choices=RESULT_CHOICES, blank=True)
    venue = models.CharField(max_length=200, blank=True)
    attendance = models.PositiveIntegerField(null=True, blank=True)
    season_record = models.CharField(max_length=20, blank=True)
    conference_record = models.CharField(max_length=20, blank=True)

    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-determine result (Win or Loss only)
        if self.oklahoma_score > self.opponent_score:
            self.result = 'W'
        else:
            self.result = 'L'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Oklahoma {self.oklahoma_score} - {self.opponent_score} {self.opponent.name} ({self.date})"

    class Meta:
        ordering = ['-date']
