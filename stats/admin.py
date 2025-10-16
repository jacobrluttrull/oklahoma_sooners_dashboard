from django.contrib import admin
from .models import Team, Game

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "conference", "abbreviation", "cfbd_team_id")
    search_fields = ("name", "abbreviation", "conference")

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("date", "opponent", "home_away", "oklahoma_score", "opponent_score", "result")
    list_filter = ("season", "game_type", "conference_game", "home_away")
    search_fields = ("opponent__name",)
