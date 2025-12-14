import logging

from django.apps import apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def create_event_groups(sender, **kwargs):
    """
    Ensure auth Groups exist for managing Events and Attendees, and
    assign appropriate model permissions.

    Creates:
      - "Event Managers": full CRUD on Event + Attendee
      - "Event Viewers":  view-only on Event + Attendee
    """
    if sender.label != "event_manager":
        return

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Get models via app registry (avoids import-time issues)
    Event = apps.get_model("event_manager", "Event")
    Attendee = apps.get_model("event_manager", "Attendee")

    ct_event = ContentType.objects.get_for_model(Event)
    ct_attendee = ContentType.objects.get_for_model(Attendee)

    # --- Create / fetch groups ---
    event_managers_group, _ = Group.objects.get_or_create(name="Event Managers")
    event_viewers_group, _ = Group.objects.get_or_create(name="Event Viewers")

    # --- Permissions for Event + Attendee ---
    manager_codenames = [
        "add_event",
        "change_event",
        "delete_event",
        "view_event",
        "add_attendee",
        "change_attendee",
        "delete_attendee",
        "view_attendee",
    ]

    viewer_codenames = [
        "view_event",
        "view_attendee",
    ]

    manager_perms = Permission.objects.filter(
        content_type__in=[ct_event, ct_attendee],
        codename__in=manager_codenames,
    )

    viewer_perms = Permission.objects.filter(
        content_type__in=[ct_event, ct_attendee],
        codename__in=viewer_codenames,
    )

    # Assign permissions (idempotent)
    event_managers_group.permissions.set(manager_perms)
    event_viewers_group.permissions.set(viewer_perms)

    logger.info(
        "Ensured event groups exist with permissions: "
        "Event Managers (%d perms), Event Viewers (%d perms)",
        manager_perms.count(),
        viewer_perms.count(),
    )
