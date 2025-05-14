from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'addons.microservice'


@receiver(post_migrate)
def create_default_microservice(sender, **kwargs):
    if sender.label != 'microservice':
        return
    Microservice = apps.get_model('microservice', 'Microservice')
    Microservice.objects.update_or_create(
        prefix='pyfinbot',
        defaults={
            'name': 'PyFinBot',
            'description': 'Finance and stock tracking',
            'base_url': 'http://pyfinbot:8001/',
            'version': '1.0.0',
            'is_active': True
        }
    )
