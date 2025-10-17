from django.forms import widgets


class BootstrapInputMixin:
    """A mixin to extend input widgets with Bootstrap 5 support."""
    input_class = "form-control"  # Default Bootstrap input class

    def __init__(self, attrs=None, placeholder=None, prepend=None, append=None):
        attrs = attrs or {}
        attrs.setdefault("class", self.input_class)

        if placeholder:
            attrs["placeholder"] = placeholder

        self.prepend = prepend  # Icon or text before input
        self.append = append    # Icon or text after input

        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"].update({
            "prepend": self.prepend,
            "append": self.append
        })
        return context


class TextInput(BootstrapInputMixin, widgets.TextInput):
    """Bootstrap-styled Text Input."""
    template_name = "widgets/bootstrap_input.html"


class NumberInput(BootstrapInputMixin, widgets.NumberInput):
    """Bootstrap-styled Number Input."""
    template_name = "widgets/bootstrap_input.html"


class EmailInput(BootstrapInputMixin, widgets.EmailInput):
    """Bootstrap-styled Email Input."""
    template_name = "widgets/bootstrap_input.html"


class URLInput(BootstrapInputMixin, widgets.URLInput):
    """Bootstrap-styled URL Input."""
    template_name = "widgets/bootstrap_input.html"


class PasswordInput(BootstrapInputMixin, widgets.PasswordInput):
    """
    Bootstrap 5 styled password input with optional visibility toggle.
    """
    template_name = "widgets/bootstrap_password.html"

    def __init__(self, attrs=None, render_value=False, placeholder="Enter password"):
        """
        :param attrs: HTML attributes
        :param render_value: Whether to render the password value
        :param placeholder: Placeholder text
        """
        super().__init__(attrs=attrs, placeholder=placeholder)
        self.render_value = render_value
