from django.contrib import admin

# Register your models here.
from .models import Attendee, Event

admin.site.register(Event)
admin.site.register(Attendee)