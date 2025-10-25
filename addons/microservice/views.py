from __future__ import annotations

import decimal
import json
import logging
from typing import Any, Dict, Optional

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.http import (
    JsonResponse,
    HttpResponseNotAllowed,
    HttpRequest,
)
from django.shortcuts import redirect, render, resolve_url
from django.views import View
from django.views.generic import TemplateView, FormView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .mixins import ProxyMixin, MicroserviceMixin
from .exceptions import MicroserviceError
from ..authentication.mixins import LoginRequiredMixin

_logger = logging.getLogger(__name__)

#TODO: add log/audit usage by user

# Create your views here.

def _makeJsonable(data: dict) -> dict:
    """
    Convert form.cleaned_data into a JSON-serializable dict.
    - Decimal → float
    - date/datetime → isoformat string
    - Leave everything else untouched
    """
    out = {}
    for k, v in data.items():
        if isinstance(v, decimal.Decimal):
            out[k] = float(v)
        elif hasattr(v, "isoformat"):  # date, datetime, time
            try:
                out[k] = v.isoformat()
            except Exception:
                out[k] = str(v)
        else:
            out[k] = v
    return out


class MicroserviceProxyView(ProxyMixin, APIView):
    permission_classes = [IsAuthenticated]


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
            ctx[self.context_object_name] = (resp.json() or {}).get("items") or []
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

    def transform_initial(self, initial: dict) -> dict:
        """Subclasses can adjust initial data before rendering the form."""
        return initial

    def transform_payload(self, cleaned_data: dict) -> dict:
        """Subclasses can adjust cleaned_data before sending to microservice."""
        return cleaned_data

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

        # allow subclasses to normalize/flatten etc.
        return self.transform_initial(initial)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record_id"] = self.kwargs.get("record_id")
        ctx["cancel_url"] = self.get_success_url()
        return ctx

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def form_valid(self, form):
        record_id = self.kwargs.get("record_id")
        if record_id:
            path, method = self.update_path.format(id=record_id), "PUT"
        else:
            path, method = self.create_path, "POST"

        # let subclasses transform cleaned_data first
        cleaned = self.transform_payload(dict(form.cleaned_data))

        payload = _makeJsonable(cleaned)
        try:
            self.getClient().request(
                path=path,
                method=method,
                user=self.request.user,
                json=payload
            )
        except MicroserviceError as e:
            messages.error(self.request, f"Failed to save record: {e}")
            return self.form_invalid(form)

        messages.success(self.request, "Record saved successfully.")
        return super().form_valid(form)


class BaseMicroserviceDeleteView(LoginRequiredMixin, MicroserviceMixin, View):
    """
    DELETE via microservice with modal confirm support.

    Subclasses must set:
      - service_prefix (e.g. "pyfinbot")
      - delete_path   (e.g. "/stocks/{id}/")
      - success_url   (reverse_lazy(...) or name/URL)

    Optional modal customisations:
      - confirm_template_name (body-only)
      - confirm_title, confirm_message, submit_label
      - submit_class, header_class, icon
    """
    delete_path: str
    success_url: str

    # ===== modal config (used for GET when requested via AJAX) =====
    confirm_template_name = "modal_forms/confirm_modal.html"
    confirm_title = "Confirm Delete"
    confirm_message = "Are you sure you want to delete this record? This action cannot be undone."
    submit_label = "Yes, delete"
    submit_class = "btn-danger"
    header_class = "bg-warning text-white"
    icon = "fas fa-triangle-exclamation"

    def _is_ajax(self, request):
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def _success_url(self):
        return resolve_url(self.success_url)

    def get(self, request, *args, **kwargs):
        if not self._is_ajax(request):
            return HttpResponseNotAllowed(["POST"])
        context = {
            "action_url": request.path,
            "title": self.confirm_title,
            "message": self.confirm_message,
            "submit_label": self.submit_label,
            "submit_class": self.submit_class,
            "header_class": self.header_class,
            "icon": self.icon,
        }
        return render(request, self.confirm_template_name, context)

    def post(self, request, *args, **kwargs):
        record_id = kwargs.get("record_id")
        try:
            self.getClient().request(
                path=self.delete_path.format(id=record_id),
                method="DELETE",
                user=request.user,
            )
        except MicroserviceError as e:
            if self._is_ajax(request):
                return JsonResponse({"ok": False, "error": str(e)}, status=400)
            messages.error(request, f"Failed to delete record: {e}")
            return redirect(self._success_url())

        # success
        if self._is_ajax(request):
            return JsonResponse({"ok": True, "redirect_url": self._success_url()})
        messages.success(request, "Record deleted successfully.")
        return redirect(self._success_url())


class BaseMicroserviceActionView(LoginRequiredMixin, MicroserviceMixin, View):
    """
    Fire-and-forget style action against a microservice endpoint.

    Subclasses MUST set:
      - service_prefix  (e.g. "pyfinbot")
      - action_path     (e.g. "/stocks/sync/{market}")
        You can use kwargs from the URL in the path via str.format(**kwargs).

    Optional:
      - method          (default: "POST")
      - success_url     (default: request.META.get("HTTP_REFERER") or "/")
      - success_message (shown when non-AJAX)
      - failure_message (shown when non-AJAX)
      - extra_headers(self, request, **kwargs) -> dict
      - build_payload(self, request, **kwargs) -> dict|None
      - transform_response(self, resp) -> Any   # if you want to massage resp.json()
    """
    action_path: str
    method: str = "POST"
    success_url: Optional[str] = None
    success_message: Optional[str] = "Action completed successfully."
    failure_message: Optional[str] = "Action failed."

    ajax_reload: bool = True  # Clients can use this to decide to reload on success

    def _path(self, **kwargs) -> str:
        if not getattr(self, "action_path", None):
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} requires an `action_path`."
            )
        try:
            return self.action_path.format(**kwargs)
        except KeyError as e:
            raise ImproperlyConfigured(
                f"Missing URL kwarg for action_path formatting: {e}"
            )

    def _success_url(self, request: HttpRequest) -> str:
        if self.success_url:
            return resolve_url(self.success_url)
        # Fall back to same page / referrer
        return request.META.get("HTTP_REFERER") or "/"

    def _is_ajax(self, request: HttpRequest) -> bool:
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"

    # --- hooks you may override in subclasses ---
    def extra_headers(self, request: HttpRequest, **kwargs) -> Dict[str, str]:
        return {}

    def build_payload(self, request: HttpRequest, **kwargs) -> Optional[Dict[str, Any]]:
        """
        If you need to send a body to the microservice, return a dict here.
        Default: None (no body).
        """
        if request.body:
            try:
                return json.loads(request.body.decode("utf-8"))
            except Exception:
                pass
        return None

    def transform_response(self, resp):
        """Return what should go into the JSON 'data' key for AJAX callers."""
        try:
            return resp.json()
        except Exception:
            return {"status_code": resp.status_code}

    # --- HTTP verbs ---
    def post(self, request: HttpRequest, *args, **kwargs):
        path = self._path(**kwargs)
        client = self.getClient()

        try:
            resp = client.request(
                path=path,
                method=self.method.upper(),
                user=request.user,
                json=self.build_payload(request, **kwargs),
                extra_headers=self.extra_headers(request, **kwargs),
            )
        except MicroserviceError as e:
            _logger.exception("Microservice action failed at %s", path)
            if self._is_ajax(request):
                return JsonResponse({"ok": False, "error": str(e)}, status=400)
            messages.error(request, self.failure_message or str(e))
            return redirect(self._success_url(request))

        # Success
        data = self.transform_response(resp)
        if self._is_ajax(request):
            return JsonResponse(
                {"ok": True, "data": data, "reload": self.ajax_reload}, status=200
            )

        if self.success_message:
            messages.success(request, self.success_message)
        return redirect(self._success_url(request))

    # Disallow other verbs by default
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])
    def put(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])
    def patch(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])
    def delete(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])
