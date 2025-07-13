from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView, FormView
from rest_framework.authentication import SessionAuthentication
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
    Deletes a single record via microservice and redirects.
    Subclasses must set:
      - service_prefix (e.g. "pyfinbot")
      - delete_path   (e.g. "/stocks/{id}/")
      - success_url   (could be reverse_lazy("…"))
    """
    delete_path: str    # URL template, e.g. "/stocks/{id}/"
    success_url: str    # name or absolute URL

    def post(self, request, *args, **kwargs):
        record_id = kwargs.get("record_id")
        try:
            self.getClient().request(
                path=self.delete_path.format(id=record_id),
                method="DELETE",
                user=request.user
            )
            messages.success(request, "Record deleted successfully.")
        except MicroserviceError as e:
            messages.error(request, f"Failed to delete record: {e}")
        return redirect(self.success_url)
