from django.urls import path
from . import views

app_name = 'houses'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('<int:pk>/', views.HouseDetailView.as_view(), name='detail'),
    path('<int:pk>/members/', views.house_members, name='members'),
    path('<int:pk>/scores/', views.house_scores, name='scores'),
]