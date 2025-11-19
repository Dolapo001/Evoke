from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('schedule/', views.event_schedule, name='schedule'),
    path('<int:event_id>/', views.event_detail, name='detail'),  # This is the correct name
    path('<int:event_id>/scores/', views.event_scores, name='event_scores'),
]