
from django.urls import path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path('', RedirectView.as_view(pattern_name='home', permanent=False), name='root-redirect'),
    path('home/', views.home, name='home'),
    path('users/profile/', views.user_profile, name='users-profile'),
]
