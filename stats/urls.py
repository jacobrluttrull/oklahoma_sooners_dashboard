from django.urls import path
from . import views

app_name = 'stats'
urlpatterns = [
    path('', views.home, name='home'), # home view
    path('boxscore/', views.boxscore, name='boxscore_latest'), # keep for backward compatibility
    path('boxscore/<int:game_id>/', views.boxscore, name='boxscore') # New route with game_id
]
