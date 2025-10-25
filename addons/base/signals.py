
from django.conf import settings
from django.db.models.signals import pre_save, post_delete, post_save
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