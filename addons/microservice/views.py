import logging

import requests
from django.http import HttpResponse
from urllib.parse import urljoin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, APIException

from .models import Microservice

_logger = logging.getLogger(__name__)

#TODO: restrict proxy access to specific user roles or groups, or log usage by user

# Create your views here.

class MicroserviceProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        self.service_prefix = kwargs.get('service')
        self.path = kwargs.get('path', '')
        return super().dispatch(request, *args, **kwargs)

    def handle_request(self, request):
        try:
            service = Microservice.objects.get(prefix=self.service_prefix, is_active=True)
        except Microservice.DoesNotExist:
            raise NotFound(detail=f'Microservice "{self.service_prefix}" not found or inactive')

        target_url = urljoin(service.base_url.rstrip('/') + '/', self.path.lstrip('/'))
        _logger.debug(f"[{request.method}] Proxying to: {target_url}")

        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() != 'host'
        }

        # Add Authorization header if authenticated
        user = request.user
        if hasattr(user, 'is_authenticated') and user.is_authenticated:
            # Add custom header with authenticated user's ID
            headers["X-User-ID"] = str(request.user.id)
            auth = request.META.get("HTTP_AUTHORIZATION")
            if auth:
                headers["Authorization"] = auth

        if request.method not in ["POST", "PUT", "PATCH"]:
            headers.pop('Content-Length', None)
            headers.pop('Content-Type', None)

        try:
            proxied_response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=request.GET,
                data=request.body if request.method in ["POST", "PUT", "PATCH"] else None,
                timeout=10,
            )

            return HttpResponse(
                proxied_response.content,
                status=proxied_response.status_code,
                content_type=proxied_response.headers.get('Content-Type', 'application/json')
            )
        except Exception as e:
            _logger.exception(f"Proxy error for {target_url}")
            raise APIException(detail=str(e))

    def get(self, request, *args, **kwargs):
        return self.handle_request(request)

    def post(self, request, *args, **kwargs):
        return self.handle_request(request)

    def put(self, request, *args, **kwargs):
        return self.handle_request(request)

    def patch(self, request, *args, **kwargs):
        return self.handle_request(request)

    def delete(self, request, *args, **kwargs):
        return self.handle_request(request)
