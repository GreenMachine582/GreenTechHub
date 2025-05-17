from __future__ import annotations

import logging

import requests
from django.db import models
from urllib.parse import urljoin

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

    def request(self,
                path: str = '',
                target_url: str = '',
                method: str = "GET",
                user=None,
                params=None,
                data=None,
                json=None,
                headers: dict = None
    ):
        if not target_url and path:
            target_url = self.buildUrl(path)

        headers = headers or {
            'Content-Type': 'application/json'
        }
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            headers["X-User-ID"] = str(user.id)

        if method not in ["POST", "PUT", "PATCH"]:
            headers.pop('Content-Length', None)
            headers.pop('Content-Type', None)

        _logger.debug(f"[{method}] Internal call to: {target_url}")

        try:
            resp = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                params=params,
                data=data if method in ["POST", "PUT", "PATCH"] else None,
                json=json if method in ["POST", "PUT", "PATCH"] else None,
                timeout=10
            )
            try:
                if resp.json():
                    return resp
            except requests.exceptions.JSONDecodeError:
                pass
            resp.raise_for_status()
            return resp
        except Exception as e:
            _logger.exception(f"Internal proxy error to {target_url}; {e}")
            raise None

    @staticmethod
    def microserviceRequest(
            service_prefix: str,
            path: str,
            method: str = "GET",
            user=None,
            params=None,
            data=None,
            json=None,
            headers: dict = None
    ):
        service = Microservice.getService(service_prefix)
        if not service:
            return []
        target_url = service.buildUrl(path)
        _logger.debug(f"[{method}] Internal call to: {target_url}")
        return service.request('', target_url, method, user, params, data, json, headers)
