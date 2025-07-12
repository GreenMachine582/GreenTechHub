from __future__ import annotations

import logging

import requests

from django.contrib import messages
from django.http import HttpResponse
from django.views.generic import TemplateView, FormView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, APIException

from .mixins import MicroserviceMixin
from .models import Microservice
from .exceptions import MicroserviceError
from ..authentication.mixins import LoginRequiredMixin

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


class BaseMicroserviceListView(LoginRequiredMixin, MicroserviceMixin, TemplateView):
    """
    Generic list-view for any microservice endpoint.
    Subclasses must define:
      - template_name (e.g. "stock-list.html")
      - service_prefix  (e.g. "pyfinbot")
      - list_path       (e.g. "/stocks/")
      - context_object_name (default: "records")
    """
    context_object_name = "records"
    list_path: str  # e.g. "/stocks/"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            resp = self.getClient().request(
                self.list_path, method="GET", user=self.request.user
            )
            ctx[self.context_object_name] = resp.json() or []
        except MicroserviceError as e:
            messages.error(self.request, f"Failed to load records: {e}")
            ctx[self.context_object_name] = []
        return ctx


class BaseMicroserviceFormView(LoginRequiredMixin, MicroserviceMixin, FormView):
    """
    Generic create/update form against a microservice.
    Subclasses must define:
      - form_class
      - template_name
      - success_url
      - service_prefix
      - create_path   (e.g. "/stocks/")
      - update_path   (e.g. "/stocks/{id}/")
    """
    create_path: str    # e.g. "/stocks/"
    update_path: str    # e.g. "/stocks/{id}/"

    def get_initial(self):
        initial = super().get_initial()
        record_id = self.kwargs.get("record_id")
        if record_id:
            try:
                resp = self.getClient().request(
                    self.update_path.format(id=record_id),
                    method="GET",
                    user=self.request.user
                )
                initial.update(resp.json() or {})
            except MicroserviceError as e:
                messages.error(self.request, f"Failed to load record: {e}")
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record_id"] = self.kwargs.get("record_id")
        ctx["cancel_url"] = self.get_success_url()
        return ctx

    def form_valid(self, form):
        record_id = self.kwargs.get("record_id")
        if record_id:
            path, method = self.update_path.format(id=record_id), "PUT"
        else:
            path, method = self.create_path, "POST"

        try:
            self.getClient().request(
                path=path,
                method=method,
                user=self.request.user,
                json=form.cleaned_data
            )
        except MicroserviceError as e:
            messages.error(self.request, f"Failed to save record: {e}")
            return self.form_invalid(form)

        messages.success(self.request, "Record saved successfully.")
        return super().form_valid(form)
