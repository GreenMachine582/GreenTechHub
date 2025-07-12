
from django.core.exceptions import ImproperlyConfigured

from .services.client import MicroserviceClient


class MicroserviceMixin:
    """
    Must set `service_prefix` on your subclass.
    Provides `self.get_client()` → a ready-to-go MicroserviceClient.
    """
    service_prefix: str

    def getClient(self):
        if not getattr(self, "service_prefix", None):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires a `service_prefix` attribute."
            )
        return MicroserviceClient.forPrefix(self.service_prefix)
