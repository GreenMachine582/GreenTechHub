from django.urls import path

from .views import MicroserviceProxyView


urlpatterns = [
    path('api/<str:service>/<path:path>', MicroserviceProxyView.as_view(), name='microservice-proxy'),
]
