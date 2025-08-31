import logging

from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView

from .forms import StockForm, TransactionForm
from ..authentication.mixins import LoginRequiredMixin
from ..microservice.views import BaseMicroserviceFormView, BaseMicroserviceListView, BaseMicroserviceDeleteView

_logger = logging.getLogger(__name__)


class StockListView(LoginRequiredMixin, TemplateView):
    template_name = "stock-list.html"
    list_path = "pyfinbot/stocks/"
    page_size = 50

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["columns"] = [
            {"title": "Symbol", "field": "symbol", "sorter": "string", "headerFilter": "input"},
            {"title": "Market", "field": "market", "sorter": "string", "headerFilter": "input"},
            {"title": "Name", "field": "name", "sorter": "string", "headerFilter": "input"},
            {"title": "Active", "field": "is_active", "formatter": "tickCross", "editor": "tickCross",
             "hozAlign": "center", "headerFilter": "tickCross"},
            {
                "title":     "Actions",
                "field":     "actions",
                "hozAlign":  "center",
                "headerSort": False,
            },
        ]
        ctx["template_columns"] = [
            {"field": "actions", "templateId": "stock-action-template"},
        ]
        return ctx


class StockFormView(BaseMicroserviceFormView):
    form_class = StockForm
    template_name = "stock-form.html"
    success_url = reverse_lazy("pyfinbot-stock-list")
    service_prefix = "pyfinbot"
    create_path = "/stocks/"
    update_path = "/stocks/{id}/"


class StockDeleteView(BaseMicroserviceDeleteView):
    service_prefix = "pyfinbot"
    delete_path = "/stocks/{id}/"
    success_url = reverse_lazy("pyfinbot-stock-list")

    confirm_title = "Delete Stock"
    confirm_message = "This will permanently remove this stock."
    confirm_label = "Delete permanently"


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


class TransactionDeleteView(BaseMicroserviceDeleteView):
    service_prefix = "pyfinbot"
    delete_path = "/transactions/{id}/"
    success_url = reverse_lazy("pyfinbot-transaction-list")
