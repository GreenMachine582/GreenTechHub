from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver

SERVICE_NAME = 'pyfinbot'
SERVICE_NAME_TEXT = 'PyFinBot'


class PyFinBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'addons.pyfinbot'


@receiver(post_migrate)
def create_microservice(sender, **kwargs):
    if sender.label != 'microservice':
        return
    Microservice = apps.get_model('microservice', 'Microservice')
    Microservice.objects.update_or_create(
        prefix=SERVICE_NAME,
        defaults={
            'name': SERVICE_NAME_TEXT,
            'description': 'Finance and stock tracking',
            'base_url': f"http://{SERVICE_NAME}:8001/",
            'version': '1.0.0',
            'is_active': True
        }
    )


@receiver(post_migrate)
def create_groups(sender, **kwargs):
    if sender.label != 'authentication':
        return

    GroupProfile = apps.get_model('authentication', 'GroupProfile')

    groups = [
        ('User', 'Allows the user to access basic functionality.'),
        ('API', 'Allows the user to access the API.'),
        ('Admin', 'Allows the user to access admin functionality.')
    ]

    for group_set in groups:
        name = ' '.join((SERVICE_NAME_TEXT, group_set[0]))
        GroupProfile.createGroupAndProfile(name, group_set[1])
