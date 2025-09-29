from django.contrib import admin
from .models import Team, Game

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'conference']
    search_fields = ['name']

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['opponent', 'date', 'oklahoma_score', 'opponent_score', 'result', 'venue']
    list_filter = ['result', 'home_away', 'date']
    date_hierarchy = 'date'
