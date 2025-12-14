from django.apps import AppConfig


class EventManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "addons.event_manager"

    def ready(self):
        from . import signals  # noqa: F401
