from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^api/(?P<service>[a-zA-Z0-9_-]+)/(?P<path>.*)$', views.MicroserviceProxyView.as_view()),
]
