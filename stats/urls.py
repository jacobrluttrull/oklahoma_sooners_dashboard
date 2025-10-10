from django.urls import path
from . import views

app_name = 'stats'
urlpatterns = [
    path('', views.home, name='home'),
    path('boxscore/', views.boxscore, name='boxscore')
]
