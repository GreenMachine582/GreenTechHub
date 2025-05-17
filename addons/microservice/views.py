from __future__ import annotations

import logging

import requests
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, APIException

from .models import Microservice

_logger = logging.getLogger(__name__)

#TODO: add log/audit usage by user

# Create your views here.

class MicroserviceProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        self.service_prefix = kwargs.get('service')
        self.path = kwargs.get('path', '')
        return super().dispatch(request, *args, **kwargs)

    def handle_request(self, request):
        user = request.user
        self._validate_user_permissions(user)

        service = self._get_microservice_or_404()
        headers = self._prepare_headers(request)

        target_url = service.buildUrl(self.path)

        try:
            _logger.debug(f"[{request.method}] Proxying to: {target_url}")
            proxied_response = service.request('', target_url, request.method, user, request.GET, request.body,
                                               headers)
            return self._build_django_response(proxied_response)
        except Exception as e:
            _logger.exception(f"Proxy error for {target_url}")
            raise APIException(detail=str(e))

    def _get_microservice_or_404(self):
        try:
            return Microservice.objects.get(prefix=self.service_prefix, is_active=True)
        except Microservice.DoesNotExist:
            raise NotFound(detail=f'Microservice "{self.service_prefix}" not found or inactive')

    def _validate_user_permissions(self, user):
        group_name = f"{self.service_prefix}_api"
        if not user.hasGroups(user, group_name):
            raise APIException(detail=f'User does not have access to the "{group_name}" group')

    def _prepare_headers(self, request):
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() != 'host'
        }

        user = request.user
        if hasattr(user, 'is_authenticated') and user.is_authenticated:
            headers["X-User-ID"] = str(user.id)
            if "HTTP_AUTHORIZATION" in request.META:
                headers["Authorization"] = request.META["HTTP_AUTHORIZATION"]

        return headers

    @staticmethod
    def _make_proxy_request(method, url, headers, params, data):
        return requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            timeout=10
        )

    @staticmethod
    def _build_django_response(proxied_response):
        return HttpResponse(
            proxied_response.content,
            status=proxied_response.status_code,
            content_type=proxied_response.headers.get('Content-Type', 'application/json')
        )

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
