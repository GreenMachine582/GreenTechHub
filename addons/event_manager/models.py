from uuid import uuid4
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="managed_events",
        help_text="Primary organiser / owner of this event.",
    )

    cohosts = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="cohosted_events",
        blank=True,
        help_text="Additional users who can manage this event.",
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    short_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Shown on event lists and overviews.",
    )
    description = models.TextField(blank=True)

    # Dates / times
    date = models.DateField(help_text="Primary event date.")
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    # Location
    venue_name = models.CharField(max_length=200)
    venue_address = models.TextField(blank=True)

    # Registration / RSVP settings
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional max attendee count (leave blank for unlimited).",
    )
    rsvp_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Optional date after which registration/RSVP should close.",
    )
    allow_public_rsvp = models.BooleanField(
        default=True,
        help_text="If disabled, only guests with a valid RSVP token can register.",
    )

    shared_rsvp_token = models.UUIDField(
        default=uuid4,
        editable=False,
        unique=True,
        help_text="Token used for a shared RSVP URL that can be sent to multiple guests.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "name"]
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("event_manager:event_detail", kwargs={"slug": self.slug})

    def get_shared_rsvp_url(self):
        """
        Shared 'secret' RSVP URL that can be sent to multiple guests, e.g.
        /events/my-wedding/rsvp/event/<shared_token>/
        """
        return reverse(
            "event_manager:event_rsvp_public_token",
            kwargs={"slug": self.slug, "token": str(self.shared_rsvp_token)},
        )

    def user_can_manage(self, user) -> bool:
        """
        True if the given user is the host or one of the cohosts.
        """
        if not user or not user.is_authenticated:
            return False
        if user == self.host:
            return True
        return self.cohosts.filter(pk=user.pk).exists()

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def registration_is_open(self) -> bool:
        """
        Registration is considered open if:
          - event is published
          - today is <= RSVP deadline (if set)
          - and today <= event date (basic safety)
        """
        if not self.is_published:
            return False

        today = timezone.localdate()
        if self.rsvp_deadline and today > self.rsvp_deadline:
            return False
        if today > self.date:
            return False
        return True

    @property
    def attendee_count(self) -> int:
        """
        Total headcount (sum of party sizes) of *accepted* attendees.
        """
        return sum(
            a.attending_count
            for a in self.attendees.filter(
                status=Attendee.RSVPStatus.ACCEPTED  # type: ignore[name-defined]
            )
        )

    @property
    def attendee_records_count(self) -> int:
        """
        Number of attendee records (not headcount).
        """
        return self.attendees.count()


class Attendee(models.Model):
    """
    A guest/attendee for an event; also stores their RSVP details.
    """

    class RSVPStatus(models.TextChoices):
        PENDING = "pending", "No response yet"
        ACCEPTED = "accepted", "Attending"
        DECLINED = "declined", "Not attending"
        MAYBE = "maybe", "Unsure / Maybe"

    class RegistrationSource(models.TextChoices):
        SELF_REGISTERED = "self_registered", "Self-registered (public form)"
        INVITED = "invited", "Invited guest"
        ADMIN_ADDED = "admin_added", "Added manually by organiser"
        IMPORTED = "imported", "Imported from external data"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="attendees",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_attendances",
        help_text="Linked account, if this attendee is a logged-in user.",
    )

    # Identity
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)

    # RSVP fields
    status = models.CharField(
        max_length=20,
        choices=RSVPStatus.choices,
        default=RSVPStatus.PENDING,
    )
    attending_count = models.PositiveIntegerField(
        default=1,
        help_text="Total people in this guest's party (including themselves).",
    )

    dietary_requirements = models.TextField(
        blank=True,
        help_text="Allergies, vegetarian/vegan, halal, etc.",
    )
    meal_preference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional meal selection if you offer choices.",
    )
    other_notes = models.TextField(
        blank=True,
        help_text="Seating notes, accessibility needs, or other info.",
    )

    # Where this record came from
    registration_source = models.CharField(
        max_length=20,
        choices=RegistrationSource.choices,
        default=RegistrationSource.SELF_REGISTERED,
    )

    # Token-based RSVP link (for invited guests)
    rsvp_token = models.UUIDField(
        default=uuid4,
        editable=False,
        unique=True,
        help_text="Token used for attendee-specific RSVP URLs.",
    )

    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event", "last_name", "first_name"]
        unique_together = [("event", "email")]
        verbose_name = "Attendee"
        verbose_name_plural = "Attendees"

    def __str__(self):
        return f"{self.full_name} – {self.event.name}"

    # ----- Convenience properties / helpers -----
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_attending(self) -> bool:
        return self.status == self.RSVPStatus.ACCEPTED

    def get_rsvp_url(self):
        """
        Attendee-specific RSVP URL, e.g.
        /events/my-wedding/rsvp/8b9a9e3d-.../
        """
        return reverse(
            "event_manager:attendee_rsvp_token",
            kwargs={"slug": self.event.slug, "token": str(self.rsvp_token)},
        )
