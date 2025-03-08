from django.contrib import admin

from .models import MapifyMarkerIcon, MapifyMarker, MapifyPlace

# Register your models here.

admin.site.register(MapifyMarkerIcon)
admin.site.register(MapifyMarker)
admin.site.register(MapifyPlace)