from __future__ import annotations

import logging

from django.db import models
from urllib.parse import urljoin

from .managers import MicroserviceManager, MicroserviceQuerySet

_logger = logging.getLogger(__name__)


# Create your models here.
class Microservice(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    prefix = models.CharField(max_length=50, unique=True, help_text="URL path prefix like 'pyfinbot'")
    base_url = models.CharField(max_length=200, help_text="Base URL like http://pyfinbot:8001/")
    version = models.CharField(max_length=20, default="1.0")
    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    objects = MicroserviceManager.from_queryset(MicroserviceQuerySet)()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (v{self.version})"

    @staticmethod
    def getService(prefix: str) -> Microservice | None:
        """Fetches the microservice instance by its prefix."""
        try:
            return Microservice.objects.get(prefix=prefix, is_active=True)
        except Microservice.DoesNotExist:
            _logger.exception(f'Microservice "{prefix}" not found or inactive')
            return None

    def buildUrl(self, path: str) -> str:
        """Builds a full URL for the microservice."""
        return urljoin(self.base_url.rstrip('/'), '/api/' + path.lstrip('/'))
