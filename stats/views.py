from django.shortcuts import render
from .models import Game


def home(request):
    latest_game = Game.objects.first()

    # Calculate season record dynamically from all games in database
    wins = Game.objects.filter(result='W').count()
    losses = Game.objects.filter(result='L').count()

    # College football doesn't have ties, so just wins-losses
    season_record = f"{wins}-{losses}"

    # Dynamic message based on performance
    if losses == 0 and wins > 0:
        message = 'Boomer Sooner! Undefeated 2025 Season! 🔥'
    else:
        message = 'Boomer Sooner! Oklahoma Dashboard is live.'

    context = {
        'title': f'Oklahoma Sooners Dashboard ({season_record})',
        'message': message,
        'latest_game': latest_game,
        'season_record': season_record,
        'wins': wins,
        'losses': losses,
    }
    return render(request, 'stats/home.html', context)
