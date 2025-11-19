from django.urls import path
from . import views

app_name = 'treasure_hunt'

urlpatterns = [
    path('', views.treasure_hunt_home, name='home'),
    path('scan/', views.scan_qr_code, name='scan'),
    path('leaderboard/', views.treasure_hunt_leaderboard, name='leaderboard'),
]