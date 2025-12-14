import csv
from uuid import uuid4

from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    FormView,
    TemplateView
)

from .forms import AttendeeRSVPForm, EventForm, PublicRSVPForm
from .models import Event, Attendee


class EventListView(LoginRequiredMixin, ListView):
    """
    List of events owned by the logged-in user.
    """
    model = Event
    template_name = "event_manager/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        return (
            Event.objects
            .filter(Q(host=self.request.user) | Q(cohosts=self.request.user))
            .order_by("-date", "name")
        )


class EventDetailView(LoginRequiredMixin, DetailView):
    """
    Basic event summary page – will later be the entry point to
    Attendee Management (guest list, RSVPs, etc.).
    """
    model = Event
    template_name = "event_manager/event_detail.html"
    context_object_name = "event"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Event.objects.filter(Q(host=self.request.user) | Q(cohosts=self.request.user))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        ctx["attendees"] = event.attendees.all()
        ctx["attending_total"] = sum(
            g.attending_count for g in event.attendees.filter(status=Attendee.RSVPStatus.ACCEPTED)
        )

        # Build absolute shareable URL for template
        shared_rsvp_url = self.request.build_absolute_uri(
            event.get_shared_rsvp_url()
        )

        ctx["shared_rsvp_url"] = shared_rsvp_url
        return ctx


class EventPublicDetailView(DetailView):
    """
    Public read-only event detail, accessible via shared_rsvp_token.
    Does NOT require login; used for guests who RSVP'd via shared link.
    """
    model = Event
    template_name = "event_manager/event_public_detail.html"
    context_object_name = "event"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        event = super().get_object(queryset)
        token = self.kwargs.get("token")
        if not token or str(token) != str(event.shared_rsvp_token):
            raise Http404("Invalid event view link.")
        return event

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # ensure token is in context (as a string)
        ctx["token"] = str(self.kwargs.get("token", "")) or None
        return ctx



class EventSharedLinkRegenerateView(PermissionRequiredMixin, View):
    """
    Regenerates the shared RSVP token for an event.
    Any previously shared links will stop working.
    """
    permission_required = "event_manager.change_event"

    def post(self, request, slug, *args, **kwargs):
        event = get_object_or_404(Event, slug=slug, host=request.user)
        event.shared_rsvp_token = uuid4()
        event.save(update_fields=["shared_rsvp_token"])

        messages.success(
            request,
            "Shareable RSVP link has been regenerated. "
            "Previously shared links will no longer work.",
        )
        return redirect("event_manager:event_detail", slug=slug)


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "event_manager/event_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.host = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record_id"] = None
        ctx["cancel_url"] = reverse_lazy("event_manager:event_list")
        return ctx


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "event_manager/event_form.html"

    def get_queryset(self):
        from django.db.models import Q
        return Event.objects.filter(
            Q(host=self.request.user) | Q(cohosts=self.request.user)
        ).distinct()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record_id"] = self.object.pk
        ctx["cancel_url"] = reverse_lazy("event_manager:event_detail", kwargs={"slug": self.object.slug})
        return ctx


class EventPublishView(PermissionRequiredMixin, View):
    permission_required = "event_manager.change_event"

    def post(self, request, slug):
        event = get_object_or_404(
            Event,
            Q(slug=slug) & (Q(host=request.user) | Q(cohosts=request.user)),
        )
        event.status = Event.Status.PUBLISHED
        event.save(update_fields=["status"])
        return redirect("event_manager:event_detail", slug=slug)


class EventArchiveView(PermissionRequiredMixin, View):
    permission_required = "event_manager.change_event"

    def post(self, request, slug):
        event = get_object_or_404(
            Event,
            Q(slug=slug) & (Q(host=request.user) | Q(cohosts=request.user)),
        )
        event.status = Event.Status.ARCHIVED
        event.save(update_fields=["status"])
        return redirect("event_manager:event_detail", slug=slug)


class EventAttendeeListView(LoginRequiredMixin, DetailView):
    """
    Lists attendees for a single event, with summary stats.
    Only the host (or later: users with proper perms) can access.
    """
    model = Event
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "event_manager/attendee_list.html"
    context_object_name = "event"

    def get_queryset(self):
        # Restrict to events owned by the current user
        return Event.objects.filter(Q(host=self.request.user) | Q(cohosts=self.request.user))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object

        attendees = (
            event.attendees
            .select_related("user")
            .order_by("last_name", "first_name")
        )

        total_records = attendees.count()

        accepted_qs = attendees.filter(status=Attendee.RSVPStatus.ACCEPTED)
        declined_qs = attendees.filter(status=Attendee.RSVPStatus.DECLINED)
        pending_qs = attendees.filter(status=Attendee.RSVPStatus.PENDING)
        maybe_qs = attendees.filter(status=Attendee.RSVPStatus.MAYBE)

        def headcount(qs):
            return sum(a.attending_count for a in qs)

        ctx.update(
            attendees=attendees,
            total_records=total_records,
            accepted_records=accepted_qs.count(),
            declined_records=declined_qs.count(),
            pending_records=pending_qs.count(),
            maybe_records=maybe_qs.count(),
            accepted_headcount=headcount(accepted_qs),
            declined_headcount=headcount(declined_qs),
            pending_headcount=headcount(pending_qs),
            maybe_headcount=headcount(maybe_qs),
        )
        return ctx


class EventAttendeeExportCSVView(LoginRequiredMixin, View):
    """
    Export all attendees for an event as CSV.
    """
    def get(self, request, slug, *args, **kwargs):
        event = get_object_or_404(Event, slug=slug, host=request.user)
        attendees = event.attendees.select_related("user").order_by("last_name", "first_name")

        response = HttpResponse(content_type="text/csv")
        filename = f"{event.slug}-attendees.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "First name",
                "Last name",
                "Email",
                "Phone",
                "Status",
                "Attending count",
                "Dietary requirements",
                "Meal preference",
                "Other notes",
                "Registration source",
                "Linked user",
                "Responded at",
                "Created at",
            ]
        )

        for a in attendees:
            writer.writerow(
                [
                    a.first_name,
                    a.last_name,
                    a.email,
                    a.phone,
                    a.get_status_display(),
                    a.attending_count,
                    a.dietary_requirements,
                    a.meal_preference,
                    a.other_notes,
                    a.get_registration_source_display(),
                    a.user.username if a.user else "",
                    a.responded_at.isoformat() if a.responded_at else "",
                    a.created_at.isoformat() if a.created_at else "",
                ]
            )

        return response


class PublicRSVPView(FormView):
    """
    Public self-registration form for an event.

    Supports two modes:
      - /events/<slug>/rsvp/                      (fully public)
      - /events/<slug>/rsvp/event/<uuid:token>/  (shared secret link)
    """
    template_name = "event_manager/rsvp_form.html"
    form_class = PublicRSVPForm

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, slug=kwargs["slug"])
        url_token = kwargs.get("token")

        user = request.user
        is_manager = (
            user.is_authenticated and self.event.user_can_manage(user)
        )

        # Check registration window
        if not self.event.registration_is_open:
            if is_manager:
                messages.info(
                    request,
                    _("RSVP is currently closed for this event. "
                      "You have been redirected to the event details page.")
                )
                return redirect("event_manager:event_detail", slug=self.event.slug)
            raise Http404("RSVP for this event is closed.")

        # If public RSVPs are disabled, a correct shared token is required
        correct_token = (str(url_token) == str(self.event.shared_rsvp_token))
        if not self.event.allow_public_rsvp:
            if not url_token or not correct_token:
                # Could return 404 instead if you prefer to hide existence
                if is_manager:
                    messages.warning(
                        request,
                        _("The RSVP link you visited is invalid or expired. "
                          "You have been redirected to the event details page.")
                    )
                    return redirect("event_manager:event_detail", slug=self.event.slug)
                raise Http404("Invalid RSVP link.")
        else:
            # Public RSVPs allowed; if a token is present, validate it (defence-in-depth)
            if url_token and not correct_token:
                if is_manager:
                    messages.warning(
                        request,
                        _("The RSVP link token is invalid. "
                          "You have been redirected to the event details page.")
                    )
                    return redirect("event_manager:event_detail", slug=self.event.slug)
                raise Http404("Invalid RSVP link.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.event
        ctx["mode"] = "public"
        ctx["attendee"] = None
        ctx["shared_token"] = self.kwargs.get("token") or self.request.GET.get("t")
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user

        if user.is_authenticated:
            initial.setdefault("first_name", getattr(user, "first_name", "") or "")
            initial.setdefault("last_name", getattr(user, "last_name", "") or "")
            initial.setdefault("email", getattr(user, "email", "") or "")

            # If you have a Profile with phone, you can do:
            try:
                profile = user.profile
                if getattr(profile, "phone", None):
                    initial.setdefault("phone", profile.phone)
            except Exception:
                pass

        return initial

    def form_valid(self, form):
        attendee = form.save(commit=False)
        attendee.event = self.event
        attendee.status = Attendee.RSVPStatus.ACCEPTED
        attendee.registration_source = Attendee.RegistrationSource.SELF_REGISTERED
        attendee.responded_at = timezone.now()

        user = self.request.user if self.request.user.is_authenticated else None
        existing = None

        if user:
            attendee.user = user

            existing = (
                Attendee.objects.filter(event=self.event, user=user)
                .order_by("-created_at")
                .first()
            )

        if existing is None:
            existing = (
                Attendee.objects
                .filter(event=self.event, email=attendee.email)
                .order_by("-created_at")
                .first()
            )

        # Simple capacity check
        if self.event.capacity:
            base_headcount = self.event.attendee_count

            if existing and existing.is_attending:
                base_headcount -= existing.attending_count

            base_headcount + attendee.attending_count
            if base_headcount > self.event.capacity:
                form.add_error("attending_count", _("Not enough remaining capacity for this party size."))
                return self.form_invalid(form)

        fields_to_copy = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "attending_count",
            "dietary_requirements",
            "meal_preference",
            "other_notes",
            "registration_source",
            "responded_at",
        ]

        if existing:
            # Update existing attendee
            for field in fields_to_copy:
                setattr(existing, field, getattr(attendee, field))
            # Ensure user is linked if we have one now
            if user and not existing.user:
                existing.user = user
            existing.save()
            saved_attendee = existing
        else:
            attendee.save()
            saved_attendee = attendee
        thanks_url = reverse("event_manager:event_rsvp_thanks", kwargs={"slug": self.event.slug})
        return redirect(f"{thanks_url}?t={self.event.shared_rsvp_token}")


class AttendeeRSVPTokenView(FormView):
    """
    RSVP/update view for invited attendees using a unique token.
    """
    template_name = "event_manager/rsvp_form.html"
    form_class = AttendeeRSVPForm

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, slug=kwargs["slug"])
        self.attendee = get_object_or_404(
            Attendee, event=self.event, rsvp_token=kwargs["token"]
        )

        # Optionally enforce registration window here:
        if not self.event.registration_is_open:
            return redirect("event_manager:event_detail", slug=self.event.slug)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        for field in self.form_class._meta.fields:
            initial[field] = getattr(self.attendee, field)
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["event"] = self.event
        ctx["attendee"] = self.attendee
        ctx["mode"] = "token"
        return ctx

    def form_valid(self, form):
        for field, value in form.cleaned_data.items():
            setattr(self.attendee, field, value)
        self.attendee.responded_at = timezone.now()
        self.attendee.save()
        return redirect(
            "event_manager:attendee_rsvp_thanks",
            slug=self.event.slug,
            token=self.attendee.rsvp_token,
        )


class RSVPThankYouView(TemplateView):
    """
    Simple 'RSVP received' page for public RSVP.
    """
    template_name = "event_manager/rsvp_thanks.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, slug=self.kwargs["slug"])
        ctx["event"] = event
        ctx["attendee"] = None
        ctx["mode"] = "public"
        ctx["shared_token"] = self.request.GET.get("t")
        return ctx


class RSVPTokenThankYouView(TemplateView):
    """
    'RSVP received' page for invited attendee, shows their name.
    """
    template_name = "event_manager/rsvp_thanks.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, slug=self.kwargs["slug"])
        attendee = get_object_or_404(
            Attendee, event=event, rsvp_token=self.kwargs["token"]
        )
        ctx["event"] = event
        ctx["attendee"] = attendee
        ctx["mode"] = "token"
        return ctx
