
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
