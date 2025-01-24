from django.urls import path, include
from . import views


urlpatterns = [
    path('authentication/', include('django.contrib.auth.urls')),
    path('register/', views.user_register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
