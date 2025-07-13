
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException

from .exceptions import MicroserviceError
from .services.client import MicroserviceClient


class MicroserviceMixin:
    """
    Must set `service_prefix` on your subclass.
    Provides `self.get_client()` → a ready-to-go MicroserviceClient.
    """
    authentication_classes = [SessionAuthentication]

    service_prefix: str

    def getClient(self):
        if not getattr(self, "service_prefix", None):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires a `service_prefix` attribute."
            )
        return MicroserviceClient.forPrefix(self.service_prefix)


class ProxyMixin(MicroserviceMixin):
    """
    Mixin to proxy HTTP methods to an external microservice using MicroserviceClient.
    """

    def dispatch(self, request, *args, **kwargs):
        """Extract service prefix and path from URL kwargs."""
        self.service_prefix = kwargs.get('service')
        self.path = kwargs.get('path', '')
        return super().dispatch(request, *args, **kwargs)

    def handleRequest(self, request):
        # Permission check delegated to DRF permissions
        user = request.user
        self._validateUserPermissions(user)

        client = self.getClient()
        # Prepare extra headers for client
        extra_headers = {k: v for k, v in request.headers.items()
                         if k.lower() not in {'host', 'content-length'}}
        # Forward authorization if present
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth:
            extra_headers['Authorization'] = auth

        try:
            resp = client.request(
                path=self.path,
                method=request.method,
                user=request.user,
                params=request.GET.dict(),
                data=request.body or None,
                extra_headers=extra_headers
            )
            return HttpResponse(
                resp.content,
                status=resp.status_code,
                content_type=resp.headers.get('Content-Type', 'application/json')
            )
        except MicroserviceError as e:
            # Let DRF handle the exception
            raise APIException(detail=str(e))

    def _validateUserPermissions(self, user):
        group_name = f"{self.service_prefix}_api"
        # if not user.is_authenticated or not user.groups.filter(name=group_name).exists():
        #     raise APIException(detail=f'User does not have access to group "{group_name}"')

    # Map HTTP verbs to handle_request
    def get(self, request, *args, **kwargs):
        return self.handleRequest(request)

    def post(self, request, *args, **kwargs):
        return self.handleRequest(request)

    def put(self, request, *args, **kwargs):
        return self.handleRequest(request)

    def patch(self, request, *args, **kwargs):
        return self.handleRequest(request)

    def delete(self, request, *args, **kwargs):
        return self.handleRequest(request)
