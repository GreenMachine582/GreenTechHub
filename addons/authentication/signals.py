import logging

from allauth.socialaccount.models import SocialAccount
from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_migrate, post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group

from .models import GroupProfile
from ..base.models import Profile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Group)
def create_group_profile(sender, instance, created, **kwargs):
    if created:
        GroupProfile.objects.get_or_create(group=instance)


@receiver(post_migrate)
def create_admin_role(sender, **kwargs):
    if sender.label != 'authentication':
        return

    Group = apps.get_model('auth', 'Group')
    Role = apps.get_model('authentication', 'Role')

    admin_role, _ = Role.objects.get_or_create(
        name='Admin',
        defaults={'description': 'Administrator role with all groups.'}
    )

    # Add all current groups to admin role
    all_groups = Group.objects.all()
    admin_role.groups.set(all_groups)  # overwrite all groups just to be sure
    admin_role.save()

    # Assign Admin role to any existing superusers
    User = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])
    superusers = User.objects.filter(is_superuser=True).exclude(role=admin_role)
    for user in superusers:
        user.role = admin_role
        user.save()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_admin_role_to_superuser(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        Role = apps.get_model('authentication', 'Role')
        try:
            admin_role = Role.objects.get(name='Admin')
            if instance.role != admin_role:
                instance.role = admin_role
                instance.save()
        except Role.DoesNotExist:
            pass  # Role not created yet


@receiver(post_save, sender='auth.Group')
def add_new_group_to_admin_role(sender, instance, created, **kwargs):
    if not created:
        return

    Role = apps.get_model('authentication', 'Role')
    try:
        admin_role = Role.objects.get(name='Admin')
        admin_role.groups.add(instance)
        admin_role.save()
    except Role.DoesNotExist:
        pass  # Role will be created post_migrate


def _extract_provider_avatar(provider: str, extra: dict) -> str | None:
    if not extra:
        return None
    provider = (provider or "").lower()
    if provider == "google":
        return extra.get("picture")
    if provider == "github":
        return extra.get("avatar_url")
    # add others here if you add more providers
    return None


def _refresh_profile_avatar_from_any_linked(user) -> tuple[str | None, str]:
    """
    Returns (avatar_url, avatar_source) from the first linked account that has one,
    or (None, 'none') if none found.
    """
    for sa in SocialAccount.objects.filter(user=user):
        url = _extract_provider_avatar(sa.provider, sa.extra_data or {})
        if url:
            return url, sa.provider
    return None, "none"


# --- when a social account is LINKED (created) ---
@receiver(post_save, sender=SocialAccount)
def on_social_linked(sender, instance: SocialAccount, created: bool, **kwargs):
    if not created:
        return
    user = instance.user
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user)

    # If no existing provider avatar, set it from this new link
    if not profile.avatar_url:
        url = _extract_provider_avatar(instance.provider, instance.extra_data or {})
        if url:
            profile.avatar_url = url
            profile.avatar_source = instance.provider
            profile.save(update_fields=["avatar_url", "avatar_source"])
            logger.info("Set provider avatar from %s for user %s", instance.provider, user.pk)


# --- when a social account is UNLINKED (deleted) ---
@receiver(post_delete, sender=SocialAccount)
def on_social_unlinked(sender, instance: SocialAccount, **kwargs):
    user = instance.user
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return

    # If current source equals the removed provider, fall back to another linked provider or clear
    if (profile.avatar_source or "").lower() == (instance.provider or "").lower():
        new_url, new_source = _refresh_profile_avatar_from_any_linked(user)
        profile.avatar_url = new_url or ""
        profile.avatar_source = new_source
        profile.save(update_fields=["avatar_url", "avatar_source"])
        logger.info("After unlinking %s, avatar now from: %s", instance.provider, new_source)
