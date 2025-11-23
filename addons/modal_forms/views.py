from django.contrib.auth.mixins import LoginRequiredMixin as LoginRequiredView
from bootstrap_modal_forms.generic import BSModalFormView

from .forms import ConfirmTextModalForm as _ConfirmTextModalForm
from .mixins import ModalFormMixin as _ModalFormMixin


class ConfirmModalView(_ModalFormMixin, LoginRequiredView, BSModalFormView):
    """
    Generic confirmation modal view.

    - Renders `modal_forms/confirm_modal.html`
    - Uses a simple "type this text to confirm" form by default
    - Expects subclasses to implement `perform_action(form)`
    """

    template_name = "modal_forms/confirm_modal.html"
    form_class = _ConfirmTextModalForm

    # Modal defaults – override in subclasses
    confirm_title = "Confirm Action"
    confirm_message = ""
    submit_label = "Confirm"
    submit_class = "btn-primary"
    header_class = "bg-warning text-dark"
    icon = ""

    required_text = None        # e.g. "DELETE", or None for no gating text
    modal_id = "confirmModal"   # override per use-case
    success_url = "/"           # where to go in non-AJAX fallback

    # ----- hooks for subclasses -----

    def get_success_url(self):
        nxt = self.request.GET.get("next") or self.request.POST.get("next")
        return nxt or super().get_success_url()

    def get_required_text(self):
        return self.required_text

    def get_modal_id(self):
        return self.modal_id

    def perform_action(self, form) -> None:
        """
        Perform the actual action once the user confirms.

        Subclasses MUST override this. They can:
        - do the destructive action, send messages, etc.
        - add errors via form.add_error(...) and let `form_valid` detect them.
        """
        raise NotImplementedError("Subclasses must implement perform_action().")

    # ----- internals -----

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("request", None)

        required_text = self.get_required_text()
        if required_text is not None:
            kwargs["required_text"] = required_text
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "action_url": self.request.path,
                "modal_id": self.get_modal_id(),
                "title": self.confirm_title,
                "message": self.confirm_message,
                "submit_label": self.submit_label,
                "submit_class": self.submit_class,
                "header_class": self.header_class,
                "icon": self.icon,
                "require_text": self.get_required_text(),
            }
        )
        return ctx

    def form_valid(self, form):
        """
        Call subclass `perform_action`. If it adds errors, treat as invalid.
        Otherwise delegate to ModalFormMixin+BSModalFormView for JSON/redirect.
        """
        self.perform_action(form)

        # Subclass may have added errors
        if form.errors:
            return self.form_invalid(form)

        return super().form_valid(form)


class DeleteConfirmModalView(ConfirmModalView):
    """
    Confirm deletion.
    """
    confirm_title = "Delete"
    submit_label = "Delete"
    submit_class = "btn-danger"
    header_class = "bg-danger text-white"
    icon = "fas fa-triangle-exclamation"

    required_text = "DELETE"
