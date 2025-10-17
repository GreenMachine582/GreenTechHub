from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'addons.authentication'

    def ready(self):
        # Import and connect signals only when app registry is ready
        from . import signals
