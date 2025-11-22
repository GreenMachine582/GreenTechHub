
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string

from ..base.utils.mixins import AjaxOnlyMixin


class ModalContextMixin:
    """
    Adds modal-related context variables:
    - modal_dismissible: boolean (defaults to True if not provided)
    - modal_static: boolean (defaults to False if not provided)
    - static_flag: 1 or 0 based on logic:
        - If modal_dismissible is False => static_flag = 1
        - Else if modal_static is True => static_flag = 1
        - Else => static_flag = 0
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        modal_dismissible = context.get("modal_dismissible")
        if modal_dismissible is None:
            modal_dismissible = True
        else:
            modal_dismissible = bool(modal_dismissible)

        modal_static = context.get("modal_static")
        if modal_static is None:
            modal_static = False
        else:
            modal_static = bool(modal_static)

        # Compute static flag:
        # - non-dismissible => forced static
        # - otherwise use modal_static
        static_flag = int((not modal_dismissible) or modal_static)

        context.update(
            {
                "modal_dismissible": modal_dismissible,
                "modal_static": modal_static,
                "static_flag": static_flag,
            }
        )
        return context


class ModalFormMixin(AjaxOnlyMixin, ModalContextMixin):
    """
    Mixin for modal-based forms.

    - Enforces AJAX-only POSTs via AjaxOnlyMixin (by default)
    - Builds and sends a success message using format(**ctx)
    - Returns JSON payload to tell the frontend what to do:
        * {'close': True, 'reload': True} for modal_success='reload'
        * {'close': True} for modal_success='close'
        * {} (no special behaviour) for modal_success=None
    """

    # AJAX config: modal submits are typically POST-only
    ajax_methods = ["POST"]

    success_message: str = ""
    success_message_kwargs = None  # optional extra context dict
    modal_success = "reload"       # 'close', 'reload', or None

    def get_success_message_kwargs(self, form):
        """
        Default context for message formatting.
        Override per-view if needed.
        """
        data = {}
        if hasattr(form, "cleaned_data"):
            data.update(form.cleaned_data)
        data["user"] = self.request.user
        return data

    def build_success_message(self, form):
        if not self.success_message:
            return ""

        ctx = self.get_success_message_kwargs(form)

        if self.success_message_kwargs:
            ctx.update(self.success_message_kwargs)

        return self.success_message.format(**ctx)

    def get_modal_success_payload(self) -> dict:
        """Build the JSON payload consumed by modal JS."""
        behavior = self.modal_success
        data: dict = {}

        if behavior is None:
            return data

        data["close"] = True
        if behavior == "reload":
            data["reload"] = True
        return data

    def form_valid(self, form):
        """
        Normal form processing, with optional AJAX modal behaviour:

        - Always run parent form_valid to perform save + redirect logic
        - If request is AJAX, return JSON payload instead of redirect
        """
        msg = self.build_success_message(form)
        if msg:
            messages.success(self.request, msg)

        response = super().form_valid(form)

        # For modal/AJAX submission, respond with JSON instead of redirect
        if self.is_ajax_request(self.request):
            if payload := self.get_modal_success_payload():
                return JsonResponse(payload)

        # Non-AJAX fallback: keep the default redirect behaviour
        return response

    def form_invalid(self, form):
        """
        For AJAX requests, return the modal HTML with errors instead of redirecting.
        For normal requests, fall back to standard behaviour.
        """
        if self.is_ajax_request(self.request):
            html = render_to_string(
                self.template_name,
                self.get_context_data(form=form),
                request=self.request,
            )
            return JsonResponse({"html": html}, status=400)

        return super().form_invalid(form)
