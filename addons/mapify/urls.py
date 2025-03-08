
from django.urls import path

from . import views


urlpatterns = [
    path('mapify/marker-icon/list/', views.MapifyMarkerIconListView.as_view(), name='mapify-marker-icon-list'),
    path('mapify/marker-icon/form/', views.MapifyMarkerIconFormView.as_view(), name='mapify-marker-icon-form'),
    path('mapify/marker-icon/form/<int:record_id>/', views.MapifyMarkerIconFormView.as_view(),
         name='mapify-marker-icon-form'),
    path('mapify/marker-icon/delete/<int:record_id>/', views.mapify_marker_icon_delete,
         name='mapify-marker-icon-delete'),

    path('mapify/marker/list/', views.MapifyMarkerListView.as_view(), name='mapify-marker-list'),
    path('mapify/marker/form/', views.MapifyMarkerFormView.as_view(), name='mapify-marker-form'),
    path('mapify/marker/form/<int:record_id>/', views.MapifyMarkerFormView.as_view(),
         name='mapify-marker-form'),
    path('mapify/marker/delete/<int:record_id>/', views.mapify_marker_delete,
         name='mapify-marker-delete'),

    path('mapify/place/list/', views.MapifyPlaceListView.as_view(), name='mapify-place-list'),
    path('mapify/place/form/', views.MapifyPlaceFormView.as_view(), name='mapify-place-form'),
    path('mapify/place/form/<int:record_id>/', views.MapifyPlaceFormView.as_view(),
         name='mapify-place-form'),
    path('mapify/place/delete/<int:record_id>/', views.mapify_place_delete,
         name='mapify-place-delete'),
]
