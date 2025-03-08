from django.db import models


# Create your models here.
class MapifyMarkerIcon(models.Model):
    colour = models.CharField(max_length=20)
    icon = models.CharField(max_length=20)
    prefix = models.CharField(max_length=20)

    class Meta:
        db_table = 'mapify_marker_icon'
        constraints = [
            models.UniqueConstraint(fields=['colour', 'icon', 'prefix'], name='unique_marker_icon',
                                    violation_error_message='A marker icon with this colour, icon, and prefix already exists.')
        ]

class MapifyMarker(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    icon = models.ForeignKey(MapifyMarkerIcon, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'mapify_marker'

class MapifyPlace(models.Model):
    link = models.URLField()
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    open_time = models.TimeField()
    close_time = models.TimeField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    marker = models.ForeignKey(MapifyMarker, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'mapify_place'
        constraints = [
            models.UniqueConstraint(fields=['link'], name='unique_marker',
                                    violation_error_message='A place with this link already exists.')
        ]