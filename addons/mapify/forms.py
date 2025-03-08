from django import forms
from .models import MapifyMarkerIcon, MapifyMarker, MapifyPlace

class MapifyMarkerIconForm(forms.ModelForm):
    class Meta:
        model = MapifyMarkerIcon
        fields = ["colour", "icon", "prefix"]

class MapifyMarkerForm(forms.ModelForm):
    class Meta:
        model = MapifyMarker
        fields = ["name", "latitude", "longitude", "icon"]

class MapifyPlaceForm(forms.ModelForm):
    class Meta:
        model = MapifyPlace
        fields = ["link", "display_name", "open_time", "close_time", "latitude", "longitude", "marker"]
