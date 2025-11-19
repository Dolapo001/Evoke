from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.gallery_home, name='home'),
    path('upload/', views.upload_image, name='upload'),
    path('<int:image_id>/', views.image_detail, name='detail'),
    path('<int:image_id>/like/', views.like_image, name='like'),
    path('<int:image_id>/download/', views.download_image, name='download'),
    path('download-all/', views.download_all_memories, name='download_all'),
]