from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group

from .models import GroupProfile


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
