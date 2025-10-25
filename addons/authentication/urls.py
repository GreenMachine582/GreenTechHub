from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from . import views


urlpatterns = [
    path('authentication/', include('django.contrib.auth.urls')),
    path('register/', views.UserRegistrationFormView.as_view(), name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path("account/delete/", views.DeleteAccountView.as_view(), name="users-delete-account"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/userinfo/', views.user_info, name='userinfo'),
    path('api/access-check/', views.access_check, name='access_check'),
]
