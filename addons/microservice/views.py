from __future__ import annotations

import logging

from django.contrib import messages
from django.http import JsonResponse, HttpResponseNotAllowed
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


class BaseMicroserviceDeleteView(LoginRequiredMixin, MicroserviceMixin, View):
    """
    DELETE via microservice with modal confirm support.

    Subclasses must set:
      - service_prefix (e.g. "pyfinbot")
      - delete_path   (e.g. "/stocks/{id}/")
      - success_url   (reverse_lazy(...) or name/URL)

    Optional modal customisations:
      - confirm_template_name (body-only)
      - confirm_title, confirm_message, confirm_label
      - confirm_class, header_class, icon
    """
    delete_path: str
    success_url: str

    # ===== modal config (used for GET when requested via AJAX) =====
    confirm_template_name = "modal_forms/confirm_modal.html"
    confirm_title = "Confirm Delete"
    confirm_message = "Are you sure you want to delete this record? This action cannot be undone."
    confirm_label = "Yes, delete"
    confirm_class = "btn-danger"
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
            "confirm_label": self.confirm_label,
            "confirm_class": self.confirm_class,
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
