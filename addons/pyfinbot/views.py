import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.html import escape
from django.views.generic import TemplateView, FormView

from ..microservice.models import Microservice
from .forms import StockForm

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
            response = Microservice.microserviceRequest('pyfinbot', '/stocks/', method='GET',
                                                        user=self.request.user)
        except Exception:
            _logger.exception("Failed to fetch stock records")
            messages.error(self.request, "Failed to load stock records.")
            response = None
        context['records'] = [] if not response else response.json()
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
                response = Microservice.microserviceRequest('pyfinbot', f'/stocks/{record_id}',
                                                            method='GET', user=self.request.user)
            except Exception:
                _logger.exception("Failed to fetch stock record")
                messages.error(self.request, "Failed to load record.")
                response = None
            if not response:
                messages.error(self.request, response.json().get("detail") or "Failed to load record.")
            kwargs['initial'] = response.json()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["record"] = self.get_form_kwargs().get("initial")
        return context

    def form_valid(self, form):
        try:
            response = Microservice.microserviceRequest('pyfinbot', f'/stocks', method='POST',
                                                        user=self.request.user, json=form.cleaned_data)
        except Exception:
            _logger.exception("Failed to save stock record")
            messages.error(self.request, "Failed to save record.")
            return super().form_invalid(form)
        if response.status_code != 200 and response.json():
            error_message = response.json().get("detail") or "Failed to save record."
            messages.error(self.request, error_message)
            return super().form_invalid(form)
        messages.success(self.request, "Form submitted successfully.")
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
        response = Microservice.microserviceRequest('pyfinbot', f'/stocks/{record_id}',
                                                    method='DELETE', user=request.user)
    except Exception:
        _logger.exception("Failed to delete stock record")
        messages.error(request, "Failed to delete record.")
        return redirect("pyfinbot-stock-list")
    if not response.ok and response.json():
        error_message = response.json().get("detail") or "Failed to delete record."
        messages.error(request, error_message)
        return redirect("pyfinbot-stock-list")
    messages.success(request, "Stock deleted successfully.")
    return redirect("pyfinbot-stock-list")