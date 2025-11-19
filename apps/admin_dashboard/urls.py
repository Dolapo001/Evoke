from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.AdminDashboardView.as_view(), name='dashboard'),
    path('scores/entry/', views.ScoreEntryView.as_view(), name='score_entry'),
    path('images/approval/', views.ImageApprovalListView.as_view(), name='image_approval'),
    path('images/<int:pk>/approve/', views.approve_image, name='approve_image'),
    path('images/<int:pk>/reject/', views.reject_image, name='reject_image'),
    path('events/create/', views.EventCreateView.as_view(), name='event_create'),
    path('notifications/send/', views.send_notification, name='send_notification'),  # New URL

]