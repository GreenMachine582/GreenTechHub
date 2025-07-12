
import logging
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
    def __init__(self, service: Microservice):
        self.service = service
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @staticmethod
    def _prepare_headers(user):
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

    def request(
        self,
        path: str = "",
        method: str = "GET",
        user=None,
        params=None,
        data=None,
        json=None,
        extra_headers: dict = None
    ) -> requests.Response:
        url = self.service.buildUrl(path)
        headers = dict(self.session.headers)
        headers.update(self._prepare_headers(user))
        if extra_headers:
            headers.update(extra_headers)

        # Remove content‐type on safe methods
        if method.upper() not in {"POST", "PUT", "PATCH"}:
            headers.pop("Content-Type", None)

        logger.debug(f"[{method}] → {url}")
        try:
            resp = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )
            # Return response early if it has content
            try:
                if resp_json := resp.json():
                    if not resp:
                        MicroserviceClient.validateJSONResponse(resp_json)
                    return resp
            except JSONDecodeError:
                pass
            resp.raise_for_status()
            return resp

        except RequestException as e:
            logger.exception(f"RequestException for {url}: {e}")
            raise MicroserviceError(f"Network error: {e}") from e
        except MicroserviceError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error for {url}: {e}")
            raise MicroserviceError(f"Unexpected error: {e}") from e

    @classmethod
    def for_prefix(cls, prefix: str) -> "MicroserviceClient":
        """Look up a Microservice by prefix & return a ready client."""
        svc = Microservice.objects.get_by_prefix(prefix)
        if not svc:
            raise MicroserviceError(f"No active microservice named '{prefix}'")
        return cls(svc)
