from django.shortcuts import redirect
from django.urls import path

from . import views


urlpatterns = [
    path('', lambda request: redirect('home/', permanent=False)),
    path('home/', views.home, name='home'),
]
