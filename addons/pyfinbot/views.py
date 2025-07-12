import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.html import escape
from django.views.generic import TemplateView, FormView

from .forms import StockForm
from ..microservice.services.client import MicroserviceClient, MicroserviceError

_logger = logging.getLogger(__name__)


class StockListView(TemplateView):
    template_name = 'stock-list.html'
    context_object_name = "records"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            client = MicroserviceClient.for_prefix("pyfinbot")
            response = client.request("/stocks/", method="GET", user=self.request.user)
            data = response.json()
        except MicroserviceError as e:
            messages.error(self.request, f"Failed to load records, due to: '{e}'.")
            data = None
        context['records'] = data or []
        return context


class StockFormView(FormView):
    form_class = StockForm
    template_name = "stock-form.html"
    success_url = reverse_lazy("pyfinbot-stock-list")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Session has expired.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        record_id = self.kwargs.get("record_id")
        if record_id:
            try:
                client = MicroserviceClient.for_prefix("pyfinbot")
                response = client.request(f"/stocks/{record_id}", method="GET", user=self.request.user)
                data = response.json()
            except MicroserviceError as e:
                messages.error(self.request, f"Failed to load record, due to: '{e}'.")
                data = None
            kwargs['initial'] = data or {}
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        record_id = self.kwargs.get("record_id")
        context["record_id"] = record_id
        context["record"] = self.get_form_kwargs().get("initial")
        return context

    def form_valid(self, form):
        try:
            client = MicroserviceClient.for_prefix("pyfinbot")
            method, path = "POST", "/stocks/"
            if record_id := self.kwargs.get("record_id"):
                method, path = "PUT", f"/stocks/{record_id}"
            _ = client.request(path, method=method, user=self.request.user, json=form.cleaned_data)
        except MicroserviceError as e:
            messages.error(self.request, f"Failed to save record, due to: '{e}'.")
            return super().form_invalid(form)
        messages.success(self.request, "Record saved successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        error_message = "<p>Failed to save record. Please correct the errors below: </p><ul>"
        for field, errors in form.errors.items():
            for error in errors:
                # Label the error with the field name if available
                field_name = form.fields[field].label if field in form.fields else "Error"
                error_message += f"<li><strong>{escape(field_name)}:</strong> {escape(error)}</li>"
        error_message += "</ul>"
        form.errors.clear()
        messages.error(self.request, error_message)
        return super().form_invalid(form)


def stock_delete(request, record_id):
    if not request.user.is_authenticated:
        messages.error(request, "Session has expired.")
        return redirect("home")

    try:
        client = MicroserviceClient.for_prefix("pyfinbot")
        _ = client.request(f"/stocks/{record_id}", method="DELETE", user=request.user)
    except MicroserviceError as e:
        messages.error(request, f"Failed to delete record, due to: '{e}'.")
        return redirect("pyfinbot-stock-list")
    messages.success(request, "Record deleted successfully.")
    return redirect("pyfinbot-stock-list")