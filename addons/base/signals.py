
from django.conf import settings
from django.db.models.signals import pre_save, post_delete, post_save, post_migrate
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def createProfile(sender, instance, created, **kwargs):
    if created:
        user_profile = Profile(user=instance)
        user_profile.save()


# --- Cleanup helpers (delete old files when replaced/removed) ---
@receiver(pre_save, sender=Profile)
def delete_old_avatar_on_change(sender, instance: Profile, **kwargs):
    if not instance.pk:
        return
    try:
        old = Profile.objects.get(pk=instance.pk)
    except Profile.DoesNotExist:
        return
    if old.avatar and old.avatar != instance.avatar:
        old.avatar.delete(save=False)

@receiver(post_delete, sender=Profile)
def delete_avatar_on_delete(sender, instance: Profile, **kwargs):
    if instance.avatar:
        instance.avatar.delete(save=False)


@receiver(post_migrate)
def configure_site_after_migrate(sender, **kwargs):
    """
    Ensure django.contrib.sites has a correctly configured Site row
    after migrations (works in fresh DBs and on changes).
    """
    # If sites app is missing, no-op
    if "django.contrib.sites" not in settings.INSTALLED_APPS:
        return

    from django.contrib.sites.models import Site

    site_id = getattr(settings, "SITE_ID", 1)
    desired_domain = getattr(settings, "SITE_DOMAIN", None)
    desired_name = getattr(settings, "SITE_NAME", None)

    if not desired_domain or not desired_name:
        # Nothing authoritative to apply
        return

    # Create or update the Site record atomically
    site, _created = Site.objects.get_or_create(id=site_id, defaults={
        "domain": desired_domain,
        "name": desired_name,
    })

    updated = False
    if site.domain != desired_domain:
        site.domain = desired_domain
        updated = True
    if site.name != desired_name:
        site.name = desired_name
        updated = True

    if updated:
        site.save()
