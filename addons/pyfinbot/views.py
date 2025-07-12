import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy

from .forms import StockForm, TransactionForm
from ..microservice.views import BaseMicroserviceFormView, BaseMicroserviceListView
from ..microservice.services.client import MicroserviceClient, MicroserviceError

_logger = logging.getLogger(__name__)


class StockListView(BaseMicroserviceListView):
    template_name = "stock-list.html"
    service_prefix = "pyfinbot"
    list_path = "/stocks/"
    context_object_name = "records"


class StockFormView(BaseMicroserviceFormView):
    form_class = StockForm
    template_name = "stock-form.html"
    success_url = reverse_lazy("pyfinbot-stock-list")
    service_prefix = "pyfinbot"
    create_path = "/stocks/"
    update_path = "/stocks/{id}/"


def stock_delete(request, record_id):
    if not request.user.is_authenticated:
        messages.error(request, "Session has expired.")
        return redirect("home")

    try:
        client = MicroserviceClient.forPrefix("pyfinbot")
        _ = client.request(f"/stocks/{record_id}", method="DELETE", user=request.user)
    except MicroserviceError as e:
        messages.error(request, f"Failed to delete record, due to: '{e}'.")
        return redirect("pyfinbot-stock-list")
    messages.success(request, "Record deleted successfully.")
    return redirect("pyfinbot-stock-list")


class TransactionListView(BaseMicroserviceListView):
    template_name = "transaction-list.html"
    service_prefix = "pyfinbot"
    list_path = "/transactions/"
    context_object_name = "records"


class TransactionFormView(BaseMicroserviceFormView):
    form_class = TransactionForm
    template_name = "transaction-form.html"
    success_url = reverse_lazy("pyfinbot-transaction-list")
    service_prefix = "pyfinbot"
    create_path = "/transactions/"
    update_path = "/transactions/{id}/"


def transaction_delete(request, record_id):
    if not request.user.is_authenticated:
        messages.error(request, "Session has expired.")
        return redirect("home")

    try:
        client = MicroserviceClient.forPrefix("pyfinbot")
        _ = client.request(f"/transactions/{record_id}", method="DELETE", user=request.user)
    except MicroserviceError as e:
        messages.error(request, f"Failed to delete record, due to: '{e}'.")
        return redirect("pyfinbot-transaction-list")
    messages.success(request, "Record deleted successfully.")
    return redirect("pyfinbot-transaction-list")