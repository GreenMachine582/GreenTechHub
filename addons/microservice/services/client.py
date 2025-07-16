
import logging
import threading
from time import time

import requests
from requests.exceptions import JSONDecodeError, RequestException
from django.conf import settings

from ..models import Microservice
from ..exceptions import MicroserviceError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = getattr(settings, "MICROSERVICE_TIMEOUT", 10)
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
}


class MicroserviceClient:
    """
    HTTP client for microservices, with TTL cache and auto-eviction on failures.
    """
    # Time to keep each client alive (in seconds)
    CACHE_TTL_SECONDS = 5 * 60  # 5 minutes
    # Cache: { prefix: {"client": MicroserviceClient, "expires_at": timestamp} }
    _client_cache: dict[str, list[dict]] = {}
    _cache_lock = threading.RLock()

    def __init__(self, service: Microservice):
        self.service = service
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @staticmethod
    def _prepareHeaders(user) -> dict:
        hdrs = {}
        if user and getattr(user, "is_authenticated", False):
            hdrs["X-User-ID"] = str(user.id)
        return hdrs

    @staticmethod
    def validateJSONResponse(resp_json):
        """Validate JSON response structure and raise a MicroserviceError if it contains an error."""
        # Handle specific error structure from microservices
        if isinstance(resp_json, dict) and (e := resp_json.get("detail")):
            raise MicroserviceError(e)
        return

    def request(self, path: str = "", method: str = "GET", user=None, params=None, data=None, json=None,
                extra_headers: dict = None, stream: bool = False,
    ) -> requests.Response:
        prefix = self.service.prefix

        # Register in_use
        with self.__class__._cache_lock:
            entry = next(
                e for e in self.__class__._client_cache[prefix]
                if e["client"] is self
            )
            entry["in_use"] += 1

        url = "Unknown URL"
        try:
            url = self.service.buildUrl(path)
            headers = dict(self.session.headers)
            headers.update(self._prepareHeaders(user))
            if extra_headers:
                headers.update(extra_headers)

            # Remove content-type on safe methods
            if method.upper() not in {"POST", "PUT", "PATCH"}:
                headers.pop("Content-Type", None)

            logger.debug(f"[{method}] → {url}")
            resp = self.session.request(
                method, url,
                params=params, data=data, json=json,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
                stream=stream,
            )
            # Return response early if it has content
            try:
                if resp_json := resp.json():
                    if not resp.ok:
                        self.validateJSONResponse(resp_json)
                    return resp
            except JSONDecodeError:
                pass
            resp.raise_for_status()
            return resp

        except RequestException as e:
            logger.exception(f"RequestException for {url}: {e}")
            self.deregisterClient()
            raise MicroserviceError(f"Network error: {e}") from e
        except MicroserviceError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error for {url}: {e}")
            self.deregisterClient()
            raise MicroserviceError(f"Unexpected error: {e}") from e
        finally:
            # Decrement and maybe evict
            with self.__class__._cache_lock:
                entry["in_use"] -= 1
                if entry["pending_deregister"] and entry["in_use"] == 0:
                    self.__class__._client_cache[prefix].remove(entry)

    @classmethod
    def forPrefix(cls, prefix: str) -> "MicroserviceClient":
        """Retrieve client from cache or create a new one."""
        now = time()
        with cls._cache_lock:
            # ensure list exists
            entries = cls._client_cache.setdefault(prefix, [])

            # Prune expired entries
            for e in list(entries):
                if e["expires_at"] <= now and e["in_use"] == 0:
                    entries.remove(e)
                elif e["expires_at"] <= now:
                    e["pending_deregister"] = True

            # Pick first healthy client
            for e in entries:
                if not e["pending_deregister"]:
                    return e["client"]

            # If we can grow, make a new one
            if len(entries) < 2:
                svc = Microservice.objects.getByPrefix(prefix)
                if not svc:
                    raise MicroserviceError(f"No active microservice '{prefix}'")
                client = cls(svc)
                entry = {
                    "client": client,
                    "expires_at": now + cls.CACHE_TTL_SECONDS,
                    "in_use": 0,
                    "pending_deregister": False,
                }
                entries.append(entry)
                return client

            # Both slots are taken and pending: fail fast
            raise MicroserviceError(f"All clients for '{prefix}' are offline or deregistering!")

    def deregisterClient(self, prefix: str = None):
        """
        Remove the client from the cache.
        Useful for cleanup after a failure or when the service is no longer available.
        """
        prefix = prefix or self.service.prefix
        with self.__class__._cache_lock:
            entries = self.__class__._client_cache.get(prefix, [])
            for e in entries:
                if e["client"] is self:
                    if e["in_use"] > 0:
                        e["pending_deregister"] = True
                    else:
                        entries.remove(e)
                    break
            # clean up empty lists
            if not entries:
                self.__class__._client_cache.pop(prefix, None)
