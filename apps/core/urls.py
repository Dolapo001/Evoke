from django.urls import path
from .views import *

app_name = "core"

urlpatterns = [
    path("login/", StudentLoginView.as_view(), name="login"),
    path("register/", StudentRegistrationView.as_view(), name="register"),
    path("logout/", logout_view, name="logout"),
    path('randomization/', HouseRandomizationView.as_view(), name='randomization'),
    path('randomization/stats/', RandomizationStatsView.as_view(), name='randomization_stats'),
    path('randomization/export/', ExportStudentsCSVView.as_view(), name='export_students'),
    path('houses/join/<str:house_code>/', join_house_whatsapp, name='join_whatsapp'),

]
