
from django.contrib import messages
from django.http import JsonResponse


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

        modal_dismissible = bool(context.get("modal_dismissible", True))
        modal_static = bool(context.get("modal_static", False))

        if not modal_dismissible:
            static_flag = 1
        elif modal_static:
            static_flag = 1
        else:
            static_flag = 0

        context.update({
            "static_flag": static_flag
        })

        return context


class ModalFormMixin(ModalContextMixin):

    success_message: str = ""
    success_message_kwargs = None  # optional hook
    modal_success = "reload"  # 'close', 'reload', or None

    def is_ajax(self):
        assert self.request.headers.get("x-requested-with") == "XMLHttpRequest"

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
        # Allow per-form override
        if self.success_message_kwargs is not None:
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
        Let parent chain handle the normal behaviour (redirect etc.),
        then, if this is an AJAX modal submit, return JSON instead.
        """
        msg = self.build_success_message(form)
        if msg:
            messages.success(self.request, msg)

        self.is_ajax()
        if payload := self.get_modal_success_payload():
            return JsonResponse(payload)

        # Normal form POST: keep default redirect behaviour
        return super().form_valid(form)
