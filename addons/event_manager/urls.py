from django.urls import path
from . import views

app_name = "event_manager"

urlpatterns = [
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/create/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<slug:slug>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<slug:slug>/edit/", views.EventUpdateView.as_view(), name="event_update"),
    path("events/<slug:slug>/publish/", views.EventPublishView.as_view(), name="event_publish"),
    path("events/<slug:slug>/archive/", views.EventArchiveView.as_view(), name="event_archive"),
    path("events/<slug:slug>/shared-link/regenerate/", views.EventSharedLinkRegenerateView.as_view(),
         name="event_shared_link_regenerate"),
    path("events/<slug:slug>/view/<uuid:token>/", views.EventPublicDetailView.as_view(), name="event_public_detail"),

    # Attendee management
    path("events/<slug:slug>/attendees/", views.EventAttendeeListView.as_view(), name="event_attendee_list"),
    path("events/<slug:slug>/attendees/export/csv/", views.EventAttendeeExportCSVView.as_view(),
         name="event_attendee_export_csv"),

    # Public RSVP (fully open)
    path("events/<slug:slug>/rsvp/", views.PublicRSVPView.as_view(), name="event_rsvp_public"),
    path("events/<slug:slug>/rsvp/thanks/", views.RSVPThankYouView.as_view(), name="event_rsvp_thanks"),

    # Event-level shared token RSVP
    path("events/<slug:slug>/rsvp/event/<uuid:token>/", views.PublicRSVPView.as_view(), name="event_rsvp_public_token"),

    # Attendee token-based RSVP (per-guest)
    path("events/<slug:slug>/rsvp/<uuid:token>/", views.AttendeeRSVPTokenView.as_view(), name="attendee_rsvp_token"),
    path("events/<slug:slug>/rsvp/<uuid:token>/thanks/", views.RSVPTokenThankYouView.as_view(), name="attendee_rsvp_thanks"),
]
